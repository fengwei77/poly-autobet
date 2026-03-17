"""
Core: Trade Executor — executes trades via py_clob_client with Redis Lock protection.
Support both paper and live trading modes.
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone
from typing import Optional

from loguru import logger

from config.settings import settings, TradingMode
from core.risk_manager import risk_manager
from data.models import Trade
from data.database import async_session
from infra.redis_client import redis_client
from infra.json_utils import json_dumps


class TradeExecutor:
    """
    Executes trades with distributed lock protection.
    Paper mode: simulates trades without API calls.
    Live mode: uses py_clob_client for actual execution.
    """

    def __init__(self):
        self._clob_client = None

    async def _init_clob_client(self):
        """Initialize Polymarket CLOB client for live trading."""
        if self._clob_client or not settings.is_live:
            return

        if not settings.polymarket_private_key or settings.polymarket_private_key == "your_private_key_here":
            logger.warning("⚠️ No Polymarket private key configured — live trading disabled")
            return

        try:
            from py_clob_client.client import ClobClient
            self._clob_client = ClobClient(
                host=settings.polymarket_host,
                key=settings.polymarket_private_key,
                chain_id=settings.polymarket_chain_id,
                signature_type=2,  # POLY_GNOSIS_SAFE
            )
            logger.info("✅ Polymarket CLOB client initialized")
        except Exception as e:
            logger.error(f"Failed to init CLOB client: {e}")

    async def execute(self, signal: dict, market: dict) -> Optional[dict]:
        """
        Execute a trade based on an analysis signal.
        """
        if settings.trading_strategy == "semi-auto":
            return await self.execute_semi_auto(signal, market)
        else:
            return await self._execute_impl(signal, market)

    async def execute_semi_auto(self, signal: dict, market: dict) -> Optional[dict]:
        """Sends button to Telegram and waits for approval."""
        from notifications.telegram_bot import notifier
        from infra.json_utils import json_loads
        
        market_id = market.get("condition_id", "unknown")
        
        # 1. Send buttons
        await notifier.notify_opportunity_with_buttons(market, analysis=signal)
        logger.info(f"⏳ Waiting for manual approval for {market_id}...")
        
        # 2. Wait for Redis signal (5 minute timeout)
        channel = f"signal:manual_approve:{market_id}"
        pubsub = await redis_client.subscribe(channel)
        
        try:
            # We wait for up to 300 seconds
            wait_time = 300 
            start_time = datetime.now()
            
            while (datetime.now() - start_time).total_seconds() < wait_time:
                message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                if message:
                    decision = message["data"]
                    if decision == "APPROVED":
                        logger.info(f"✅ Manual approval received for {market_id}")
                        return await self._execute_impl(signal, market)
                    else:
                        logger.info(f"❌ Manual rejection received for {market_id}")
                        return {"status": "rejected", "reason": "User rejected via Telegram"}
                await asyncio.sleep(1)
                
            logger.info(f"⏰ Manual approval timed out for {market_id}")
            return {"status": "timeout", "reason": "Approval timeout"}
        finally:
            await pubsub.unsubscribe(channel)

    async def _execute_impl(self, signal: dict, market: dict) -> Optional[dict]:
        """Internal implementation of trade execution flow."""
        condition_id = market.get("condition_id", "unknown")
        signal_type = signal.get("signal", "HOLD")

        if signal_type == "HOLD":
            return None

        # Step 1: Risk check
        approved, reason = await risk_manager.check_trade(signal)
        if not approved:
            logger.info(f"⛔ Trade blocked by risk manager: {reason}")
            # Notify user of blockage if it was an active intent
            return {"status": "blocked", "reason": reason}

        # Step 2: Distributed lock
        lock_name = f"trade:{condition_id}"
        async with redis_client.distributed_lock(lock_name, timeout=30) as acquired:
            if not acquired:
                logger.info(f"🔒 Another node is trading {condition_id}, skipping")
                return {"status": "lock_denied"}

            # Step 3: Execute
            if settings.trading_mode == TradingMode.PAPER:
                result = await self._paper_trade(signal, market)
            elif settings.trading_mode == TradingMode.LIVE:
                result = await self._live_trade(signal, market)
            else:
                return None

        # Step 4: Update risk cache
        if result and result.get("status") == "filled":
            await risk_manager.update_after_trade(result.get("amount_usdc", 0))

        # Step 5: Publish notification
        if result and "status" in result:
            await self._publish_trade_result(result)

        return result

    async def _paper_trade(self, signal: dict, market: dict) -> dict:
        """Simulate a trade (paper trading mode)."""
        size_usdc = signal.get("suggested_size_usdc", settings.min_single_bet)
        price = market.get("yes_price", 0.5)
        side = signal.get("signal", "BUY")

        # Calculate shares: amount / price
        shares = size_usdc / price if price > 0 else 0

        trade = Trade(
            market_condition_id=market.get("condition_id", ""),
            order_id=f"paper-{uuid.uuid4().hex[:12]}",
            side=side,
            token_id=market.get("tokens", ""),
            price=price,
            size=shares,
            amount_usdc=size_usdc,
            status="filled",
            fill_price=price,
            is_paper=True,
            node_id=settings.node_role.value,
        )

        async with async_session() as session:
            session.add(trade)
            await session.commit()

        logger.info(f"📝 Paper trade: {side} ${size_usdc:.2f} @ {price:.4f} | {market.get('question', '')[:60]}")

        return {
            "status": "filled",
            "order_id": trade.order_id,
            "side": side,
            "amount_usdc": size_usdc,
            "price": price,
            "is_paper": True,
            "market": market.get("question", ""),
        }

    async def _live_trade(self, signal: dict, market: dict) -> dict:
        """Execute a real trade via Polymarket CLOB API."""
        await self._init_clob_client()

        if not self._clob_client:
            logger.error("CLOB client not available for live trading")
            return {"status": "error", "reason": "CLOB client not initialized"}

        size_usdc = signal.get("suggested_size_usdc", settings.min_single_bet)
        price = market.get("yes_price", 0.5)
        side = signal.get("signal", "BUY")

        try:
            from py_clob_client.order_builder.constants import BUY as CLOB_BUY, SELL as CLOB_SELL

            clob_side = CLOB_BUY if side == "BUY" else CLOB_SELL
            token_id = market.get("tokens", "")

            if isinstance(token_id, str) and "," in token_id:
                # YES token is first, NO token is second
                tokens = token_id.split(",")
                token_id = tokens[0].strip() if side == "BUY" else tokens[1].strip()

            order = self._clob_client.create_and_post_order({
                "token_id": token_id,
                "price": price,
                "size": size_usdc / price,
                "side": clob_side,
            })

            # Record trade
            trade = Trade(
                market_condition_id=market.get("condition_id", ""),
                order_id=order.get("orderID", ""),
                side=side,
                token_id=token_id,
                price=price,
                size=size_usdc / price,
                amount_usdc=size_usdc,
                status="pending",
                is_paper=False,
                node_id=settings.node_role.value,
            )

            async with async_session() as session:
                session.add(trade)
                await session.commit()

            logger.info(f"💰 LIVE trade: {side} ${size_usdc:.2f} @ {price:.4f} | Order: {order.get('orderID', 'N/A')}")

            return {
                "status": "pending",
                "order_id": order.get("orderID", ""),
                "side": side,
                "amount_usdc": size_usdc,
                "price": price,
                "is_paper": False,
                "market": market.get("question", ""),
            }
        except Exception as e:
            logger.error(f"Live trade failed: {e}")
            return {"status": "error", "reason": str(e)}

    async def start_order_status_tracking(self):
        """Background loop to track pending orders and update their status."""
        logger.info("📡 Starting background order status tracking...")
        while True:
            try:
                await self._update_order_statuses()
            except Exception as e:
                logger.error(f"Error in order status tracking loop: {e}")
            await asyncio.sleep(30)  # Check every 30 seconds

    async def _update_order_statuses(self):
        """Poll CLOB for pending orders and update DB."""
        if not settings.is_live or not self._clob_client:
            return

        async with async_session() as session:
            result = await session.execute(
                select(Trade).where(Trade.status == "pending", Trade.is_paper == False)
            )
            pending_trades = result.scalars().all()

            for trade in pending_trades:
                try:
                    # Poll CLOB client for order status
                    order_status = self._clob_client.get_order(trade.order_id)
                    if not order_status:
                        continue
                    
                    # Implementation depends on exact py_clob_client response structure
                    # Assuming it has status like 'filled', 'canceled', etc.
                    remote_status = order_status.get("status", "").lower()
                    
                    if remote_status in ["filled", "canceled", "expired"]:
                        trade.status = remote_status
                        if remote_status == "filled":
                            trade.fill_price = float(order_status.get("average_fill_price", trade.price))
                        
                        logger.info(f"🔄 Order {trade.order_id} status updated to: {remote_status}")
                        await session.commit()
                        
                        # Notify after update
                        await self._publish_trade_result({
                            "status": remote_status,
                            "order_id": trade.order_id,
                            "market_id": trade.market_condition_id,
                            "is_paper": False
                        })
                        
                except Exception as e:
                    logger.debug(f"Error checking status for order {trade.order_id}: {e}")

    async def _publish_trade_result(self, result: dict) -> None:
        """Publish trade result to Redis for notification system."""
        channel = "signal:trade_result"
        await redis_client.publish(channel, json_dumps(result))


trade_executor = TradeExecutor()

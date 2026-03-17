"""
Core: Position Manager — Paper Trading & pre-resolution Scalping (Take-Profit/Stop-Loss).
Tracks active positions in SQLite, monitors real-time prices coming from Redis WebSocket updates,
and triggers simulated SELL orders to take profit or cut losses before the market resolves.
"""

from __future__ import annotations

import uuid
from typing import Optional
from loguru import logger
from sqlalchemy import select, update
from datetime import datetime, timezone

from data.models import Trade
from data.database import async_session
from infra.redis_client import redis_client

from config.settings import settings

# Scalping thresholds are now loaded from settings (converted from percentages)
# e.g., 0.15 -> 1.15 multiplier, 0.10 -> 0.90 multiplier

class PositionManager:
    """Manages active paper-trading positions and executes simulated scalping."""

    async def scan_positions_for_exit(self, market_condition_id: str, current_price: float):
        """
        Called when a real-time price tick comes in.
        Checks if we hold any YES shares for this market, and if the current price
        triggers our take-profit or stop-loss limits.
        """
        async with async_session() as session:
            # 1. Look for OPEN "BUY" positions in paper mode
            query = select(Trade).where(
                Trade.market_condition_id == market_condition_id,
                Trade.side == "BUY",
                Trade.status == "filled",
                Trade.is_paper == True,
                Trade.resolved == False
            )
            result = await session.execute(query)
            open_positions = result.scalars().all()
            
            for position in open_positions:
                # Need at least some size to sell
                if position.size <= 0:
                    continue
                    
                # 2. Calculate current value
                cost_basis_usdc = position.amount_usdc
                current_value_usdc = position.size * current_price
                
                # Calculate return ratio
                if cost_basis_usdc == 0:
                    continue
                return_ratio = current_value_usdc / cost_basis_usdc
                
                # 3. Check for Take-Profit / Stop-Loss triggers
                trigger = None
                tp_threshold = 1.0 + settings.scalping_take_profit_pct
                sl_threshold = 1.0 - settings.scalping_stop_loss_pct

                if return_ratio >= tp_threshold:
                    trigger = "TAKE_PROFIT"
                elif return_ratio <= sl_threshold:
                    trigger = "STOP_LOSS"
                    
                if trigger:
                    pnl_dollars = current_value_usdc - cost_basis_usdc
                    pnl_percent = (return_ratio - 1.0) * 100
                    
                    logger.warning(
                        f"🚨 [{trigger}] Triggered on {market_condition_id[:8]}! "
                        f"Entry: ${cost_basis_usdc:.2f}(@{position.price:.2f}) -> "
                        f"Now: ${current_value_usdc:.2f}(@{current_price:.2f}) | "
                        f"PnL: ${pnl_dollars:+.2f} ({pnl_percent:+.1f}%)"
                    )
                    
                    # 4. Execute the simulated SELL (Paper Mode Scalp)
                    await self._execute_simulated_sell(
                        session=session,
                        position=position,
                        sell_price=current_price,
                        trigger_reason=trigger,
                        pnl_usdc=pnl_dollars
                    )

    async def _execute_simulated_sell(self, session, position: Trade, sell_price: float, trigger_reason: str, pnl_usdc: float):
        """Creates a SELL trade record and closes out the original BUY position."""
        sell_amount_usdc = position.size * sell_price
        
        sell_trade = Trade(
            market_condition_id=position.market_condition_id,
            order_id=f"paper-sell-{trigger_reason.lower()}-{uuid.uuid4().hex[:8]}",
            side="SELL",
            token_id=position.token_id,
            price=sell_price,
            size=position.size,  # Sell everything we bought in that lot
            amount_usdc=sell_amount_usdc,
            status="filled",
            fill_price=sell_price,
            is_paper=True,
            resolved=True, # It's resolved manually via scalp
            pnl=pnl_usdc,
            node_id="brain"
        )
        
        session.add(sell_trade)
        
        # Mark the original buy position as resolved so we don't scalp it again
        position.resolved = True
        
        await session.commit()
        
        # Increment a Redis counter for dashbaord notifications (optional)
        try:
            icon = "✅" if trigger_reason == "TAKE_PROFIT" else "🛑"
            await redis_client._client.lpush(
                "notifications:scalps", 
                f"{icon} {trigger_reason} ${pnl_usdc:+.2f} on {sell_price:.2f}"
            )
            # Keep only last 10
            await redis_client._client.ltrim("notifications:scalps", 0, 9)
        except Exception:
            pass
            
        logger.success(f"💸 Paper position CLOSED. Secured {pnl_usdc:+.2f} USDC.")

# Module singleton
position_manager = PositionManager()

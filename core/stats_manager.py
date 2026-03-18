"""
Core: Stats Manager — Aggregates trading performance and account balance.
"""

from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import Dict, Any
from sqlalchemy import select, func
from loguru import logger

from data.database import async_session
from data.models import Trade, DailyPnL, Market
from config.settings import settings, TradingMode

class StatsManager:
    """Calculates PnL, balance, and volume metrics from the database."""

    async def get_summary(self) -> dict[str, Any]:
        """Get a comprehensive summary of account status."""
        async with async_session() as session:
            # 1. Total Realized PnL (Resolved trades)
            pnl_query = select(func.sum(Trade.pnl)).where(Trade.resolved == True)
            total_realized_pnl = (await session.execute(pnl_query)).scalar() or 0.0

            # 2. Today's Realized PnL
            today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
            today_pnl_query = select(func.sum(Trade.pnl)).where(
                Trade.resolved == True,
                Trade.created_at >= today_start
            )
            today_pnl = (await session.execute(today_pnl_query)).scalar() or 0.0

            # 3. Active Positions & Unrealized PnL
            # Join Trade with Market to get current prices
            active_trades_query = select(Trade, Market.yes_price).join(
                Market, Trade.market_condition_id == Market.condition_id
            ).where(
                Trade.status == "filled",
                Trade.resolved == False
            )
            result = await session.execute(active_trades_query)
            active_data = result.all()
            
            active_positions_count = len(active_data)
            total_unrealized_pnl = 0.0
            
            for trade, current_price in active_data:
                # Unrealized PnL = (Current Price - Entry Price) * Size
                # Note: Trade.amount_usdc is the cost basis
                current_value = trade.size * current_price
                unrealized = current_value - trade.amount_usdc
                total_unrealized_pnl += unrealized

            # 4. Total Invested (All time volume of filled trades)
            invested_query = select(func.sum(Trade.amount_usdc)).where(Trade.status == "filled")
            total_invested = (await session.execute(invested_query)).scalar() or 0.0

            # 5. Calculate Balance (Equity)
            initial_bankroll = 10000.0 if settings.trading_mode == TradingMode.PAPER else settings.live_bankroll
            current_balance = initial_bankroll + total_realized_pnl + total_unrealized_pnl

            return {
                "total_pnl": total_realized_pnl, # Realized
                "unrealized_pnl": total_unrealized_pnl,
                "today_pnl": today_pnl,
                "active_positions": active_positions_count,
                "total_invested": total_invested,
                "current_balance": current_balance,
                "initial_bankroll": initial_bankroll,
                "mode": settings.trading_mode.value,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

# Singleton
stats_manager = StatsManager()

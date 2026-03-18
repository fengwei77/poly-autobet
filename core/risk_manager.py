"""
Core: Risk Manager — enforces trading limits, stop-losses, and position constraints.
All checks use Redis-cached state for non-blocking performance.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from loguru import logger

from config.settings import settings, TradingMode
from data.database import async_session
from data.models import Trade
from infra.redis_client import redis_client
from infra.json_utils import json_loads, json_dumps
from sqlalchemy import select, func


class RiskManager:
    """Risk control engine — every trade MUST pass all checks before execution."""

    # Allow settings to be overridden for testing
    settings = settings

    async def check_trade(self, signal: dict) -> tuple[bool, str]:
        """
        Run all risk checks. Returns (approved, reason).
        """
        if await self._is_emergency_stopped():
            return False, "🚨 Emergency Stop is active (System Locked)"

        checks = [
            self._check_single_bet_limit(signal),
            await self._check_daily_exposure(),
            await self._check_daily_loss(),
            await self._check_position_count(),
            await self._check_city_limit(signal.get("city", "")),
            await self._check_consecutive_losses(),
            await self._check_capital_utilization(signal.get("suggested_size_usdc", 0)),
        ]

        for approved, reason in checks:
            if not approved:
                logger.warning(f"🛡️ Risk BLOCKED: {reason}")
                return False, reason

        return True, "All checks passed"

    async def _is_emergency_stopped(self) -> bool:
        """Check if system is in emergency stop state via Redis."""
        status = await redis_client.cache_get("risk:emergency_stop")
        return status == "true"

    async def set_emergency_stop(self, active: bool = True) -> None:
        """Globally activate or deactivate the emergency stop."""
        await redis_client.cache_set("risk:emergency_stop", "true" if active else "false", ttl=0)
        if active:
            logger.critical("🚨 EMERGENCY STOP ACTIVATED")

    def _check_single_bet_limit(self, signal: dict) -> tuple[bool, str]:
        size = signal.get("suggested_size_usdc", 0)
        if size > settings.max_single_bet:
            return False, f"Single bet ${size:.2f} exceeds limit ${settings.max_single_bet}"
        if size < settings.min_single_bet:
            return False, f"Bet size ${size:.2f} below minimum ${settings.min_single_bet}"
        return True, "OK"

    async def _check_daily_exposure(self) -> tuple[bool, str]:
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        cache_key = f"risk:daily_exposure:{today}"

        cached = await redis_client.cache_get(cache_key)
        if cached:
            exposure = float(cached)
        else:
            exposure = await self._calc_daily_exposure_from_db(today)
            await redis_client.cache_set(cache_key, str(exposure), ttl=60)

        if exposure >= settings.max_daily_exposure:
            return False, f"Daily exposure ${exposure:.2f} >= limit ${settings.max_daily_exposure}"
        return True, "OK"

    async def _check_capital_utilization(self, new_bet_size: float) -> tuple[bool, str]:
        """Ensures (Total Exposure + New Bet) / Total Equity <= 80%."""
        nav = await self._get_total_nav()
        if nav <= 0:
            return False, "Cannot determine total NAV for capital limit"

        # Current exposure = Sum of active trades (invested amount)
        async with async_session() as session:
            result = await session.execute(
                select(func.sum(Trade.amount_usdc)).where(
                    Trade.status == "filled",
                    Trade.resolved == False,
                )
            )
            current_exposure = result.scalar() or 0.0

        utilization = (current_exposure + new_bet_size) / nav
        if utilization > settings.max_capital_utilization:
            return False, f"Capital utilization {utilization:.1%} exceeds limit {settings.max_capital_utilization:.0%}"
        
        return True, "OK"

    async def _get_total_nav(self) -> float:
        """Get Total Net Asset Value (Cash + Position Value)."""
        if settings.trading_mode == TradingMode.LIVE:
            # Use configured live bankroll from settings
            # TODO: Integrate with CLOB client to fetch actual wallet balance
            return settings.live_bankroll
        else:
            # Paper mode: assume 10,000 USDC starting capital
            return 10000.0

    async def _check_daily_loss(self) -> tuple[bool, str]:
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        cache_key = f"risk:daily_loss:{today}"

        cached = await redis_client.cache_get(cache_key)
        if cached:
            loss = float(cached)
        else:
            loss = await self._calc_daily_loss_from_db(today)
            await redis_client.cache_set(cache_key, str(loss), ttl=60)

        if loss >= settings.daily_stop_loss:
            return False, f"Daily loss ${loss:.2f} >= stop-loss ${settings.daily_stop_loss}"
        return True, "OK"

    async def _check_position_count(self) -> tuple[bool, str]:
        async with async_session() as session:
            result = await session.execute(
                select(func.count(Trade.id)).where(
                    Trade.status == "filled",
                    Trade.resolved == False,
                )
            )
            count = result.scalar() or 0

        if count >= settings.max_positions:
            return False, f"Open positions {count} >= limit {settings.max_positions}"
        return True, "OK"

    async def _check_city_limit(self, city: str) -> tuple[bool, str]:
        if not city or city == "unknown":
            return True, "OK"

        # Check if city is tracked in database - only apply limits to tracked cities
        async with async_session() as session:
            result = await session.execute(
                select(func.count(Trade.id)).where(
                    Trade.status == "filled",
                    Trade.resolved == False,
                    Trade.market_condition_id.like(f"%{city}%")
                )
            )
            count = result.scalar() or 0

        # Only enforce limits for tracked cities
        if count >= settings.max_per_city:
            return False, f"Open positions in {city} ({count}) >= limit {settings.max_per_city}"
        return True, "OK"

    async def _check_consecutive_losses(self) -> tuple[bool, str]:
        async with async_session() as session:
            result = await session.execute(
                select(Trade).where(
                    Trade.resolved == True,
                ).order_by(Trade.created_at.desc()).limit(settings.max_consecutive_loss_limit)
            )
            recent_trades = result.scalars().all()

        if len(recent_trades) >= settings.max_consecutive_loss_limit:
            if all(t.pnl is not None and t.pnl < 0 for t in recent_trades):
                await self.set_emergency_stop(True)
                return False, f"Consecutive {settings.max_consecutive_loss_limit} losses — EMERGENCY STOP"
        return True, "OK"

    # === DB Helpers ===

    async def _calc_daily_exposure_from_db(self, date_str: str) -> float:
        async with async_session() as session:
            result = await session.execute(
                select(func.sum(Trade.amount_usdc)).where(
                    Trade.created_at >= datetime.fromisoformat(f"{date_str}T00:00:00"),
                    Trade.status.in_(["pending", "filled"]),
                )
            )
            return result.scalar() or 0.0

    async def _calc_daily_loss_from_db(self, date_str: str) -> float:
        async with async_session() as session:
            result = await session.execute(
                select(func.sum(Trade.pnl)).where(
                    Trade.created_at >= datetime.fromisoformat(f"{date_str}T00:00:00"),
                    Trade.resolved == True,
                    Trade.pnl < 0,
                )
            )
            return abs(result.scalar() or 0.0)

    # === Update exposure cache after trade ===

    async def update_after_trade(self, amount_usdc: float) -> None:
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        cache_key = f"risk:daily_exposure:{today}"
        cached = await redis_client.cache_get(cache_key)
        current = float(cached) if cached else 0.0
        await redis_client.cache_set(cache_key, str(current + amount_usdc), ttl=86400)


risk_manager = RiskManager()

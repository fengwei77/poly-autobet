"""
Core: City Resolver — Resolves city IDs from text using static maps, DB aliases, and AI fallback.
"""

from __future__ import annotations

import re
from typing import Optional
from loguru import logger
from sqlalchemy import select

from config.cities import CITIES
from data.models import CityAlias
from data.database import async_session


class CityResolver:
    """
    Intelligent city identification layer.
    Flow: Static List -> Database Aliases -> AI Extraction -> Persistent Save.
    """

    def __init__(self):
        self._manual_overrides = {
            "nyc": "new_york",
            "lax": "los_angeles",
            "sfo": "san_francisco",
            "phl": "philadelphia",
            "chi": "chicago",
            "atx": "austin",
        }

    async def resolve_city(self, text: str) -> str:
        """
        Main entry point to identify a city ID from text.
        """
        text_lower = text.lower()

        # 1. 靜態匹配 (Static Map)
        for city_id, cfg in CITIES.items():
            if cfg.name.lower() in text_lower:
                return city_id
            for tag in cfg.polymarket_tags:
                if tag.lower().replace("-", " ") in text_lower.replace("-", " "):
                    return city_id

        # 2. 手動常用縮寫 (Hardcoded Overrides)
        for alias, city_id in self._manual_overrides.items():
            if re.search(rf"\b{alias}\b", text_lower):
                return city_id

        # 3. 資料庫別名表 (Database Aliases)
        db_city_id = await self._check_db_aliases(text_lower)
        if db_city_id:
            return db_city_id

        # 4. AI 萃取 (AI Extraction Fallback)
        from core.ai_analyzer import ai_analyzer
        ai_name = await ai_analyzer.extract_city(text)
        if ai_name and ai_name.lower() != "unknown":
            resolved_id = self._map_to_existing_city(ai_name)
            if resolved_id != "unknown":
                # 自動學習：將此 AI 辨識出的別名存入資料庫，下次直接秒讀
                await self._save_alias(ai_name.lower(), resolved_id)
                logger.info(f"💡 CityResolver learned: '{ai_name}' -> {resolved_id}")
                return resolved_id

        return "unknown"

    async def _check_db_aliases(self, text: str) -> Optional[str]:
        """Check the database for any known aliases in the text."""
        async with async_session() as session:
            # We fetch all verified aliases (could be cached in Redis for production)
            result = await session.execute(select(CityAlias))
            aliases = result.scalars().all()
            
            for entry in aliases:
                if re.search(rf"\b{re.escape(entry.alias)}\b", text):
                    return entry.city_id
        return None

    def _map_to_existing_city(self, city_name: str) -> str:
        """Map a free-text city name to our internal city_id."""
        normalized = city_name.lower().strip()
        for city_id, cfg in CITIES.items():
            if normalized == cfg.name.lower() or normalized in cfg.name.lower() or cfg.name.lower() in normalized:
                return city_id
        return "unknown"

    async def _save_alias(self, alias: str, city_id: str):
        """Persist a new alias to the database."""
        async with async_session() as session:
            try:
                new_alias = CityAlias(alias=alias, city_id=city_id, is_verified=True)
                session.add(new_alias)
                await session.commit()
            except Exception:
                await session.rollback()


# Singleton
city_resolver = CityResolver()

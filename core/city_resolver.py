"""
Core: City Resolver — Resolves city IDs from text using DB cities, aliases, and AI fallback.
"""

from __future__ import annotations

import re
from typing import Optional
from loguru import logger
from sqlalchemy import select, text

from data.models import CityAlias
from data.database import async_session


class CityResolver:
    """
    Intelligent city identification layer.
    Flow: Database Cities -> Manual Overrides -> Database Aliases -> AI Extraction.
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
        # Cache for city lookup
        self._cities_cache: Optional[list[dict]] = None

    async def _load_cities(self) -> list[dict]:
        """Load all cities from database into cache."""
        if self._cities_cache is None:
            async with async_session() as session:
                result = await session.execute(text("SELECT city_id, name FROM cities"))
                self._cities_cache = [{"city_id": r[0], "name": r[1]} for r in result.fetchall()]
        return self._cities_cache

    async def resolve_city(self, text: str) -> str:
        """
        Main entry point to identify a city ID from text.
        """
        text_lower = text.lower()
        # Normalize text: replace hyphens with spaces for matching
        text_normalized = text_lower.replace("-", " ")

        # 1. Database Aliases FIRST - before cities to handle duplicates (like Odessa US vs Odesa UA)
        db_city_id = await self._check_db_aliases(text_lower)
        if db_city_id:
            return db_city_id

        # 2. Manual Overrides
        for alias, city_id in self._manual_overrides.items():
            if re.search(rf"\b{alias}\b", text_lower):
                return city_id

        # 3. Database Cities (loaded from SQL migration)
        # Use word boundary matching to avoid partial matches
        cities = await self._load_cities()
        for city in cities:
            city_name = city["name"].lower()
            city_id_normalized = city["city_id"].lower().replace("_", " ")

            # Check if city name appears as whole word in text
            if re.search(rf"\b{re.escape(city_name)}\b", text_normalized):
                return city["city_id"]

            # Check if city_id (with underscores replaced) appears as whole word
            if re.search(rf"\b{re.escape(city_id_normalized)}\b", text_normalized):
                return city["city_id"]

        # 4. AI Extraction Fallback
        from core.ai_analyzer import ai_analyzer
        ai_name = await ai_analyzer.extract_city(text)
        if ai_name and ai_name.lower() != "unknown":
            # Try to map AI result to our cities
            resolved_id = await self._map_ai_city(ai_name)
            if resolved_id:
                # Auto-learn: save alias to database for faster lookup next time
                await self._save_alias(ai_name.lower(), resolved_id)
                logger.info(f"💡 CityResolver learned: '{ai_name}' -> {resolved_id}")
                return resolved_id
            else:
                # Return the detected city name (even if not in our tracked list)
                logger.debug(f"📍 Detected untracked city: {ai_name}")
                return ai_name.lower().replace(" ", "_")

        return "unknown"

    async def _check_db_aliases(self, text: str) -> Optional[str]:
        """Check the database for any known aliases in the text."""
        async with async_session() as session:
            result = await session.execute(select(CityAlias))
            aliases = result.scalars().all()

            for entry in aliases:
                if re.search(rf"\b{re.escape(entry.alias)}\b", text):
                    return entry.city_id
        return None

    async def _map_ai_city(self, city_name: str) -> Optional[str]:
        """Map an AI-extracted city name to our internal city_id."""
        normalized = city_name.lower().strip()
        cities = await self._load_cities()

        for city in cities:
            city_name_lower = city["name"].lower()
            # Exact match
            if normalized == city_name_lower:
                return city["city_id"]
            # Partial match (e.g., "New York" matches "New York City")
            if normalized in city_name_lower or city_name_lower in normalized:
                return city["city_id"]
        return None

    async def _save_alias(self, alias: str, city_id: str):
        """Persist a new alias to the database."""
        async with async_session() as session:
            try:
                new_alias = CityAlias(alias=alias, city_id=city_id, is_verified=True)
                session.add(new_alias)
                await session.commit()
            except Exception:
                await session.rollback()

    def invalidate_cache(self):
        """Clear the cities cache to force reload on next lookup."""
        self._cities_cache = None


# Singleton
city_resolver = CityResolver()

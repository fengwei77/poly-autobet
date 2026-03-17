"""
Core: Market Scanner — discovers and tracks Polymarket weather markets via Gamma API.
"""

from __future__ import annotations

import asyncio
import traceback
from datetime import datetime, timezone
from typing import Optional

import aiohttp
import httpx
from loguru import logger
from sqlalchemy import select

from config.settings import settings
from config.cities import CITIES
from data.models import Market
from data.database import async_session
from infra.json_utils import json_loads, json_dumps
from infra.redis_client import redis_client


GAMMA_API_BASE = "https://gamma-api.polymarket.com"

# Known weather-related tags on Polymarket
WEATHER_KEYWORDS = [
    "temperature", "weather", "rain", "precipitation",
    "snow", "wind", "heat", "cold", "forecast", "degrees", "celsius", "fahrenheit",
    "temp-high", "temp-low", "weather-forecast"
]


class MarketScanner:
    """
    Scans Polymarket for active weather markets via Gamma API.
    Caches results in Redis to avoid rate limiting.
    """

    def __init__(self):
        self._http: Optional[httpx.AsyncClient] = None
        self._ws_session: Optional[aiohttp.ClientSession] = None
        self._ws_task: Optional[asyncio.Task] = None
        self._active_tokens: set[str] = set()
        self._ws_url = "wss://ws-subscriptions-clob.polymarket.com/ws/market"

    async def _get_client(self) -> httpx.AsyncClient:
        if self._http is None or self._http.is_closed:
            self._http = httpx.AsyncClient(
                timeout=30.0,
                headers={"Accept": "application/json"},
                follow_redirects=True,
            )
        return self._http

    async def close(self):
        if self._ws_task:
            self._ws_task.cancel()
            try:
                await self._ws_task
            except asyncio.CancelledError:
                pass
        if self._ws_session and not self._ws_session.closed:
            await self._ws_session.close()
        if self._http and not self._http.is_closed:
            await self._http.aclose()

    # === Main Scan ===

    async def scan_weather_markets(self) -> list[dict]:
        """
        Fetch all active weather markets from Gamma API.
        Flow:
        1. Check Redis cache first
        2. If miss, fetch from Gamma API
        3. Filter for weather-related markets
        4. Store in Redis cache + DB
        """
        # Try cache first
        cached = await redis_client.cache_get("markets:weather:all")
        if cached:
            logger.debug("📦 Using cached weather markets")
            return json_loads(cached)

        # Fetch from Gamma API
        markets = await self._fetch_all_events()
        weather_markets = await self._filter_weather_markets(markets)

        logger.info(f"🔍 Found {len(weather_markets)} weather markets from {len(markets)} total events")

        # Cache for 10 minutes
        if weather_markets:
            await redis_client.cache_set("markets:weather:all", json_dumps(weather_markets), ttl=600)

        # Persist to DB
        await self._save_markets_to_db(weather_markets)

        # 啟動或更新 WebSocket 訂閱與 Token 映射
        tokens = []
        for m in weather_markets:
            t = m.get("tokens", "")
            if t:
                # 若為雙代幣(Yes/No)，取 Yes token (第一個)
                yes_token = t.split(",")[0].strip() if "," in t else t
                tokens.append(yes_token)
                
                # Cache token -> market mapping for fast lookup in ws listener
                await redis_client.cache_set(
                    f"market:mapping:{yes_token}", 
                    json_dumps(m), 
                    ttl=86400  # 1 day
                )
        
        if tokens:
            await self.subscribe_orderbook(tokens)

        return weather_markets

    async def _fetch_all_events(self) -> list[dict]:
        """Fetch events from Gamma API with pagination."""
        client = await self._get_client()
        all_events = []
        offset = 0
        limit = 100

        while True:
            try:
                resp = await client.get(
                    f"{GAMMA_API_BASE}/events",
                    params={
                        "active": "true",
                        "closed": "false",
                        "limit": limit,
                        "offset": offset,
                    },
                )
                resp.raise_for_status()
                events = resp.json()

                if not events:
                    break

                all_events.extend(events)
                offset += limit

                if len(events) < limit:
                    break

                # Rate limit courtesy
                await asyncio.sleep(0.2)

            except httpx.HTTPError as e:
                logger.error(f"Gamma API error: {e}")
                break

        return all_events

    async def fetch_market_detail(self, condition_id: str) -> Optional[dict]:
        """Fetch detailed market data for a specific condition ID."""
        cache_key = f"market:detail:{condition_id}"
        cached = await redis_client.cache_get(cache_key)
        if cached:
            return json_loads(cached)

        client = await self._get_client()
        try:
            resp = await client.get(
                f"{GAMMA_API_BASE}/markets",
                params={"condition_id": condition_id},
            )
            resp.raise_for_status()
            markets = resp.json()
            if markets:
                await redis_client.cache_set(cache_key, json_dumps(markets[0]), ttl=300)
                return markets[0]
        except httpx.HTTPError as e:
            logger.error(f"Failed to fetch market {condition_id}: {e}")
        return None

    # === Filtering ===

    async def _filter_weather_markets(self, events: list[dict]) -> list[dict]:
        """Filter events to keep only weather-related markets."""
        weather_markets = []

        for event in events:
            title = (event.get("title", "") or "").lower()
            description = (event.get("description", "") or "").lower()
            tags = [t.get("label", "").lower() for t in (event.get("tags", []) or [])]
            combined_text = f"{title} {description} {' '.join(tags)}"

            # Check if any weather keyword matches
            is_weather = any(kw in combined_text for kw in WEATHER_KEYWORDS)

            if is_weather:
                # Extract individual markets from the event
                for market in event.get("markets", [event]):
                    parsed = await self._parse_market(market, event)
                    if parsed:
                        weather_markets.append(parsed)

        return weather_markets

    async def _parse_market(self, market: dict, event: dict) -> Optional[dict]:
        """Parse a market into a standardized dict."""
        condition_id = market.get("conditionId") or market.get("condition_id", "")
        if not condition_id:
            return None

        # Detect city (Unified intelligent resolution)
        from core.city_resolver import city_resolver
        title = event.get("title", "")
        question = market.get("question", "")
        city = await city_resolver.resolve_city(f"{title} | {question}")
        if city != "unknown":
            logger.debug(f"📍 Resolved city for market: {city}")

        # Parse end date
        end_date_str = market.get("endDate") or market.get("end_date_iso", "")
        end_date = None
        if end_date_str:
            try:
                end_date = datetime.fromisoformat(end_date_str.replace("Z", "+00:00"))
            except (ValueError, TypeError):
                pass

        # Safely parse floats that might come as '"0"' strings
        raw_vol = str(market.get("volume", "0")).replace('"', '').replace("'", "")
        raw_liq = str(market.get("liquidity", "0")).replace('"', '').replace("'", "")

        return {
            "condition_id": condition_id,
            "question": market.get("question", event.get("title", "")),
            "market_slug": market.get("market_slug", ""),
            "city": city,
            "category": self._detect_category(market.get("question", "")),
            "yes_price": float(market.get("outcomePrices", "[0.5,0.5]").replace('"', '').replace("'", "").strip("[]").split(",")[0] if isinstance(market.get("outcomePrices"), str) else 0.5),
            "volume": float(raw_vol) if raw_vol else 0.0,
            "liquidity": float(raw_liq) if raw_liq else 0.0,
            "end_date": end_date.isoformat() if end_date else None,
            "tokens": market.get("clobTokenIds", ""),
            "is_active": market.get("active", True),
        }

    def _detect_category(self, question: str) -> str:
        """Detect market category from question text."""
        q = question.lower()
        if any(w in q for w in ["temperature", "high", "low", "degrees", "celsius", "fahrenheit"]):
            return "temperature"
        if any(w in q for w in ["rain", "precipitation", "inches"]):
            return "precipitation"
        if any(w in q for w in ["snow", "snowfall"]):
            return "snow"
        if any(w in q for w in ["wind", "mph", "kmh"]):
            return "wind"
        if any(w in q for w in ["earthquake", "quake", "magnitude"]):
            return "earthquake"
        return "weather"

    # === DB Persistence ===

    async def _save_markets_to_db(self, markets: list[dict]) -> None:
        """Upsert markets to database."""
        async with async_session() as session:
            for m in markets:
                result = await session.execute(
                    select(Market).where(Market.condition_id == m["condition_id"])
                )
                existing = result.scalar_one_or_none()

                if existing:
                    existing.yes_price = m.get("yes_price", existing.yes_price)
                    existing.volume = m.get("volume", existing.volume)
                    existing.liquidity = m.get("liquidity", existing.liquidity)
                    existing.is_active = m.get("is_active", True)
                    existing.updated_at = datetime.utcnow()
                else:
                    end_date = None
                    if m.get("end_date"):
                        try:
                            end_date = datetime.fromisoformat(m["end_date"])
                        except (ValueError, TypeError):
                            pass

                    new_market = Market(
                        condition_id=m["condition_id"],
                        question=m.get("question", ""),
                        market_slug=m.get("market_slug", ""),
                        category=m.get("category", "weather"),
                        city=m.get("city", "unknown"),
                        yes_price=m.get("yes_price", 0.5),
                        volume=m.get("volume", 0),
                        liquidity=m.get("liquidity", 0),
                        end_date=end_date,
                        is_active=m.get("is_active", True),
                    )
                    session.add(new_market)

            await session.commit()
            logger.debug(f"💾 Saved {len(markets)} markets to DB")

    # === WebSocket 即時盤口 (High-Concurrency Real-time) ===

    async def subscribe_orderbook(self, tokens: list[str]) -> None:
        """Subscribe to orderbook updates for the given tokens."""
        new_tokens = set(tokens) - self._active_tokens
        if not new_tokens and self._ws_task and not self._ws_task.done():
            return # Already subscribed
        
        self._active_tokens.update(tokens)
        
        # 啟動 WS task (如果還沒啟動)
        if not self._ws_task or self._ws_task.done():
            self._ws_task = asyncio.create_task(self._ws_loop())
            
    async def _ws_loop(self) -> None:
        """Persistent WebSocket connection loop for real-time orderbook updates."""
        while True:
            try:
                if not self._ws_session or self._ws_session.closed:
                    self._ws_session = aiohttp.ClientSession()
                
                logger.info(f"🔌 Connecting to Polymarket WebSocket... (tracking {len(self._active_tokens)} tokens)")
                async with self._ws_session.ws_connect(self._ws_url, heartbeat=30.0) as ws:
                    # Send subscription message
                    sub_msg = {
                        "assets_ids": list(self._active_tokens),
                        "type": "market"
                    }
                    await ws.send_json(sub_msg)
                    logger.success("🔊 Polymarket orderbook subscription active")
                    
                    async for msg in ws:
                        if msg.type == aiohttp.WSMsgType.TEXT:
                            await self._handle_ws_message(msg.data)
                        elif msg.type in (aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.ERROR):
                            logger.warning(f"WebSocket closed/error: {msg.type}")
                            break
                            
            except asyncio.CancelledError:
                logger.info("🛑 WebSocket tracking task cancelled")
                break
            except Exception as e:
                logger.error(f"WebSocket error: {e}")
                logger.debug(traceback.format_exc())
                
            # Reconnect backoff
            logger.info("🔄 Reconnecting WebSocket in 5 seconds...")
            await asyncio.sleep(5)
            
    async def _handle_ws_message(self, data: str) -> None:
        """Process incoming WebSocket tick and publish to Redis Pub/Sub."""
        try:
            payload = json_loads(data)
            
            # polymorphism handling based on Polymarket WS schema
            if isinstance(payload, list) and len(payload) > 0:
                for event in payload:
                    if event.get("event_type") == "price_change" or event.get("price"):
                        token = event.get("asset_id")
                        price = float(event.get("price", 0))
                        
                        if token and price > 0:
                            # Update Redis cache
                            cache_key = f"market:price:{token}"
                            await redis_client.cache_set(cache_key, str(price), ttl=3600)
                            
                            # Publish to Pub/Sub for realtime execution decoupling
                            channel = "market:price_update"
                            await redis_client.publish(channel, json_dumps({
                                "token": token,
                                "price": price,
                                "timestamp": datetime.now(timezone.utc).isoformat()
                            }))
                            
        except Exception as e:
            logger.error(f"Error handling WS message: {e}")


# Module singleton
scanner = MarketScanner()

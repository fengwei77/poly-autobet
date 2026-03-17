"""
Core: Weather Collector — fetches forecasts from multiple APIs concurrently via httpx.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Optional

import httpx
from loguru import logger

from config.settings import settings
from config.cities import CityConfig, CITIES
from data.models import WeatherForecast
from data.database import async_session
from infra.redis_client import redis_client
from infra.json_utils import json_dumps, json_loads


class WeatherCollector:
    """
    Fetches weather forecasts from NOAA, OpenWeatherMap, and Open-Meteo
    using httpx async parallel requests.
    """

    def __init__(self):
        self._http: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._http is None or self._http.is_closed:
            self._http = httpx.AsyncClient(
                timeout=20.0,
                follow_redirects=True,
            )
        return self._http

    async def close(self):
        if self._http and not self._http.is_closed:
            await self._http.aclose()

    # === Main Entry ===

    async def fetch_all_cities(self) -> dict[str, dict]:
        """Fetch weather for all configured cities in parallel."""
        tasks = [
            self.fetch_city_weather(city_id, cfg)
            for city_id, cfg in CITIES.items()
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        city_weather = {}
        for city_id, result in zip(CITIES.keys(), results):
            if isinstance(result, Exception):
                logger.error(f"Failed to fetch weather for {city_id}: {result}")
                continue
            city_weather[city_id] = result

        logger.info(f"🌡️ Fetched weather for {len(city_weather)}/{len(CITIES)} cities")
        return city_weather

    async def fetch_city_weather(self, city_id: str, city: CityConfig) -> dict:
        """Fetch weather from all available APIs for a single city."""
        # Check cache
        cache_key = f"weather:{city_id}"
        cached = await redis_client.cache_get(cache_key)
        if cached:
            return json_loads(cached)

        # Parallel fetch from all configured APIs
        api_tasks = {}
        for api in city.weather_apis:
            if api == "noaa" and city.country == "US":
                api_tasks["noaa"] = self._fetch_noaa(city)
            elif api == "openweathermap" and settings.openweathermap_api_key:
                api_tasks["owm"] = self._fetch_owm(city)
            elif api == "open_meteo":
                api_tasks["open_meteo"] = self._fetch_open_meteo(city)

        task_names = list(api_tasks.keys())
        results = await asyncio.gather(*api_tasks.values(), return_exceptions=True)

        forecasts = {}
        for name, result in zip(task_names, results):
            if isinstance(result, Exception):
                logger.warning(f"⚠️ {name} failed for {city_id}: {result}")
                continue
            if result:
                forecasts[name] = result

        # Cross-validate and merge
        merged = self._merge_forecasts(forecasts, city_id)

        # Cache for 30 minutes
        if merged:
            await redis_client.cache_set(cache_key, json_dumps(merged), ttl=1800)

        # Save to DB
        await self._save_forecasts(city_id, forecasts)

        return merged

    # === NOAA API ===

    async def _fetch_noaa(self, city: CityConfig) -> Optional[dict]:
        """Fetch from NOAA NWS API (US cities only, free, no key needed)."""
        client = await self._get_client()

        try:
            # Step 1: Get forecast URL from points endpoint
            points_resp = await client.get(
                f"https://api.weather.gov/points/{city.lat},{city.lon}",
                headers={"User-Agent": settings.noaa_user_agent},
            )
            points_resp.raise_for_status()
            forecast_url = points_resp.json()["properties"]["forecast"]

            # Step 2: Get actual forecast
            forecast_resp = await client.get(
                forecast_url,
                headers={"User-Agent": settings.noaa_user_agent},
            )
            forecast_resp.raise_for_status()
            periods = forecast_resp.json()["properties"]["periods"]

            # Parse first few periods
            result = {"source": "noaa", "periods": []}
            for period in periods[:6]:  # Next 3 days (day + night)
                result["periods"].append({
                    "name": period.get("name", ""),
                    "temperature": period.get("temperature"),
                    "unit": period.get("temperatureUnit", "F"),
                    "description": period.get("shortForecast", ""),
                    "wind_speed": period.get("windSpeed", ""),
                    "is_daytime": period.get("isDaytime", True),
                })

            # Extract high/low temps
            day_temps = [p["temperature"] for p in result["periods"] if p.get("is_daytime") and p.get("temperature")]
            night_temps = [p["temperature"] for p in result["periods"] if not p.get("is_daytime") and p.get("temperature")]

            result["temp_high_f"] = max(day_temps) if day_temps else None
            result["temp_low_f"] = min(night_temps) if night_temps else None

            # Convert F to C
            if result["temp_high_f"] is not None:
                result["temp_high_c"] = round((result["temp_high_f"] - 32) * 5 / 9, 1)
            if result["temp_low_f"] is not None:
                result["temp_low_c"] = round((result["temp_low_f"] - 32) * 5 / 9, 1)

            return result

        except Exception as e:
            logger.warning(f"NOAA API error for {city.name}: {e}")
            return None

    # === OpenWeatherMap API ===

    async def _fetch_owm(self, city: CityConfig) -> Optional[dict]:
        """Fetch from OpenWeatherMap (global, free tier 1000/day)."""
        client = await self._get_client()

        try:
            resp = await client.get(
                "https://api.openweathermap.org/data/2.5/forecast",
                params={
                    "lat": city.lat,
                    "lon": city.lon,
                    "appid": settings.openweathermap_api_key,
                    "units": "metric",
                    "cnt": 16,  # 48 hours at 3h intervals
                },
            )
            resp.raise_for_status()
            data = resp.json()

            forecasts = data.get("list", [])
            if not forecasts:
                return None

            # Extract temps from 3-hour intervals
            temps = [f["main"]["temp"] for f in forecasts if "main" in f]
            precip = sum(f.get("rain", {}).get("3h", 0) + f.get("snow", {}).get("3h", 0) for f in forecasts)

            return {
                "source": "owm",
                "temp_high_c": round(max(temps), 1) if temps else None,
                "temp_low_c": round(min(temps), 1) if temps else None,
                "precipitation_mm": round(precip, 1),
                "humidity": forecasts[0]["main"].get("humidity"),
                "wind_speed_kmh": round(forecasts[0].get("wind", {}).get("speed", 0) * 3.6, 1),
                "description": forecasts[0].get("weather", [{}])[0].get("description", ""),
            }

        except Exception as e:
            logger.warning(f"OWM API error for {city.name}: {e}")
            return None

    # === Open-Meteo API ===

    async def _fetch_open_meteo(self, city: CityConfig) -> Optional[dict]:
        """Fetch from Open-Meteo (global, free, no API key needed)."""
        client = await self._get_client()

        try:
            resp = await client.get(
                "https://api.open-meteo.com/v1/forecast",
                params={
                    "latitude": city.lat,
                    "longitude": city.lon,
                    "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,wind_speed_10m_max",
                    "timezone": city.timezone,
                    "forecast_days": 3,
                },
            )
            resp.raise_for_status()
            data = resp.json()

            daily = data.get("daily", {})
            if not daily.get("temperature_2m_max"):
                return None

            return {
                "source": "open_meteo",
                "temp_high_c": daily["temperature_2m_max"][0],
                "temp_low_c": daily["temperature_2m_min"][0],
                "precipitation_mm": daily.get("precipitation_sum", [0])[0],
                "wind_speed_kmh": daily.get("wind_speed_10m_max", [0])[0],
                "forecast_days": [
                    {
                        "date": daily["time"][i],
                        "high": daily["temperature_2m_max"][i],
                        "low": daily["temperature_2m_min"][i],
                        "precip": daily.get("precipitation_sum", [0] * 3)[i],
                    }
                    for i in range(min(3, len(daily["time"])))
                ],
            }

        except Exception as e:
            logger.warning(f"Open-Meteo API error for {city.name}: {e}")
            return None

    # === Merge & Validate ===

    def _merge_forecasts(self, forecasts: dict, city_id: str) -> dict:
        """Merge and cross-validate forecasts from multiple sources."""
        temps_high = []
        temps_low = []
        precips = []

        for source, data in forecasts.items():
            if data.get("temp_high_c") is not None:
                temps_high.append(data["temp_high_c"])
            if data.get("temp_low_c") is not None:
                temps_low.append(data["temp_low_c"])
            if data.get("precipitation_mm") is not None:
                precips.append(data["precipitation_mm"])

        merged = {
            "city": city_id,
            "sources": list(forecasts.keys()),
            "source_count": len(forecasts),
            "temp_high_c": round(sum(temps_high) / len(temps_high), 1) if temps_high else None,
            "temp_low_c": round(sum(temps_low) / len(temps_low), 1) if temps_low else None,
            "precipitation_mm": round(sum(precips) / len(precips), 1) if precips else None,
            "agreement": self._calculate_agreement(temps_high, temps_low),
            "raw": forecasts,
            "fetched_at": datetime.now(timezone.utc).isoformat(),
        }

        return merged

    def _calculate_agreement(self, highs: list[float], lows: list[float]) -> str:
        """Calculate agreement level between forecast sources."""
        if len(highs) < 2:
            return "single_source"
        spread = max(highs) - min(highs) if highs else 0
        if spread <= 2:
            return "high"
        elif spread <= 5:
            return "medium"
        else:
            return "low"

    # === DB ===

    async def _save_forecasts(self, city_id: str, forecasts: dict) -> None:
        """Save forecast data to database."""
        async with async_session() as session:
            for source, data in forecasts.items():
                if not data:
                    continue
                forecast = WeatherForecast(
                    city=city_id,
                    source=source,
                    forecast_date=datetime.now(timezone.utc),
                    temp_high=data.get("temp_high_c"),
                    temp_low=data.get("temp_low_c"),
                    precipitation_mm=data.get("precipitation_mm"),
                    wind_speed_kmh=data.get("wind_speed_kmh"),
                    humidity_pct=data.get("humidity"),
                    description=data.get("description", ""),
                )
                session.add(forecast)
            await session.commit()


# Module singleton
weather_collector = WeatherCollector()

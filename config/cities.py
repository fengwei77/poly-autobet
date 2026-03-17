"""
City configuration: coordinates, weather API mapping, timezone, and Polymarket tags.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CityConfig:
    name: str
    lat: float
    lon: float
    weather_apis: list[str]           # Which weather APIs cover this city
    polymarket_tags: list[str]        # Polymarket search tags
    timezone: str
    country: str


# fmt: off
CITIES: dict[str, CityConfig] = {
    "new_york": CityConfig(
        name="New York",
        lat=40.7128, lon=-74.0060,
        weather_apis=["noaa", "openweathermap", "open_meteo"],
        polymarket_tags=["nyc-temperature", "new-york-weather", "nyc-high"],
        timezone="America/New_York",
        country="US",
    ),
    "los_angeles": CityConfig(
        name="Los Angeles",
        lat=34.0522, lon=-118.2437,
        weather_apis=["noaa", "openweathermap", "open_meteo"],
        polymarket_tags=["la-temperature", "los-angeles-weather"],
        timezone="America/Los_Angeles",
        country="US",
    ),
    "chicago": CityConfig(
        name="Chicago",
        lat=41.8781, lon=-87.6298,
        weather_apis=["noaa", "openweathermap", "open_meteo"],
        polymarket_tags=["chicago-temperature", "chicago-weather"],
        timezone="America/Chicago",
        country="US",
    ),
    "miami": CityConfig(
        name="Miami",
        lat=25.7617, lon=-80.1918,
        weather_apis=["noaa", "openweathermap", "open_meteo"],
        polymarket_tags=["miami-temperature", "miami-weather"],
        timezone="America/New_York",
        country="US",
    ),
    "tokyo": CityConfig(
        name="Tokyo",
        lat=35.6762, lon=139.6503,
        weather_apis=["openweathermap", "open_meteo"],
        polymarket_tags=["tokyo-temperature", "tokyo-weather"],
        timezone="Asia/Tokyo",
        country="JP",
    ),
    "london": CityConfig(
        name="London",
        lat=51.5074, lon=-0.1278,
        weather_apis=["openweathermap", "open_meteo"],
        polymarket_tags=["london-temperature", "london-weather"],
        timezone="Europe/London",
        country="GB",
    ),
    "austin": CityConfig(
        name="Austin",
        lat=30.2672, lon=-97.7431,
        weather_apis=["noaa", "openweathermap", "open_meteo"],
        polymarket_tags=["austin-temperature", "austin-weather"],
        timezone="America/Chicago",
        country="US",
    ),
    "denver": CityConfig(
        name="Denver",
        lat=39.7392, lon=-104.9903,
        weather_apis=["noaa", "openweathermap", "open_meteo"],
        polymarket_tags=["denver-temperature", "denver-weather"],
        timezone="America/Denver",
        country="US",
    ),
    "san_francisco": CityConfig(
        name="San Francisco",
        lat=37.7749, lon=-122.4194,
        weather_apis=["noaa", "openweathermap", "open_meteo"],
        polymarket_tags=["sf-temperature", "san-francisco-weather", "sfo"],
        timezone="America/Los_Angeles",
        country="US",
    ),
    "washington-dc": CityConfig(
        name="Washington DC",
        lat=38.9072, lon=-77.0369,
        weather_apis=["noaa", "openweathermap", "open_meteo"],
        polymarket_tags=["dc-temperature", "washington-weather", "washington-dc"],
        timezone="America/New_York",
        country="US",
    ),
    "seattle": CityConfig(
        name="Seattle",
        lat=47.6062, lon=-122.3321,
        weather_apis=["noaa", "openweathermap", "open_meteo"],
        polymarket_tags=["seattle-temperature", "seattle-weather"],
        timezone="America/Los_Angeles",
        country="US",
    ),
    "houston": CityConfig(
        name="Houston",
        lat=29.7604, lon=-95.3698,
        weather_apis=["noaa", "openweathermap", "open_meteo"],
        polymarket_tags=["houston-temperature", "houston-weather"],
        timezone="America/Chicago",
        country="US",
    ),
    "phoenix": CityConfig(
        name="Phoenix",
        lat=33.4484, lon=-112.0740,
        weather_apis=["noaa", "openweathermap", "open_meteo"],
        polymarket_tags=["phoenix-temperature", "phoenix-weather"],
        timezone="America/Phoenix",
        country="US",
    ),
    "philadelphia": CityConfig(
        name="Philadelphia",
        lat=39.9526, lon=-75.1652,
        weather_apis=["noaa", "openweathermap", "open_meteo"],
        polymarket_tags=["philly-temperature", "philadelphia-weather", "phl"],
        timezone="America/New_York",
        country="US",
    ),
    "paris": CityConfig(
        name="Paris",
        lat=48.8566, lon=2.3522,
        weather_apis=["openweathermap", "open_meteo"],
        polymarket_tags=["paris-temperature", "paris-weather"],
        timezone="Europe/Paris",
        country="FR",
    ),
    "berlin": CityConfig(
        name="Berlin",
        lat=52.5200, lon=13.4050,
        weather_apis=["openweathermap", "open_meteo"],
        polymarket_tags=["berlin-temperature", "berlin-weather"],
        timezone="Europe/Berlin",
        country="DE",
    ),
    "sydney": CityConfig(
        name="Sydney",
        lat=-33.8688, lon=151.2093,
        weather_apis=["openweathermap", "open_meteo"],
        polymarket_tags=["sydney-temperature", "sydney-weather"],
        timezone="Australia/Sydney",
        country="AU",
    ),
}
# fmt: on


def get_city(city_id: str) -> CityConfig | None:
    return CITIES.get(city_id)


def get_all_cities() -> dict[str, CityConfig]:
    return CITIES

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.scanner import scanner
from core.city_resolver import city_resolver
from data.database import async_session
from data.models import Market
from sqlalchemy import select
from loguru import logger

async def debug_city_resolution():
    logger.info("🕵️ Debugging City Resolution...")
    
    async with async_session() as session:
        result = await session.execute(select(Market).limit(20))
        markets = result.scalars().all()
        
        if not markets:
            logger.warning("No markets found in DB. Running a fresh scan...")
            raw_markets = await scanner.scan_weather_markets()
            # scanner already saves to DB
            result = await session.execute(select(Market).limit(20))
            markets = result.scalars().all()

        logger.info(f"Checking {len(markets)} markets...")
        for m in markets:
            # Re-try resolution
            text = f"{m.question} | {m.market_slug}"
            resolved = await city_resolver.resolve_city(text)
            logger.info(f"Question: {m.question[:50]}...")
            logger.info(f"  Current DB City: {m.city}")
            logger.info(f"  Re-resolved: {resolved}")
            logger.info("-" * 40)

if __name__ == "__main__":
    asyncio.run(debug_city_resolution())

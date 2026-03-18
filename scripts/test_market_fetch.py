import asyncio
import sys
import os
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.scanner import scanner
from infra.redis_client import redis_client
from loguru import logger

async def test_market_fetch():
    logger.info("🚀 Starting Polymarket market fetch test...")
    
    # Ensure Redis is connected
    await redis_client.connect()
    
    # 1. Clear cache to force a fresh fetch from Gamma API
    logger.info("🧹 Clearing market cache to force fresh scan...")
    # Based on infra/redis_client.py, we should use the internal client or wait for a public method
    # Let's check redis_client.py for the correct deletion method
    if hasattr(redis_client, 'cache_delete'):
        await redis_client.cache_delete("markets:weather:all")
    else:
        # Fallback to internal access if needed, but carefully
        await redis_client._client.delete("markets:weather:all")
    
    # 2. Perform scan
    markets = await scanner.scan_weather_markets()
    
    logger.info("="*60)
    if markets:
        logger.success(f"✅ Successfully fetched {len(markets)} weather markets!")
        
        # Display top 5 markets
        for i, m in enumerate(markets[:5], 1):
            logger.info(f"[{i}] City: {m.get('city', 'Unknown')} | Question: {m.get('question', '')[:60]}...")
            logger.info(f"    Price: {m.get('yes_price')} | Volume: ${m.get('volume'):,.2f}")
    else:
        logger.error("❌ No weather markets found. Check keywords in core/scanner.py or Polymarket Gamma API status.")
    logger.info("="*60)
    
    # Cleanup
    await redis_client.close()
    await scanner.close()

if __name__ == "__main__":
    asyncio.run(test_market_fetch())

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.ai_analyzer import ai_analyzer
from config.settings import settings
from loguru import logger

async def test_ai_availability():
    logger.info("🧪 Testing AI model availability...")
    logger.info(f"Current default provider: {settings.ai_provider}")
    
    # 1. Test City Extraction (Fast)
    logger.info("Testing City Extraction (extract_city)...")
    text = "Will it rain in Singapore tomorrow?"
    city = await ai_analyzer.extract_city(text)
    if city:
        logger.success(f"✅ City Extraction Success: {city}")
    else:
        logger.error("❌ City Extraction Failed")

    # 2. Test Full Analysis
    logger.info("Testing Full Analysis (analyze_opportunity)...")
    market = {
        "question": "Will it rain in New York on March 18?",
        "yes_price": 0.35,
        "volume": 5000,
        "city": "new_york",
        "condition_id": "test_id_123"
    }
    weather = {
        "temp_high_c": 15,
        "temp_low_c": 8,
        "precipitation_mm": 2.5,
        "agreement": "high",
        "source_count": 3
    }
    
    try:
        result = await ai_analyzer.analyze_opportunity(market, weather)
        if result:
            logger.success(f"✅ Analysis Success via Source: {result.get('source')}")
            logger.info(f"   Signal: {result.get('signal')} | Edge: {result.get('edge')}")
            logger.info(f"   Reasoning: {result.get('reasoning')[:100]}...")
        else:
            logger.error("❌ Analysis returned None")
    except Exception as e:
        logger.error(f"❌ Analysis crashed: {e}")

if __name__ == "__main__":
    asyncio.run(test_ai_availability())

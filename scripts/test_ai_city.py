import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.ai_analyzer import ai_analyzer
from loguru import logger

async def test_ai_extraction():
    logger.info("🤖 Testing AI City Extraction...")
    
    test_cases = [
        "Will it rain in New York tomorrow?",
        "Daily Temperature: Chicago - high > 85F?",
        "March 18 Rain: LONDON | Will it rain?",
        "Hurricane Milton track toward Tampa",
    ]
    
    for text in test_cases:
        resolved = await ai_analyzer.extract_city(text)
        logger.info(f"Input: {text}")
        logger.info(f"  Extracted: {resolved}")
        logger.info("-" * 40)

if __name__ == "__main__":
    asyncio.run(test_ai_extraction())

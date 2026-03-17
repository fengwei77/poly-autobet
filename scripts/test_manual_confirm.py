
import asyncio
import sys
import os
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import settings
from core.trade_executor import trade_executor
from loguru import logger
from infra.redis_client import redis_client

async def test_manual_flow():
    # Force localhost connection if running on Windows host
    await redis_client.connect()
    if not redis_client.connected:
        logger.warning("Connection to default failed, trying localhost explicitly...")
        redis_client._url = "redis://localhost:6379"
        await redis_client.connect()
    
    if not redis_client.connected:
        logger.error("Could not connect to Redis. Manual approval signal will not work across containers!")
        return
    
    # Mock data
    market = {
        "condition_id": "test_signal_123",
        "question": "TEST: Will it rain in Taipei on March 20th?",
        "yes_price": 0.45,
        "tokens": "token_yes_123,token_no_123",
        "city": "Taipei"
    }
    
    analysis = {
        "signal": "BUY",
        "edge": 0.15,
        "confidence": 85,
        "suggested_size_usdc": 10.0
    }
    
    # IMPORTANT: Initialize notifier so it can send buttons
    from notifications.telegram_bot import notifier
    await notifier.initialize()
    
    logger.info("🚀 Triggering execute_semi_auto...")
    
    # This should send buttons to Telegram and wait for Redis signal
    result = await trade_executor.execute(analysis, market)
    
    if result:
        logger.success(f"🏁 Final Result: {result}")
    else:
        logger.warning("🏁 No result returned (possibly HOLD signal)")
        
    await redis_client.close()

if __name__ == "__main__":
    if settings.trading_strategy != "semi-auto":
        logger.error("Please set TRADING_STRATEGY=semi-auto in .env first!")
    else:
        asyncio.run(test_manual_flow())

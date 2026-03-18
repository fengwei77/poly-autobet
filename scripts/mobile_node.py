"""
POLY DREAM: Mobile Execution Node (Termux/UserLAnd)
Listens to Redis Pub/Sub for trade signals and executes them locally to minimize latency
and keep private keys secure on the mobile device.
"""

from __future__ import annotations

import asyncio
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import click
from loguru import logger

from config.settings import settings, NodeRole
from infra.redis_client import redis_client
from infra.json_utils import json_loads
from infra.event_loop import setup_event_loop


async def handle_trade_signal(message_data: str):
    """Callback for when a trade signal is received from Redis."""
    from core.trade_executor import trade_executor
    
    try:
        payload = json_loads(message_data)
        market = payload.get("market")
        analysis = payload.get("analysis")
        
        if not market or not analysis:
            logger.error("Invalid payload received from brain")
            return
            
        logger.info(f"⚡ Received delegated trade: {analysis.get('signal')} for {market.get('question', '')[:40]}")
        
        # Execute the trade (this handles locking to prevent duplicates)
        result = await trade_executor.execute(analysis, market)
        
        if result and result.get("status") == "filled":
            logger.success(f"✅ Delegated trade executed: {result}")
        elif result and result.get("status") == "blocked":
            logger.warning(f"⛔ Delegated trade blocked: {result.get('reason')}")
            
    except Exception as e:
        logger.error(f"Error handling trade signal: {e}")


async def mobile_node_loop():
    """Main loop for the mobile executor node."""
    from infra.event_loop import detect_environment
    from data.database import init_db
    
    env = detect_environment()
    logger.info("📱 POLY DREAM Mobile Execution Node Starting...")
    logger.info(f"   Platform: {env['platform']} ({env['architecture']})")
    
    # Initialize infrastructure
    await init_db()
    await redis_client.connect()
    
    # Needs to be initialized for CLOB client
    from core.trade_executor import trade_executor
    await trade_executor._init_clob_client()
    
    channel = "signal:trade_execute"
    logger.info(f"🎧 Listening to Redis channel: {channel}")
    
    pubsub = redis_client._client.pubsub()
    await pubsub.subscribe(channel)
    
    try:
        async for message in pubsub.listen():
            if message["type"] == "message":
                logger.info("New message received on channel")
                await handle_trade_signal(message["data"])
    except asyncio.CancelledError:
        logger.info("Mobile node shutting down...")
    finally:
        await pubsub.unsubscribe(channel)
        await redis_client.close()


@click.command()
@click.option("--redis-url", default=None, help="Override Redis URL")
def main(redis_url: str | None):
    """Start the mobile execution node."""
    if redis_url:
        os.environ["REDIS_URL"] = redis_url
        settings.__init__()
        
    # Force role to executor
    os.environ["NODE_ROLE"] = "executor"
    settings.__init__()
    
    setup_event_loop()
    
    try:
        asyncio.run(mobile_node_loop())
    except KeyboardInterrupt:
        logger.info("Shutting down cleanly via keyboard interrupt")


if __name__ == "__main__":
    main()

"""
Poly-AutoBet: Main Entry Point
Orchestrates all system components: scanning, analysis, trading, and monitoring.
"""

from __future__ import annotations

import asyncio
import signal
import sys

import click
from loguru import logger
from data.database import close_db

# Configure loguru
logger.remove()
logger.add(
    sys.stderr,
    format="<green>{time:HH:mm:ss}</green> | <level>{level:^8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>",
    level="INFO",
)
logger.add(
    "logs/polybet_{time:YYYY-MM-DD}.log",
    rotation="1 day",
    retention="30 days",
    level="DEBUG",
    encoding="utf-8",
)


async def run_scan_cycle():
    """Single scan-analyze-trade cycle."""
    from core.scanner import scanner
    from core.weather_collector import weather_collector
    from core.ai_analyzer import ai_analyzer
    from core.trade_executor import trade_executor
    from config.settings import settings

    # Step 1: Scan markets
    logger.info("=" * 60)
    logger.info("🔍 Scanning Polymarket weather markets...")
    markets = await scanner.scan_weather_markets()
    logger.info(f"Found {len(markets)} weather markets")

    if not markets:
        logger.info("No weather markets found, waiting for next cycle...")
        return

    # Step 2: Fetch weather data
    logger.info("🌡️ Fetching weather forecasts...")
    weather_data = await weather_collector.fetch_all_cities()

    # Step 3: Analyze and Filter markets
    # Note: scanner.scan_weather_markets() now saves EVERYTHING to the DB for visibility.
    # We only trade on high-volume, identified cities.
    active_liquid = [m for m in markets if m["volume"] > 100.0 and m["city"] != "unknown"]
    active_liquid.sort(key=lambda x: x["volume"], reverse=True)
    top_targets = active_liquid[:200]
    
    logger.info(f"🎯 Selected {len(top_targets)} high-quality targets for deep analysis")

    opportunities = []
    for market in top_targets:
        city = market.get("city")
        if not city or city not in weather_data:
            continue

        weather = weather_data[city]
        analysis = await ai_analyzer.analyze_opportunity(market, weather)

        if analysis and analysis.get("signal") != "HOLD":
            opportunities.append((market, analysis))
            logger.info(
                f"🎯 {analysis['signal']} | {market.get('question', '')[:50]} | "
                f"edge={analysis['edge']:.1%} conf={analysis['confidence']}"
            )

    logger.info(f"📊 Found {len(opportunities)} trading opportunities")

    # Step 4: Execute trades (or delegate to mobile node)
    for market, analysis in opportunities:
        if settings.delegate_execution and settings.node_role.value == "brain":
            # Publish to Redis for the executor node
            payload = {
                "market": market,
                "analysis": analysis
            }
            from infra.redis_client import redis_client
            from infra.json_utils import json_dumps
            await redis_client._client.publish("signal:trade_execute", json_dumps(payload))
            logger.info(f"📤 Delegated trade to executor node via Redis: {analysis.get('signal')}")
        else:
            # Execute locally
            result = await trade_executor.execute(analysis, market)
            if result and result.get("status") == "filled":
                logger.info(f"✅ Trade executed: {result}")
            elif result and result.get("status") == "blocked":
                logger.info(f"⛔ Trade blocked: {result.get('reason')}")


async def market_price_listener_loop(shutdown_event: asyncio.Event):
    """Listens to real-time price tick updates from scanner's WebSocket stream."""
    from infra.redis_client import redis_client
    from infra.json_utils import json_loads
    from config.settings import settings
    
    # We delay imports to prevent circular dependencies at module load
    from core.ai_analyzer import ai_analyzer
    from core.trade_executor import trade_executor
    from core.position_manager import position_manager
    from infra.json_utils import json_dumps
    
    channel = "market:price_update"
    pubsub = redis_client._client.pubsub()
    await pubsub.subscribe(channel)
    
    logger.info("🎧 Real-time market price listener active")
    
    try:
        while not shutdown_event.is_set():
            message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
            if not message:
                continue
                
            try:
                raw_data = message.get("data")
                if not isinstance(raw_data, (str, bytes)):
                    logger.debug(f"Ignoring non-payload message: {type(raw_data)}")
                    continue
                    
                payload = json_loads(raw_data)
                token = payload.get("token")
                new_price = payload.get("price")
                
                if not token or not new_price:
                    continue
                    
                # 1. Fetch market payload
                market_str = await redis_client.cache_get(f"market:mapping:{token}")
                if not market_str:
                    continue
                    
                market_data = json_loads(market_str)
                market_data["yes_price"] = new_price  # Update with latest real-time price
                
                # 2. Fetch weather for market's city
                city = market_data.get("city")
                if not city or city == "unknown":
                    continue
                
                # 3. Quick scalping check on existing open positions (Check Take Profit / Stop Loss)
                if settings.trading_mode.value == "paper":
                    condition_id = market_data.get("condition_id")
                    if condition_id:
                        asyncio.create_task(position_manager.scan_positions_for_exit(condition_id, new_price))
                        
                weather_str = await redis_client.cache_get(f"weather:{city}")
                if not weather_str:
                    continue
                    
                weather_data = json_loads(weather_str)
                
                # 4. Quick analyze (Statistical filter runs first, AI only if edge > threshold)
                analysis = await ai_analyzer.analyze_opportunity(market_data, weather_data)
                
                if analysis and analysis.get("signal") != "HOLD":
                    logger.success(
                        f"⚡ [REAL-TIME] {analysis['signal']} | {market_data.get('question', '')[:50]} | "
                        f"edge={analysis['edge']:.1%} conf={analysis['confidence']}"
                    )
                    
                    # 4. Execute or delegate trade
                    if settings.delegate_execution and settings.node_role.value == "brain":
                        trade_payload = {
                            "market": market_data,
                            "analysis": analysis
                        }
                        await redis_client._client.publish("signal:trade_execute", json_dumps(trade_payload))
                        logger.info(f"📤 Delegated real-time trade to executor node via Redis")
                    else:
                        result = await trade_executor.execute(analysis, market_data)
                        if result and result.get("status") == "filled":
                            logger.info(f"✅ Real-time trade executed: {result}")
                            
            except Exception as e:
                logger.error(f"Error processing real-time tick: {e}")
                
    except asyncio.CancelledError:
        pass
    finally:
        await pubsub.unsubscribe(channel)


async def manual_scan_listener(shutdown_event: asyncio.Event):
    """Listens for manual scan triggers from Redis (usually from dashboard)."""
    from infra.redis_client import redis_client
    
    channel = "signal:manual_scan"
    pubsub = redis_client._client.pubsub()
    await pubsub.subscribe(channel)
    
    logger.info("🎧 Manual scan listener active")
    
    try:
        while not shutdown_event.is_set():
            message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
            if not message:
                continue
            
            logger.info("⚡ [MANUAL] Triggering immediate scan cycle via Redis signal")
            asyncio.create_task(run_scan_cycle())
            
    except asyncio.CancelledError:
        pass
    finally:
        await pubsub.unsubscribe(channel)


async def notification_loop(shutdown_event: asyncio.Event):
    """Listens for internal signals and sends Telegram/system notifications."""
    from infra.redis_client import redis_client
    from infra.json_utils import json_loads
    from notifications.telegram_bot import notifier

    # Initialize Telegram Bot
    await notifier.initialize()
    
    channel = "signal:trade_result"
    pubsub = redis_client._client.pubsub()
    await pubsub.subscribe(channel)
    
    logger.info("📱 Notification listener active (Telegram)")
    
    try:
        while not shutdown_event.is_set():
            message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
            if not message:
                continue
                
            try:
                # Check message type before accessing data
                if message.get("type") != "message":
                    continue
                raw_data = message.get("data")
                if not raw_data:
                    continue
                result = json_loads(raw_data)
                # Send to Telegram
                await notifier.notify_trade(result)
            except Exception as e:
                logger.error(f"Error in notification loop: {e}")
                
    except asyncio.CancelledError:
        pass
    finally:
        await pubsub.unsubscribe(channel)


async def main_loop():
    """Main async event loop — runs continuous scan cycles."""
    from config.settings import settings
    from data.database import init_db
    from infra.redis_client import redis_client
    from infra.event_loop import detect_environment

    # Log environment info
    env = detect_environment()
    logger.info("🚀 POLY DREAM Starting...")
    logger.info(f"   Platform: {env['platform']} ({env['architecture']})")
    logger.info(f"   Python: {env['python_version']}")
    logger.info(f"   uvloop: {'✅' if env['uvloop_available'] else '❌'}")
    logger.info(f"   orjson: {'✅' if env['orjson_available'] else '❌'}")
    logger.info(f"   Mode: {settings.trading_mode.value}")
    logger.info(f"   Role: {settings.node_role.value}")

    # Initialize services
    missing = settings.validate()
    if missing:
        logger.warning(f"⚠️ Missing critical settings: {', '.join(missing)}")
        if settings.is_live:
            logger.critical("❌ LIVE trading will fail without these keys!")
            
    await init_db()
    await redis_client.connect()

    logger.info("=" * 60)
    logger.info(f"🎮 Running in {settings.trading_mode.value.upper()} mode")
    logger.info(f"   Max daily exposure: ${settings.max_daily_exposure}")
    logger.info(f"   Max single bet: ${settings.max_single_bet}")
    logger.info(f"   Min edge: {settings.min_edge:.0%}")
    logger.info(f"   Scan interval: {settings.scan_interval_minutes} min")
    logger.info("=" * 60)

    # Graceful shutdown
    shutdown_event = asyncio.Event()

    def handle_signal(*_):
        logger.info("🛑 Shutdown signal received...")
        shutdown_event.set()

    # Register signal handlers (Unix only)
    try:
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, handle_signal)
    except (NotImplementedError, AttributeError):
        # Windows doesn't support add_signal_handler
        pass

    # Start background tasks
    listener_task = asyncio.create_task(market_price_listener_loop(shutdown_event))
    notif_task = asyncio.create_task(notification_loop(shutdown_event))
    manual_scan_task = asyncio.create_task(manual_scan_listener(shutdown_event))
    
    # Order Status tracking for Live mode
    from core.trade_executor import trade_executor
    executor_track_task = asyncio.create_task(trade_executor.start_order_status_tracking())

    # Main loop (periodic baseline)
    try:
        cycle = 0
        while not shutdown_event.is_set():
            cycle += 1
            try:
                logger.info(f"\n🔄 Cycle #{cycle}")
                await run_scan_cycle()
            except Exception as e:
                logger.error(f"Cycle error: {e}")

            # Wait for next cycle or shutdown
            try:
                await asyncio.wait_for(
                    shutdown_event.wait(),
                    timeout=settings.scan_interval_minutes * 60,
                )
                break  # Shutdown requested
            except asyncio.TimeoutError:
                continue  # Next cycle
    finally:
        # Cleanup
        listener_task.cancel()
        notif_task.cancel()
        executor_track_task.cancel()
        try:
            await asyncio.gather(listener_task, notif_task, manual_scan_task, executor_track_task, return_exceptions=True)
        except Exception as e:
            logger.debug(f"Task cancellation: {e}")

        try:
            from core.scanner import scanner
            if scanner:
                await scanner.close()
        except Exception as e:
            logger.warning(f"Error closing scanner: {e}")

        try:
            from core.weather_collector import weather_collector
            if weather_collector:
                await weather_collector.close()
        except Exception as e:
            logger.warning(f"Error closing weather_collector: {e}")

        await redis_client.close()
        await close_db()
        logger.info("👋 POLY DREAM shutdown complete.")


@click.command()
@click.option("--mode", type=click.Choice(["monitor", "paper", "live", "backtest"]), default=None)
def cli(mode: str | None):
    """POLY DREAM: Polymarket Weather Market Auto-Betting System"""
    from infra.event_loop import setup_event_loop
    from config.settings import settings

    # Override mode from CLI if provided
    if mode:
        import os
        os.environ["TRADING_MODE"] = mode
        # Reload settings
        from config.settings import reload_settings
        reload_settings()

    setup_event_loop()
    asyncio.run(main_loop())


if __name__ == "__main__":
    cli()

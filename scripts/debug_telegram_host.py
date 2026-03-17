
import asyncio
import sys
import os
from pathlib import Path

# Add project root to sys.path
sys.path.append(str(Path(__file__).parent.parent))

from config.settings import settings
from notifications.telegram_bot import notifier
from loguru import logger

async def persistent_test():
    """
    啟動一個更穩定的測試，持續監聽並打印每一個連線動作。
    """
    logger.info("📡 [核心診斷] 啟動長效監聽測試 (主機模式)...")
    logger.info(f"Target Token: {settings.telegram_bot_token[:8]}***")
    
    # 設置環境變數強制更高的超時（有些網路環境需要）
    os.environ["HTTPX_TIMEOUT"] = "60"

    # 初始化 bot
    await notifier.initialize()
    
    # 持續運行並監控
    market_id = "final_debug_host"
    mock_market = {"condition_id": market_id, "question": "主機連線深度診斷測"}
    mock_analysis = {"signal": "BUY", "confidence": 99, "edge": 0.5, "suggested_size_usdc": 1}
    
    logger.info("📤 嘗試推播測試訊息...")
    success = await notifier.notify_opportunity_with_buttons(mock_market, mock_analysis)
    
    if success:
        logger.success("✅ 訊息推播成功！監聽器現在正處於 Polling 核心循環中。")
    else:
        logger.warning("⚠️ 推播失敗（可能是網路擁塞），但 Polling 監聽器應仍會嘗試背景啟動。")

    logger.info("📺 正在實時輸出 Polling 日誌（請勿關閉終端，等待約 30-60 秒）...")
    
    # 保持主線程運行
    counter = 0
    while True:
        await asyncio.sleep(10)
        counter += 10
        logger.debug(f"⏱️ 監聽器已運行 {counter}s...")
        if counter > 300: # 5 mins
            break

if __name__ == "__main__":
    try:
        asyncio.run(persistent_test())
    except KeyboardInterrupt:
        logger.info("停止測試。")

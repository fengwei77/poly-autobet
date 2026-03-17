
import asyncio
import sys
import os
from pathlib import Path

# Add project root to sys.path
sys.path.append(str(Path(__file__).parent.parent))

from config.settings import settings
from notifications.telegram_bot import notifier
from loguru import logger

async def test_interactive_trade():
    """
    模擬發送一個需要手動審核的交易機會到 Telegram。
    """
    logger.info("🚀 啟動 Telegram 互動測試 (手動審核模式)...")
    
    # 初始化 bot 並強制等待完成
    await notifier.initialize()
    # 直接等待內部設定完成，確保測試時 bot 已可用
    if hasattr(notifier, '_setup_async'):
        logger.info("⏳ 正在強制等待 Telegram 背景初始化...")
        # 這裡我們等待一小段時間讓背景任務有機會開始執行
        await asyncio.sleep(1)
    
    # 模擬市場數據
    mock_market = {
        "condition_id": "test_cond_123",
        "question": "測試市場: 紐約明天會下雨嗎？ (及時互動測試)",
        "city": "new-york"
    }
    
    # 模擬分析結果
    mock_analysis = {
        "signal": "YES",
        "confidence": 85,
        "edge": 0.12,
        "suggested_size_usdc": 10.0,
        "price": 0.45,
        "reasoning": "AI 預測有 80% 機率降雨，盤口價格 0.45 具有顯著優勢。"
    }
    
    logger.info("📤 正在發送互動式訊息到 Telegram...")
    # 調用修正後的雙參數方法
    success = await notifier.notify_opportunity_with_buttons(mock_market, mock_analysis)
    
    if success:
        logger.success("✅ 訊息已發送！請檢查您的 Telegram 並嘗試點擊 [批准] 或 [拒絕]。")
        logger.info("⏳ 腳本將保持運行 120 秒，等待您的點擊反饋...")
        await asyncio.sleep(120)
    else:
        logger.error("❌ 訊息發送失敗，請檢查 .env 中的 TELEGRAM_BOT_TOKEN 和 CHAT_ID。")

if __name__ == "__main__":
    if not settings.telegram_bot_token or settings.telegram_bot_token == "your_telegram_token":
        logger.error("錯誤: 請先在 .env 中設置正確的 TELEGRAM_BOT_TOKEN。")
    else:
        asyncio.run(test_interactive_trade())

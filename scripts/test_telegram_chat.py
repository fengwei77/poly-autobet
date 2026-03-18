
import asyncio
import sys
import json
import os
from pathlib import Path

# Add project root to sys.path
sys.path.append(str(Path(__file__).parent.parent))

from config.settings import settings
from notifications.telegram_bot import notifier
from loguru import logger

async def test_telegram_chat():
    """
    模擬發送普通文字訊息（非指令）到 Telegram Webhook。
    """
    logger.info("🚀 啟動 Telegram AI Chat 測試...")
    
    # 確保 Notifier 已初始化
    await notifier.initialize()
    await asyncio.sleep(2) # 等待背景任務
    
    # 模擬 Telegram Webhook Update JSON (普通文字訊息)
    mock_update = {
        "update_id": 987654321,
        "message": {
            "message_id": 2,
            "from": {
                "id": int(settings.telegram_chat_id) if settings.telegram_chat_id.isdigit() else 12345,
                "is_bot": False,
                "first_name": "TestUser",
                "username": "testuser"
            },
            "chat": {
                "id": int(settings.telegram_chat_id) if settings.telegram_chat_id.isdigit() else 12345,
                "first_name": "TestUser",
                "type": "private"
            },
            "date": 1640000000,
            "text": "目前的投資回報如何？有哪些值得關注的市場？"
        }
    }
    
    body = json.dumps(mock_update).encode('utf-8')
    secret = getattr(settings, "telegram_webhook_secret", "")
    
    logger.info("📥 注入模擬聊天訊息...")
    
    # 注意：在測試環境中，這會觸發 AIAnalyzer 並嘗試發送回覆
    success = await notifier.process_webhook_update(body, secret)
    
    if success:
        logger.success("✅ Chat Webhook 處理成功！請檢查控制台日誌或 Telegram。")
    else:
        logger.error("❌ Chat Webhook 處理失敗。")

if __name__ == "__main__":
    asyncio.run(test_telegram_chat())

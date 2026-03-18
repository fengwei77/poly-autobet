
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

async def test_telegram_status_command():
    """
    模擬發送 /status 指令到 Telegram Webhook。
    """
    logger.info("🚀 啟動 Telegram /status 指令測試...")
    
    # 確保 Notifier 已初始化
    await notifier.initialize()
    await asyncio.sleep(2) # 等待背景任務
    
    # 模擬 Telegram Webhook Update JSON
    # 這裡的 chat_id, text 等需要符合 Telegram Update 格式
    mock_update = {
        "update_id": 123456789,
        "message": {
            "message_id": 1,
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
            "text": "/status",
            "entities": [
                {"offset": 0, "length": 7, "type": "bot_command"}
            ]
        }
    }
    
    body = json.dumps(mock_update).encode('utf-8')
    secret = getattr(settings, "telegram_webhook_secret", "")
    
    logger.info("📥 注入模擬 Webhook 封包 (/status)...")
    
    # 注意：在測試環境中，process_update 會嘗試調用 Telegram API 發送回覆 (reply_text)
    # 如果 TOKEN 正確且能連上網路，這會真的發送一條訊息到您的手機。
    success = await notifier.process_webhook_update(body, secret)
    
    if success:
        logger.success("✅ Webhook 處理成功！請檢查您的 Telegram 是否收到狀態報告。")
    else:
        logger.error("❌ Webhook 處理失敗。")

if __name__ == "__main__":
    if not settings.telegram_bot_token or settings.telegram_bot_token == "your_telegram_token":
        logger.error("錯誤: 請先在 .env 中設置正確的 TELEGRAM_BOT_TOKEN。")
    else:
        asyncio.run(test_telegram_status_command())

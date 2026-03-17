
import asyncio
import sys
import os
import requests
from pathlib import Path

# Add project root to sys.path
sys.path.append(str(Path(__file__).parent.parent))

from config.settings import settings
from loguru import logger

def send_test_with_requests():
    """
    使用同步 Requests 直接發送帶有按鈕的訊息，避開異步衝突。
    由背景運行的 poly-autobet 容器處理點擊。
    """
    token = settings.telegram_bot_token
    chat_id = settings.telegram_chat_id
    
    if not token or not chat_id:
        logger.error("TOKEN or CHAT_ID missing in .env")
        return

    market_id = "test_interaction_final"
    msg = (
        "🧪 <b>最終互動連通性測試</b>\n\n"
        "這則訊息由獨立腳本發送，應由背景容器處理按鈕。\n"
        "請點擊下方按鈕進行驗證。"
    )
    
    kb = {
        "inline_keyboard": [[
            {"text": "✅ 測試核准", "callback_data": f"approve:{market_id}"},
            {"text": "❌ 測試忽略", "callback_data": f"reject:{market_id}"}
        ]]
    }
    
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": msg,
        "parse_mode": "HTML",
        "reply_markup": kb
    }
    
    logger.info("📤 正在發送測試按鈕...")
    resp = requests.post(url, json=payload, timeout=10)
    if resp.status_code == 200:
        logger.success("✅ 發送成功！請在 Telegram 點擊按鈕，並觀察 docker logs poly-autobet 的輸出。")
    else:
        logger.error(f"❌ 發送失敗: {resp.text}")

if __name__ == "__main__":
    send_test_with_requests()

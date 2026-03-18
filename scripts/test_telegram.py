import asyncio
import os
import sys

# Add app to path
sys.path.insert(0, os.getcwd())

from notifications.telegram_bot import notifier

async def run_test():
    print("Initializing Telegram Bot...")
    await notifier.initialize()
    print("Sending test message...")
    success = await notifier.send("🔔 <b>POLY DREAM 手動測試</b>\n\n如果您收到此訊息，表示您的 Telegram Bot 與 Chat ID 設定完全正確！\n\n目前系統已進入自動化監控狀態，祝您投資獲利！")
    
    if success:
        print("✅ 測試訊息發送成功！請檢查您的 Telegram 手機 App。")
    else:
        print("❌ 發送失敗，請檢查 .env 中的 TOKEN 與 CHAT_ID 是否正確。")

if __name__ == "__main__":
    asyncio.run(run_test())

import asyncio
import sys
import os
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from notifications.telegram_bot import notifier

async def main():
    print("🚀 Triggering Webhook Test Message...")
    
    # Initialize the notifier (this will skip setup because WEBHOOK doesn't need polling)
    await notifier.initialize()
    
    # Wait for bot to be ready (it's initialized in a background task)
    print("⏳ Waiting for Telegram Bot to initialize...")
    for i in range(15):
        if notifier._bot:
            print(f"✅ Bot initialized after {i}s")
            break
        await asyncio.sleep(1)
    
    if not notifier._bot:
        print("❌ Bot not initialized within 15s. Check network or token.")
        # Try to show the error if possible
        return

    test_market = {
        "condition_id": "webhook_test_999",
        "question": "Webhook 整合測試：您能看到這條訊息並點擊按鈕嗎？"
    }
    test_analysis = {
        "edge": 0.15,
        "confidence": 95,
        "signal": "BUY"
    }

    success = await notifier.notify_opportunity_with_buttons(test_market, test_analysis)
    if success:
        print("✅ Test message sent! Please click a button in Telegram.")
        print("💡 Monitor API logs with: docker logs -f poly-autobet-api")
    else:
        print("❌ Failed to send test message.")

if __name__ == "__main__":
    asyncio.run(main())

import requests
import json

import os
from config.settings import settings

token = settings.telegram_bot_token
base_url = settings.telegram_webhook_base_url or "http://localhost:8601"
secret = settings.telegram_webhook_secret

# Ensure base_url ends correctly
base_url = base_url.rstrip("/")
url = f"{base_url}/webhook/telegram"

# 1. 註冊 Webhook
print(f"📡 正在嘗試註冊 Webhook 至: {url}")
try:
    set_url = f"https://api.telegram.org/bot{token}/setWebhook"
    payload = {
        "url": url,
        "secret_token": secret,
        "allowed_updates": ["callback_query", "message"]
    }
    r = requests.post(set_url, json=payload, timeout=30)
    print(f"✅ 註冊回應: {r.status_code}")
    print(json.dumps(r.json(), indent=2, ensure_ascii=False))
except Exception as e:
    print(f"❌ 註冊失敗: {e}")

# 2. 檢查 Webhook 狀態
print("\n🔍 檢查 Webhook 目前狀態...")
try:
    status_url = f"https://api.telegram.org/bot{token}/getWebhookInfo"
    r = requests.get(status_url, timeout=30)
    print(json.dumps(r.json(), indent=2, ensure_ascii=False))
except Exception as e:
    print(f"❌ 查詢失敗: {e}")

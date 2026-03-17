"""
Webhook Router — 供 FastAPI 掛載。
將此 router 加入你的主 FastAPI app。

使用方式：
    # 在你的 main.py 或 app.py
    from api.webhook_router import router as webhook_router
    app.include_router(webhook_router)
"""

from fastapi import APIRouter, Request, Response
from loguru import logger
from notifications.telegram_bot import notifier

router = APIRouter()


@router.get("/health")
async def health_check():
    """System health check endpoint."""
    return {"status": "ok", "service": "api"}


@router.post("/webhook/telegram")
async def telegram_webhook(request: Request):
    """
    Telegram 會把使用者的按鈕點擊、訊息等，
    以 POST 方式打到這個端點。

    流程：
      使用者點擊按鈕
        → Telegram 伺服器
        → POST https://poly.otter-labs.website/webhook/telegram
        → 這裡接收
        → 交給 notifier.process_webhook_update() 處理
        → 觸發 _handle_callback()
        → 發 Redis 信號 + 更新訊息 UI
    """
    body   = await request.body()
    secret = request.headers.get("X-Telegram-Bot-Api-Secret-Token", "")

    logger.debug(f"📥 Webhook 收到請求，body 長度：{len(body)}")

    ok = await notifier.process_webhook_update(body, secret)

    if not ok:
        # 就算處理失敗，也要回 200，否則 Telegram 會重試
        logger.warning("⚠️ Webhook 處理失敗，但回傳 200 避免 Telegram 重發")

    return Response(content='{"ok":true}', media_type="application/json")

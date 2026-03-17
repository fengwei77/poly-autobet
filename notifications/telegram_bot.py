"""
Notifications: Telegram Bot — Webhook 模式
改用 Webhook 取代 Polling，解決 Docker 內無法連出到 api.telegram.org 的問題。

架構說明：
  Polling 模式（舊）: Bot → 主動連到 api.telegram.org 拉資料 → 被防火牆擋
  Webhook 模式（新）: Telegram → 主動 POST 到你的 HTTPS 網址 → Bot 接收處理

Webhook 端點：
  POST https://poly.otter-labs.website/webhook/telegram

需要在 .env 新增：
  TELEGRAM_WEBHOOK_SECRET=任意隨機字串（防止偽造請求）
"""

from __future__ import annotations

import asyncio
import hmac
import hashlib
from typing import Optional
from loguru import logger
from config.settings import settings
from infra.redis_client import redis_client

try:
    from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup, Update
    from telegram.ext import Application, ApplicationBuilder, CallbackQueryHandler
    from telegram.request import HTTPXRequest
except ImportError:
    logger.warning("python-telegram-bot not installed.")
    Bot = None
    InlineKeyboardButton = None
    InlineKeyboardMarkup = None
    Update = None
    Application = None
    ApplicationBuilder = None
    CallbackQueryHandler = None
    HTTPXRequest = None


# ── Webhook 相關設定 ─────────────────────────────────────────────
# NOTE: WEBHOOK_BASE_URL should be configured in settings.telegram_webhook_base_url
# If not set, Webhook mode will be skipped
WEBHOOK_PATH     = "/webhook/telegram"

def get_webhook_url() -> str:
    """Get webhook URL from settings or return empty string."""
    from config.settings import settings
    base_url = settings.telegram_webhook_base_url
    if not base_url:
        return ""
    return f"{base_url}{WEBHOOK_PATH}"


class TelegramNotifier:
    """Telegram Bot：推送通知 + 接收按鈕指令（Webhook 模式）。"""

    def __init__(self):
        self._bot: Optional[Bot] = None
        self._app: Optional[Application] = None
        self._initialized = False

    # ════════════════════════════════════════════════════════════════
    # 初始化：建立 Bot + 向 Telegram 註冊 Webhook
    # ════════════════════════════════════════════════════════════════
    async def initialize(self):
        """啟動時呼叫一次。建立 Bot 實例並向 Telegram 設定 Webhook。"""
        if self._initialized:
            return
        self._initialized = True

        if not settings.telegram_bot_token or settings.telegram_bot_token == "your_telegram_token":
            logger.info("📱 Telegram Bot: 未設定 Token，略過初始化。")
            return

        asyncio.create_task(self._setup_async())

    async def _setup_async(self):
        """背景執行：建立 Application 並向 Telegram 註冊 Webhook 端點。"""
        if not Bot:
            logger.error("❌ python-telegram-bot 套件未安裝。")
            return

        try:
            logger.info("📱 Telegram Bot: 初始化 Webhook 模式...")

            # 建立自定義 HTTPXRequest，處理 SSL 問題
            request_config = HTTPXRequest(
                connect_timeout=60,
                read_timeout=60,
                write_timeout=60,
                pool_timeout=60,
            )

            # 建立 Application（不啟動 Polling）
            self._app = (
                ApplicationBuilder()
                .token(settings.telegram_bot_token)
                .request(request_config)
                .build()
            )

            # 註冊按鈕回呼處理器
            self._app.add_handler(CallbackQueryHandler(self._handle_callback))

            await self._app.initialize()
            # 注意：不呼叫 start_polling()，改用 Webhook
            await self._app.start()

            self._bot = self._app.bot

            # 向 Telegram 伺服器設定 Webhook
            webhook_url = get_webhook_url()
            if not webhook_url:
                logger.warning("⚠️ Telegram Webhook URL 未設定，跳過 Webhook 設定")
                return
            await self._register_webhook()

            logger.success(f"✅ Telegram Bot: Webhook 模式啟動，端點：{webhook_url}")

        except Exception as e:
            logger.error(f"❌ Telegram Bot 初始化失敗：{e}")

    async def _register_webhook(self, webhook_url: str = ""):
        """
        向 Telegram API 登記 Webhook URL。
        Telegram 收到使用者訊息後，會主動 POST 到這個 URL。
        """
        try:
            if not webhook_url:
                webhook_url = get_webhook_url()

            # 如果有設定 secret，加上防偽造驗證
            secret = getattr(settings, "telegram_webhook_secret", None)

            if secret:
                await self._bot.set_webhook(
                    url=webhook_url,
                    secret_token=secret,
                    allowed_updates=["callback_query", "message"],
                )
                logger.info(f"📌 Webhook 已設定（含 Secret）：{webhook_url}")
            else:
                await self._bot.set_webhook(
                    url=webhook_url,
                    allowed_updates=["callback_query", "message"],
                )
                logger.warning(f"📌 Webhook 已設定（無 Secret，建議設定 TELEGRAM_WEBHOOK_SECRET）：{webhook_url}")

        except Exception as e:
            logger.error(f"❌ Webhook 設定失敗：{e}")
            logger.error("請確認 Docker 容器能連到 api.telegram.org（只需要在啟動時呼叫一次）")

    # ════════════════════════════════════════════════════════════════
    # Webhook 接收端點（供 FastAPI/Flask Router 呼叫）
    # ════════════════════════════════════════════════════════════════
    async def process_webhook_update(self, body: bytes, secret_header: str = "") -> bool:
        """
        由 Web Framework 的路由呼叫，處理 Telegram 打進來的 Webhook 請求。

        使用方式（FastAPI 範例）：
            @app.post("/webhook/telegram")
            async def telegram_webhook(request: Request):
                body = await request.body()
                secret = request.headers.get("X-Telegram-Bot-Api-Secret-Token", "")
                await notifier.process_webhook_update(body, secret)
                return {"ok": True}

        Args:
            body:          HTTP 請求的原始 body（bytes）
            secret_header: Telegram 傳來的 X-Telegram-Bot-Api-Secret-Token header 值

        Returns:
            bool: True 表示處理成功
        """
        if not self._app:
            logger.error("❌ App 尚未初始化，無法處理 Webhook。")
            return False

        # 驗證 Secret（防止偽造請求打進來）
        secret = getattr(settings, "telegram_webhook_secret", None)
        if secret and secret_header != secret:
            logger.warning(f"⚠️ Webhook Secret 驗證失敗，拒絕請求。")
            return False

        try:
            import json
            logger.debug(f"📥 Received Webhook Body (first 100 bytes): {body[:100]!r}")
            logger.debug(f"🔐 Received Secret Header: {secret_header}")
            
            data = json.loads(body)
            update = Update.de_json(data, self._bot)
            if not update:
                logger.error("❌ Failed to parse Update from JSON")
                return False
                
            await self._app.process_update(update)
            logger.success("✅ Webhook update processed successfully")
            return True
        except Exception as e:
            logger.error(f"❌ Webhook 處理失敗：{e}")
            return False

    # ════════════════════════════════════════════════════════════════
    # 按鈕回呼處理（邏輯與原本完全相同）
    # ════════════════════════════════════════════════════════════════
    async def _handle_callback(self, update, context):
        """處理使用者點擊「批准 / 拒絕」按鈕。"""
        query = update.callback_query
        logger.info(f"🔘 Telegram Callback received: data={query.data}")

        try:
            await query.answer()
        except Exception as e:
            logger.warning(f"Failed to answer query: {e}")

        data = query.data  # 格式："approve|market_id"
        if "|" not in data:
            logger.error(f"Invalid callback data: {data}")
            return

        action, market_id = data.split("|", 1)
        logger.info(f"Processing action: {action} for market_id: {market_id}")

        if action == "approve":
            # 1. 先發 Redis 信號，確保交易不會因 UI 延遲而卡住
            await redis_client.publish(f"signal:manual_approve:{market_id}", "APPROVED")
            logger.info(f"🚀 Signal [APPROVED] released for market_id: {market_id}")

            # 2. 更新 Telegram 訊息 UI
            try:
                msg_text = query.message.text_html if query.message.text_html else query.message.text
                msg_text = msg_text.split("\n\n✅ <b>已核准下單</b>")[0].split("\n\n❌ <b>已忽略該機會</b>")[0]

                await context.bot.edit_message_text(
                    chat_id=query.message.chat_id,
                    message_id=query.message.message_id,
                    text=f"{msg_text}\n\n✅ <b>已核准下單</b>",
                    parse_mode="HTML",
                )
                logger.success(f"Market {market_id} UI updated: APPROVED")
            except Exception as e:
                logger.error(f"UI Update failed for approve: {e}")

        elif action == "reject":
            # 1. 先發 Redis 信號
            await redis_client.publish(f"signal:manual_approve:{market_id}", "REJECTED")
            logger.info(f"🚀 Signal [REJECTED] released for market_id: {market_id}")

            # 2. 更新 UI
            try:
                msg_text = query.message.text_html if query.message.text_html else query.message.text
                msg_text = msg_text.split("\n\n✅ <b>已核准下單</b>")[0].split("\n\n❌ <b>已忽略該機會</b>")[0]

                await context.bot.edit_message_text(
                    chat_id=query.message.chat_id,
                    message_id=query.message.message_id,
                    text=f"{msg_text}\n\n❌ <b>已忽略該機會</b>",
                    parse_mode="HTML",
                )
                logger.info(f"Market {market_id} UI updated: REJECTED")
            except Exception as e:
                logger.error(f"UI Update failed for reject: {e}")

    # ════════════════════════════════════════════════════════════════
    # 發送訊息（與原本邏輯相同，只保留 SDK 方式，移除 requests fallback）
    # ════════════════════════════════════════════════════════════════
    async def notify_opportunity_with_buttons(self, market: dict, analysis: dict) -> bool:
        """發送交易機會訊息，附帶「批准 / 拒絕」按鈕。"""
        max_retries = 10
        while not self._bot and max_retries > 0:
            logger.info("⏳ 等待 Telegram Bot 初始化...")
            await asyncio.sleep(1)
            max_retries -= 1

        if not self._bot or not settings.telegram_chat_id:
            logger.error("❌ Telegram Bot 未初始化或缺少 chat_id")
            return False

        market_id = market.get("condition_id", "unknown")
        question  = market.get("question", "")[:100]
        edge      = analysis.get("edge", 0)
        signal    = analysis.get("signal", "BUY")

        msg = (
            f"🎯 <b>發現在地策略機會</b>\n\n"
            f"標的: {question}\n"
            f"信號: <b>{signal}</b>\n"
            f"預期利潤 (Edge): {edge:.1%}\n"
            f"AI 信心度: {analysis.get('confidence')}\n\n"
            f"是否現在執行下單？"
        )

        keyboard = [[
            InlineKeyboardButton("✅ 執行下單", callback_data=f"approve|{market_id}"),
            InlineKeyboardButton("❌ 忽略",    callback_data=f"reject|{market_id}"),
        ]]

        try:
            await self._bot.send_message(
                chat_id=settings.telegram_chat_id,
                text=msg,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode="HTML",
            )
            logger.success(f"✅ 機會訊息已送出：{market_id}")
            return True
        except Exception as e:
            logger.error(f"❌ 發送失敗：{e}")
            return False

    async def send(self, message: str) -> bool:
        """發送純文字訊息。"""
        max_retries = 10
        while not self._bot and max_retries > 0:
            logger.info("⏳ 等待 Telegram Bot 初始化...")
            await asyncio.sleep(1)
            max_retries -= 1

        if not self._bot or not settings.telegram_chat_id:
            logger.error("❌ Telegram Bot 未初始化或缺少 chat_id")
            return False

        try:
            await self._bot.send_message(
                chat_id=settings.telegram_chat_id,
                text=message,
                parse_mode="HTML",
            )
            return True
        except Exception as e:
            logger.error(f"❌ 發送失敗：{e}")
            return False

    async def notify_trade(self, result: dict) -> None:
        side   = result.get("side", "?")
        amount = result.get("amount_usdc", 0)
        price  = result.get("price", 0)
        market = result.get("market", "")[:60]
        mode   = "📝" if result.get("is_paper") else "💰"
        await self.send(f"{mode} <b>{side}</b> ${amount:.2f} @ {price:.4f}\n{market}")

    async def notify_alert(self, alert_type: str, details: str) -> None:
        await self.send(f"⚠️ <b>{alert_type}</b>\n{details}")


notifier = TelegramNotifier()

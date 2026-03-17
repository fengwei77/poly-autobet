"""
FastAPI Server — Webhook 接收 + API 端點
"""

from fastapi import FastAPI
from loguru import logger
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from contextlib import asynccontextmanager
from api.webhook_router import router as webhook_router
from notifications.telegram_bot import notifier

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle manager for the FastAPI application."""
    logger.info("🚀 API Server Start: Initializing Telegram Notifier...")
    await notifier.initialize()
    yield
    logger.info("🛑 API Server Shutdown...")

app = FastAPI(title="Poly-AutoBet API", lifespan=lifespan)

# Include webhook router
app.include_router(webhook_router)

@app.get("/health")
async def health_check():
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8601)

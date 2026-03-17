"""
Poly-AutoBet: Global Configuration (Pydantic BaseSettings)
All settings are loaded from .env file or environment variables.
"""

from __future__ import annotations

import sys
from enum import Enum
from pathlib import Path
from typing import Optional

from loguru import logger
from pydantic import Field, field_validator, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class TradingMode(str, Enum):
    MONITOR = "monitor"
    PAPER = "paper"
    LIVE = "live"
    BACKTEST = "backtest"


class NodeRole(str, Enum):
    BRAIN = "brain"       # Full analysis + execution
    EXECUTOR = "executor"  # Signal receiver + order execution only


class Settings(BaseSettings):
    """Central configuration loaded from .env"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # === Polymarket ===
    polymarket_private_key: str = ""
    polymarket_api_key: str = ""
    polymarket_api_secret: str = ""
    polymarket_passphrase: str = ""
    polymarket_host: str = "https://clob.polymarket.com"
    polymarket_chain_id: int = 137  # Polygon mainnet

    # === Weather APIs ===
    openweathermap_api_key: str = ""
    noaa_user_agent: str = "poly-autobet/1.0"

    # === AI Multi-Provider (全部 OpenAI-compatible) ===
    ai_provider: str = "minimax"  # gpt | deepseek | minimax | kimi | qwen | glm | gemini
    ai_model: str = ""  # 留空 = 自動使用 provider 預設模型

    # 各 Provider API Keys（只需填入你有的）
    openai_api_key: str = ""       # GPT-4o
    deepseek_api_key: str = ""     # DeepSeek-V3
    minimax_api_key: str = ""      # MiniMax-M2.5
    kimi_api_key: str = ""         # Kimi / Moonshot
    qwen_api_key: str = ""         # Qwen 3.5 (阿里通義)
    glm_api_key: str = ""          # GLM-4 (智譜)
    gemini_api_key: str = ""       # Gemini 2.5 Flash

    # === Redis & DB ===
    redis_url: str = "redis://localhost:6379"
    database_url: str = "sqlite+aiosqlite:///./db/polybet.db"

    # === Notifications ===
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""
    telegram_webhook_secret: str = ""

    # === Trading Settings ===
    trading_mode: TradingMode = TradingMode.PAPER
    node_role: NodeRole = NodeRole.BRAIN
    delegate_execution: bool = False  # If True, Brain node publishes to Redis instead of executing locally
    max_daily_exposure: float = 500.0
    max_single_bet: float = 50.0
    min_single_bet: float = 2.0
    min_edge: float = 0.05            # 5% minimum edge
    confidence_threshold: int = 70     # 0-100
    kelly_fraction: float = 0.25       # Conservative Kelly
    max_positions: int = 20
    max_per_city: int = 3
    
    # === Safety & Strategy ===
    trading_strategy: str = "auto"     # auto | semi-auto
    max_consecutive_loss_limit: int = 10
    max_capital_utilization: float = 0.8

    # === Scanning ===
    scan_interval_minutes: int = 15
    deep_analysis_interval_minutes: int = 60
    auto_exit_hours_before_resolution: int = 1

    # === Risk Control ===
    stop_loss_pct: float = 0.20
    daily_stop_loss: float = 100.0
    weekly_stop_loss: float = 300.0
    consecutive_loss_pause: int = 5
    pause_duration_hours: int = 6

    # === Scalping Strategy ===
    scalping_take_profit_pct: float = 0.15  # 15% 停利
    scalping_stop_loss_pct: float = 0.10   # 10% 停損

    @property
    def is_brain(self) -> bool:
        return self.node_role == NodeRole.BRAIN

    @property
    def is_live(self) -> bool:
        return self.trading_mode == TradingMode.LIVE

    @computed_field
    @property
    def db_dir(self) -> Path:
        p = Path("./db")
        p.mkdir(exist_ok=True)
        return p

    def validate(self) -> list[str]:
        """Validate critical settings on startup."""
        errors = []
        if self.is_live:
            if not self.polymarket_private_key: errors.append("polymarket_private_key")
            if not self.polymarket_api_key: errors.append("polymarket_api_key")
            
        if self.ai_provider == "minimax" and not self.minimax_api_key:
            errors.append("minimax_api_key")
        elif self.ai_provider == "openai" and not self.openai_api_key:
            errors.append("openai_api_key")
            
        if not self.telegram_bot_token: errors.append("telegram_bot_token")
        
        return errors


# Singleton
settings = Settings()

def reload_settings():
    """Manually reload settings from .env"""
    global settings
    settings = Settings()
    logger.info("♻️ Settings reloaded from .env")

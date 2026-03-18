"""
Core: AI Analyzer — Multi-provider AI analysis with instructor structured output.
Supports 7 OpenAI-compatible providers: GPT, DeepSeek, MiniMax, Kimi, Qwen, GLM, Gemini.
All providers share the same OpenAI chat.completions API format.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import re
import json
import asyncio
from typing import Optional
from loguru import logger
from pydantic import BaseModel, Field

from config.settings import settings
from data.models import AnalysisResult
from data.database import async_session


# === Provider Registry ===

@dataclass(frozen=True)
class AIProvider:
    """Definition of an OpenAI-compatible AI provider."""
    name: str
    base_url: str
    default_model: str
    api_key_field: str  # settings attribute name


# All 7 supported providers — all OpenAI-compatible
PROVIDERS: dict[str, AIProvider] = {
    "gpt": AIProvider(
        name="OpenAI GPT",
        base_url="https://api.openai.com/v1",
        default_model="gpt-4o",
        api_key_field="openai_api_key",
    ),
    "deepseek": AIProvider(
        name="DeepSeek",
        base_url="https://api.deepseek.com/v1",
        default_model="deepseek-chat",
        api_key_field="deepseek_api_key",
    ),
    "minimax": AIProvider(
        name="MiniMax",
        base_url="https://api.minimax.chat/v1",
        default_model="MiniMax-M2.5",
        api_key_field="minimax_api_key",
    ),
    "kimi": AIProvider(
        name="Kimi (Moonshot)",
        base_url="https://api.moonshot.ai/v1",
        default_model="moonshot-v1-8k",
        api_key_field="kimi_api_key",
    ),
    "qwen": AIProvider(
        name="Qwen (通義千問)",
        base_url="https://dashscope-intl.aliyuncs.com/compatible-mode/v1",
        default_model="qwen-plus",
        api_key_field="qwen_api_key",
    ),
    "glm": AIProvider(
        name="GLM (智譜)",
        base_url="https://open.bigmodel.cn/api/paas/v4",
        default_model="glm-4-flash",
        api_key_field="glm_api_key",
    ),
    "gemini": AIProvider(
        name="Gemini",
        base_url="https://generativelanguage.googleapis.com/v1beta/openai",
        default_model="gemini-1.5-flash",
        api_key_field="gemini_api_key",
    ),
    "cli": AIProvider(
        name="CLI Simulation",
        base_url="local://cli",
        default_model="manual-eval",
        api_key_field="openai_api_key", # Dummy field
    ),
}


# === Pydantic Schema for structured AI output ===

class TradeDecision(BaseModel):
    """Structured output schema enforced by instructor."""
    real_probability: float = Field(ge=0.0, le=1.0, description="Estimated true probability (0-1)")
    confidence: int = Field(ge=0, le=100, description="Confidence score 0-100")
    signal: str = Field(description="BUY, SELL, or HOLD")
    reasoning: str = Field(description="Analysis reasoning in 1-2 sentences")
    risk_factors: list[str] = Field(default_factory=list, description="Key risk factors")


class CityExtraction(BaseModel):
    """Structured city name extraction."""
    city_name: str = Field(description="The primary name of the city identified in the text (e.g., 'New York')")
    is_weather_market: bool = Field(description="Whether this text actually refers to a weather market")


class AIAnalyzer:
    """
    Multi-provider AI market analysis with instructor structured output.
    All 7 providers use the same OpenAI-compatible API, making them hot-swappable.
    Configure via AI_PROVIDER env var or settings.ai_provider.
    """

    def __init__(self):
        self._client = None
        self._provider: Optional[AIProvider] = None
        self._model: str = ""
        self._initialized = False

    async def _ensure_client(self):
        if self._initialized:
            return

        provider_key = settings.ai_provider.lower()
        import os
        env_provider = os.environ.get("AI_PROVIDER", "").lower()
        if env_provider == "cli":
            provider_key = env_provider
            
        logger.info(f"🔄 AI Analyzer: Initializing with provider='{provider_key}'")

        provider = PROVIDERS.get(provider_key)
        if not provider:
            available = ", ".join(PROVIDERS.keys())
            logger.error(f"❌ Unknown AI provider: '{provider_key}'. Available: {available}")
            return

        # Handle CLI
        if provider_key == "cli":
            self._provider = provider
            self._model = provider.default_model
            self._initialized = True
            logger.success(f"📟 AI Analyzer: {provider.name} Mode Active (Initialized)")
            return

        # Standard OpenAI-compatible initialization
        api_key = getattr(settings, provider.api_key_field, "")
        base_url = settings.ai_base_url if settings.ai_base_url else provider.base_url

        if not api_key and provider_key != "cli":
            logger.warning(f"⚠️ No API key for {provider.name} — seeking fallback...")
            api_key, provider = self._find_fallback_provider()
            if not api_key:
                logger.error("❌ No configured AI providers found.")
                return
            base_url = settings.ai_base_url if settings.ai_base_url else provider.base_url

        # Model: user override or provider default
        model = settings.ai_model if settings.ai_model else provider.default_model

        try:
            import instructor
            from openai import AsyncOpenAI

            openai_client = AsyncOpenAI(
                api_key=api_key or "sk-proxy", # Dummy if using proxy
                base_url=base_url,
            )
            self._client = instructor.from_openai(openai_client)
            self._provider = provider
            self._model = model
            self._initialized = True
            logger.info(f"🤖 AI Analyzer: {provider.name} | model={model} | base_url={base_url}")
        except Exception as e:
            logger.warning(f"⚠️ AI Initialization failed: {e}")

    def _find_fallback_provider(self) -> tuple[str, Optional[AIProvider]]:
        """Try to find any provider that has a configured API key."""
        for key, provider in PROVIDERS.items():
            if key in ["cli"]: continue
            api_key = getattr(settings, provider.api_key_field, "")
            if api_key:
                logger.info(f"🔄 Fallback to {provider.name} (has API key)")
                return api_key, provider
        return "", None

    def get_available_providers(self) -> list[dict]:
        """List all providers and whether they have API keys configured."""
        result = []
        for key, provider in PROVIDERS.items():
            api_key = getattr(settings, provider.api_key_field, "")
            result.append({
                "id": key,
                "name": provider.name,
                "model": provider.default_model,
                "configured": bool(api_key),
                "active": key == settings.ai_provider.lower(),
            })
        return result

    # === Main Entry ===

    async def analyze_opportunity(
        self,
        market: dict,
        weather: dict,
    ) -> Optional[dict]:
        """
        Analyze a market opportunity using AI + statistical model.
        Returns analysis result with signal, edge, confidence.
        """
        await self._ensure_client()

        market_price = market.get("yes_price", 0.5)

        # Step 1: Statistical analysis (always runs, no API cost)
        stat_result = self._statistical_analysis(market, weather)

        # Step 2: AI deep analysis (if provider available)
        ai_result = None
        trigger_threshold = (
            settings.ai_trigger_threshold_paper
            if settings.trading_mode.value == "paper"
            else settings.ai_trigger_threshold_live
        )
        
        can_use_ai = bool(self._client) or (self._provider and self._provider.name == "CLI Simulation")
        edge = stat_result.get("edge", 0)
        
        if can_use_ai and edge > trigger_threshold:
            logger.info(f"🤖 AI Analyzer: Triggering Deep Analysis ({self._provider.name if self._provider else 'unknown'})")
            ai_result = await self._ai_analysis(market, weather, stat_result)
        else:
            if not can_use_ai:
                logger.info("⏭️ AI Analyzer: Skipping (No client initialized)")
            else:
                logger.info(f"⏭️ AI Analyzer: Skipping (Edge {edge:.1%} <= Threshold {trigger_threshold:.1%})")

        # Step 3: Merge results
        final = self._merge_analysis(stat_result, ai_result)

        # Step 4: Calculate Kelly sizing
        final["kelly_fraction"] = self._kelly_criterion(
            final["forecast_probability"],
            market_price,
        )
        final["suggested_size_usdc"] = min(
            settings.max_single_bet,
            max(settings.min_single_bet, settings.max_daily_exposure * final.get("kelly_fraction", 0) * settings.kelly_fraction),
        )

        # Save to DB
        await self._save_result(market, final)

        return final

    async def extract_city(self, text: str) -> Optional[str]:
        """Use AI to extract city name from text. Supports automatic failover."""
        await self._ensure_client()
        if not self._client and self._provider.name != "CLI Simulation":
            return None

        prompt = f"Extract the city name from this Polymarket market question: '{text}'. Return only the standardized city name in English (e.g., 'New York')."

        try:
            if self._provider and self._provider.name == "CLI Simulation":
                city_match = re.search(r"['\"]?([^'\"\n,]+)['\"]?", text)
                return city_match.group(1).strip() if city_match else "unknown"

            extraction = await self._client.chat.completions.create(
                model=self._model,
                max_tokens=64,
                response_model=CityExtraction,
                messages=[{"role": "user", "content": prompt}],
            )
            if extraction.city_name.lower() != "unknown":
                return extraction.city_name
        except Exception as e:
            logger.warning(f"⚠️ City extraction failed: {e}")
        return None

    # === Statistical Analysis ===

    def _statistical_analysis(self, market: dict, weather: dict) -> dict:
        """Pure statistical comparison of weather forecast vs market price."""
        market_price = market.get("yes_price", 0.5)
        forecast_prob = self._estimate_probability(market, weather)
        edge = forecast_prob - market_price

        agreement = weather.get("agreement", "single_source")
        base_confidence = {"high": 85, "medium": 65, "low": 40, "single_source": 50}.get(agreement, 50)

        volume = market.get("volume", 0)
        if volume > 10000:
            base_confidence = min(95, base_confidence + 10)
        elif volume < 1000:
            base_confidence = max(20, base_confidence - 15)

        signal = "HOLD"
        if edge > settings.min_edge and base_confidence >= settings.confidence_threshold:
            signal = "BUY"
        elif edge < -settings.min_edge and base_confidence >= settings.confidence_threshold:
            signal = "SELL"

        return {
            "forecast_probability": round(forecast_prob, 4),
            "market_price": round(market_price, 4),
            "edge": round(edge, 4),
            "confidence": base_confidence,
            "signal": signal,
            "reasoning": f"Statistical: edge={edge:.1%}, agreement={agreement}, volume=${volume:,.0f}",
            "risk_factors": [],
            "source": "statistical",
        }

    def _estimate_probability(self, market: dict, weather: dict) -> float:
        from core.strategy_engine import strategy_engine
        return strategy_engine.estimate_probability(market, weather)

    # === AI Analysis ===

    async def _ai_analysis(self, market: dict, weather: dict, stat: dict) -> Optional[dict]:
        """Use AI for deep analysis with failover."""
        await self._ensure_client()
        if not self._client and self._provider.name != "CLI Simulation":
            return None

        prompt = f"""You are a weather prediction market analyst.
Market: {market.get('question', 'N/A')}
Price: {market.get('yes_price', 0.5):.4f}
Forecast: High {weather.get('temp_high_c')}C, Low {weather.get('temp_low_c')}C, Precip {weather.get('precipitation_mm')}mm
Stat Edge: {stat.get('edge', 0):.1%}

Provide TradeDecision in Traditional Chinese. 白話、親切、直白。
"""

        tried_providers = {self._provider.name if self._provider else "default"}

        for attempt in range(3):
            try:
                if self._provider.name == "CLI Simulation":
                    return {
                        "forecast_probability": stat.get("forecast_probability", 0.5),
                        "confidence": 70,
                        "signal": "HOLD",
                        "reasoning": "CLI Simulation Active.",
                        "source": "cli_simulation",
                    }

                decision = await self._client.chat.completions.create(
                    model=self._model,
                    max_tokens=512,
                    response_model=TradeDecision,
                    messages=[{"role": "user", "content": prompt}],
                )
                return {
                    "forecast_probability": decision.real_probability,
                    "confidence": decision.confidence,
                    "signal": decision.signal,
                    "reasoning": decision.reasoning,
                    "risk_factors": decision.risk_factors,
                    "source": self._provider.name,
                }
            except Exception as e:
                logger.warning(f"⚠️ AI analysis failed on {self._provider.name}: {e}")
                next_key, next_prov = self._find_next_available_provider(tried_providers)
                if next_prov:
                    logger.info(f"🔄 Failover: Switching to {next_prov.name}")
                    tried_providers.add(next_prov.name)
                    import instructor
                    from openai import AsyncOpenAI
                    api_key = getattr(settings, next_prov.api_key_field)
                    openai_client = AsyncOpenAI(api_key=api_key, base_url=next_prov.base_url)
                    self._client = instructor.from_openai(openai_client)
                    self._provider = next_prov
                    self._model = next_prov.default_model
                    continue
                break
        return None

    def _find_next_available_provider(self, tried_names: set[str]) -> tuple[str, Optional[AIProvider]]:
        for key, provider in PROVIDERS.items():
            if provider.name in tried_names or key == "cli":
                continue
            api_key = getattr(settings, provider.api_key_field, "")
            if api_key:
                return key, provider
        return "", None

    def _merge_analysis(self, stat: dict, ai: Optional[dict]) -> dict:
        if not ai:
            return stat

        ai_weight = ai.get("confidence", 50) / 100
        stat_weight = 1 - ai_weight

        merged_prob = stat["forecast_probability"] * stat_weight + ai["forecast_probability"] * ai_weight
        merged_confidence = int(stat["confidence"] * 0.4 + ai["confidence"] * 0.6)
        merged_edge = merged_prob - stat["market_price"]
        
        signal = "HOLD"
        if merged_edge > settings.min_edge and merged_confidence >= settings.confidence_threshold:
            signal = "BUY"
        elif merged_edge < -settings.min_edge and merged_confidence >= settings.confidence_threshold:
            signal = "SELL"

        return {
            "forecast_probability": round(merged_prob, 4),
            "market_price": stat["market_price"],
            "edge": round(merged_edge, 4),
            "confidence": merged_confidence,
            "signal": signal,
            "reasoning": f"AI: {ai.get('reasoning', '')} | Stat: {stat.get('reasoning', '')}",
            "risk_factors": ai.get("risk_factors", []) + stat.get("risk_factors", []),
            "source": "merged",
        }

    def _kelly_criterion(self, prob: float, price: float) -> float:
        if price <= 0 or price >= 1 or prob <= 0 or prob >= 1:
            return 0.0
        b = (1 / price) - 1
        kelly = (b * prob - (1 - prob)) / b
        return max(0.0, min(1.0, kelly))

    async def _log_cli_prompt(self, type: str, data: dict) -> None:
        import os
        log_file = "/app/logs/ai_prompts.jsonl"
        os.makedirs("/app/logs", exist_ok=True)
        logger.debug(f"📝 CLI AI: Logging prompt of type '{type}' to {log_file}")
        entry = {"timestamp": datetime.now(timezone.utc).isoformat(), "type": type, "data": data}
        try:
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except Exception as e:
            logger.error(f"❌ Failed to log CLI prompt: {e}")

    async def ask_ai(self, question: str, context: dict) -> str:
        await self._ensure_client()
        context_str = f"模式: {context.get('mode')}\n餘額: {context.get('current_balance', 0):.2f} USDC"
        full_prompt = f"你是 POLY DREAM 助手。背景:\n{context_str}\n\n問題: {question}"

        if not self._client:
            return "❌ AI 未初始化。請檢查 .env 設定。"

        try:
            raw_client = self._client.client if hasattr(self._client, "client") else self._client
            response = await raw_client.chat.completions.create(
                model=self._model,
                messages=[{"role": "user", "content": full_prompt}],
                temperature=0.7,
                max_tokens=500
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"❌ AI Q&A failed: {e}")
            return f"❌ 抱歉，AI 暫時無法回覆 ({e})"

    async def _save_result(self, market: dict, result: dict) -> None:
        async with async_session() as session:
            record = AnalysisResult(
                market_condition_id=market.get("condition_id", ""),
                city=market.get("city", "unknown"),
                forecast_probability=result.get("forecast_probability", 0.5),
                market_price=result.get("market_price", 0.5),
                edge=result.get("edge", 0),
                confidence=result.get("confidence", 0),
                signal=result.get("signal", "HOLD"),
                reasoning=result.get("reasoning", ""),
                risk_factors=result.get("risk_factors", []),
                kelly_fraction=result.get("kelly_fraction"),
                suggested_size_usdc=result.get("suggested_size_usdc"),
            )
            session.add(record)
            await session.commit()


# Module singleton
ai_analyzer = AIAnalyzer()

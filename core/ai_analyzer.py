"""
Core: AI Analyzer — Multi-provider AI analysis with instructor structured output.
Supports 7 OpenAI-compatible providers: GPT, DeepSeek, MiniMax, Kimi, Qwen, GLM, Gemini.
All providers share the same OpenAI chat.completions API format.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
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
        base_url="https://api.minimax.io/v1",
        default_model="MiniMax-M2.5",
        api_key_field="minimax_api_key",
    ),
    "kimi": AIProvider(
        name="Kimi (Moonshot)",
        base_url="https://api.moonshot.ai/v1",
        default_model="kimi-k2",
        api_key_field="kimi_api_key",
    ),
    "qwen": AIProvider(
        name="Qwen (通義千問)",
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
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
        default_model="gemini-2.5-flash",
        api_key_field="gemini_api_key",
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
        self._initialized = True

        provider_key = settings.ai_provider.lower()
        provider = PROVIDERS.get(provider_key)

        if not provider:
            available = ", ".join(PROVIDERS.keys())
            logger.error(f"❌ Unknown AI provider: '{provider_key}'. Available: {available}")
            return

        # Get API key from settings
        api_key = getattr(settings, provider.api_key_field, "")
        if not api_key:
            logger.warning(f"⚠️ No API key for {provider.name} ({provider.api_key_field}) — using statistical analysis only")
            # Try fallback: find any configured provider
            api_key, provider = self._find_fallback_provider()
            if not api_key:
                return

        # Model: user override or provider default
        model = settings.ai_model if settings.ai_model else provider.default_model

        try:
            import instructor
            from openai import AsyncOpenAI

            openai_client = AsyncOpenAI(
                api_key=api_key,
                base_url=provider.base_url,
            )
            self._client = instructor.from_openai(openai_client)
            self._provider = provider
            self._model = model
            logger.info(f"🤖 AI Analyzer: {provider.name} | model={model} | endpoint={provider.base_url}")
        except ImportError as e:
            logger.warning(f"⚠️ openai/instructor not installed: {e}")

    def _find_fallback_provider(self) -> tuple[str, Optional[AIProvider]]:
        """Try to find any provider that has a configured API key."""
        for key, provider in PROVIDERS.items():
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
        # Get trigger threshold from settings based on trading mode
        trigger_threshold = (
            settings.ai_trigger_threshold_paper
            if settings.trading_mode.value == "paper"
            else settings.ai_trigger_threshold_live
        )
        if self._client and stat_result.get("edge", 0) > trigger_threshold:
            ai_result = await self._ai_analysis(market, weather, stat_result)

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
        """Use AI to extract city name from text."""
        await self._ensure_client()
        if not self._client:
            return None

        prompt = f"Extract the city name from this Polymarket weather market question: '{text}'. Return only the standardized city name (e.g., 'New York'). If no city is found, return 'unknown'."

        try:
            extraction = await self._client.chat.completions.create(
                model=self._model,
                max_tokens=64,
                response_model=CityExtraction,
                messages=[{"role": "user", "content": prompt}],
            )
            if extraction.is_weather_market and extraction.city_name.lower() != "unknown":
                return extraction.city_name
        except Exception as e:
            logger.debug(f"AI city extraction failed: {e}")
        return None

    # === Statistical Analysis (local, no API call) ===

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
        """Estimate true probability based on weather forecast data."""
        from core.strategy_engine import strategy_engine
        return strategy_engine.estimate_probability(market, weather)

    # === AI Analysis (any provider) ===

    async def _ai_analysis(self, market: dict, weather: dict, stat: dict) -> Optional[dict]:
        """Use any configured AI provider + instructor for deep analysis."""
        if not self._client:
            return None

        provider_name = self._provider.name if self._provider else "unknown"

        prompt = f"""You are a weather prediction market analyst. Analyze this opportunity:

## Market
- Question: {market.get('question', 'N/A')}
- Current Price: {market.get('yes_price', 0.5):.4f} ({market.get('yes_price', 0.5) * 100:.1f}% implied probability)
- Volume: ${market.get('volume', 0):,.0f}
- City: {market.get('city', 'unknown')}

## Weather Forecast (averaged from {weather.get('source_count', 1)} sources)
- High: {weather.get('temp_high_c', 'N/A')}°C
- Low: {weather.get('temp_low_c', 'N/A')}°C
- Precipitation: {weather.get('precipitation_mm', 'N/A')}mm
- Source Agreement: {weather.get('agreement', 'unknown')}

## Statistical Pre-Analysis
- Estimated Real Probability: {stat.get('forecast_probability', 0.5):.1%}
- Edge: {stat.get('edge', 0):.1%}

Provide your analysis as a TradeDecision with real_probability, confidence, signal (BUY/SELL/HOLD), reasoning, and risk_factors."""

        try:
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
                "source": provider_name,
            }
        except Exception as e:
            logger.error(f"AI analysis failed ({provider_name}): {e}")
            return None

    # === Merge ===

    def _merge_analysis(self, stat: dict, ai: Optional[dict]) -> dict:
        """Merge statistical and AI analysis results."""
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
            "reasoning": f"AI ({ai.get('source', '?')}): {ai.get('reasoning', '')} | Stat: {stat.get('reasoning', '')}",
            "risk_factors": ai.get("risk_factors", []) + stat.get("risk_factors", []),
            "source": "merged",
        }

    # === Kelly Criterion ===

    def _kelly_criterion(self, prob: float, price: float) -> float:
        """Calculate Kelly fraction for optimal bet sizing."""
        if price <= 0 or price >= 1 or prob <= 0 or prob >= 1:
            return 0.0
        b = (1 / price) - 1
        kelly = (b * prob - (1 - prob)) / b
        return max(0.0, min(1.0, kelly))

    # === DB ===

    async def _save_result(self, market: dict, result: dict) -> None:
        """Persist analysis result to database."""
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

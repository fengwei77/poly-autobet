"""
Core: AI Analyzer — Multi-provider AI analysis with instructor structured output.
Supports 7 OpenAI-compatible providers: GPT, DeepSeek, MiniMax, Kimi, Qwen, GLM, Gemini.
All providers share the same OpenAI chat.completions API format.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import re
import httpx
import asyncio
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
        default_model="kimi-k2-turbo-preview",
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
        default_model="gemini-2.5-flash",
        api_key_field="gemini_api_key",
    ),
    "cli": AIProvider(
        name="CLI Simulation",
        base_url="local://cli",
        default_model="manual-eval",
        api_key_field="openai_api_key", # Dummy field
    ),
    "opencode": AIProvider(
        name="OpenCode CLI",
        base_url="local://opencode",
        default_model="opencode-go/kimi-k2.5",
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
        if env_provider in ["cli", "opencode"]:
            provider_key = env_provider
            
        logger.info(f"🔄 AI Analyzer: Initializing with provider='{provider_key}'")

        provider = PROVIDERS.get(provider_key)
        if not provider:
            available = ", ".join(PROVIDERS.keys())
            logger.error(f"❌ Unknown AI provider: '{provider_key}'. Available: {available}")
            return

        # Handle CLI/OpenCode (No API key needed)
        if provider_key in ["cli", "opencode"]:
            self._provider = provider
            self._model = provider.default_model
            self._initialized = True
            logger.success(f"📟 AI Analyzer: {provider.name} Mode Active (Initialized)")
            return

        # Standard OpenAI-compatible initialization
        api_key = getattr(settings, provider.api_key_field, "")
        if not api_key:
            logger.warning(f"⚠️ No API key for {provider.name} ({provider.api_key_field}) — seeking fallback...")
            api_key, provider = self._find_fallback_provider()
            if not api_key:
                logger.error("❌ No configured AI providers found. Falling back to statistical mode.")
                return

        # Model: user override or provider default
        model = settings.ai_model if settings.ai_model else provider.default_model

        if provider_key in ["cli", "opencode"]:
            self._provider = provider
            self._model = provider.default_model
            self._initialized = True
            logger.success(f"📟 AI Analyzer: {provider.name} Mode Active (Initialized)")
            return

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
        # AI Deep Analysis Trigger
        # If provider is CLI or OpenCode, we don't need self._client (instructor)
        is_manual = self._provider and self._provider.name in ["CLI Simulation", "OpenCode CLI"]
        can_use_ai = bool(self._client) or is_manual
        
        edge = stat_result.get("edge", 0)
        logger.info(f"🔍 AI Trigger Check: can_use_ai={can_use_ai}, is_manual={is_manual}, edge={edge:.1%}, threshold={trigger_threshold:.1%}, provider={self._provider.name if self._provider else 'None'}")
        
        if can_use_ai and edge > trigger_threshold:
            logger.info(f"🤖 AI Analyzer: Triggering Deep Analysis ({self._provider.name if self._provider else 'unknown'})")
            ai_result = await self._ai_analysis(market, weather, stat_result)
        else:
            if not can_use_ai:
                logger.info("⏭️ AI Analyzer: Skipping (No client or provider active)")
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
        if not self._client:
            return None

        prompt = f"Extract the city name from this Polymarket market question: '{text}'. Return only the standardized city name in English (e.g., 'New York'). If the question refers to a specific location or city, extract it even if it's not a weather market. If no city/location is found, return 'unknown'."

        # Try automatic failover
        tried_providers = {self._provider.name if self._provider else "default"}

        for attempt in range(3):
            try:
                # CLI Mode Interception
                if self._provider and self._provider.name == "CLI Simulation":
                    await self._log_cli_prompt("city_extraction", {"text": text, "prompt": prompt})
                    # For city extraction in CLI, we usually want immediate results. 
                    # If we can't get one, fallback to simple parsing.
                    city_match = re.search(r"['\"]?([^'\"\n,]+)['\"]?", text)
                    return city_match.group(1).strip() if city_match else "unknown"

                # Use instructor for structured output (OpenAI SDK compatible)

                extraction = await self._client.chat.completions.create(
                    model=self._model,
                    max_tokens=64,
                    response_model=CityExtraction,
                    messages=[{"role": "user", "content": prompt}],
                )
                if extraction.is_weather_market and extraction.city_name.lower() != "unknown":
                    return extraction.city_name
                break # Success
            except Exception as e:
                logger.warning(f"⚠️ AI extraction failed on {self._provider.name if self._provider else 'default'}: {e}")
                
                next_key, next_prov = self._find_next_available_provider(tried_providers)
                if next_prov:
                    logger.info(f"🔄 Failover (Extraction): Switching to {next_prov.name}")
                    tried_providers.add(next_prov.name)
                    # Temporary override
                    from openai import AsyncOpenAI
                    import instructor
                    api_key = getattr(settings, next_prov.api_key_field)
                    openai_client = AsyncOpenAI(api_key=api_key, base_url=next_prov.base_url)
                    self._client = instructor.from_openai(openai_client)
                    self._provider = next_prov
                    self._model = next_prov.default_model
                    continue
                break
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
        """Use any configured AI provider + instructor for deep analysis. Supports automatic failover."""
        await self._ensure_client()
        if not self._client:
            return None

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

Provide your analysis as a TradeDecision with real_probability, confidence, signal (BUY/SELL/HOLD), reasoning, and risk_factors.
**IMPORTANT**: All text output (reasoning, risk_factors) MUST be in **Traditional Chinese (繁體中文)**.
分析理由 (reasoning) 必須使用極其通俗易懂的「白話文」(layperson-friendly)，像是在跟朋友聊天一樣自然。
避免使用過於專業的術語或僵硬的 AI 腔調，要用一般人一看就懂、有溫度且直白的語言來解釋盤口與天氣的關係。
例如：不要說「降水概率偏差導致期望值正向」，而要說「我看這地方降雨機率比開出的盤口低很多，現在進場買 Yes 很有勝算」。
"""

        # Try automatic failover for quota/error issues
        active_provider = self._provider
        tried_providers = {self._provider.name if self._provider else "default"}

        for attempt in range(3): # Try up to 3 different providers
            try:
                # OpenCode CLI Mode
                if active_provider and active_provider.name == "OpenCode CLI":
                    return await self._opencode_cli_analysis(prompt, stat)

                # CLI Mode Interception (Interacting with Assistant)
                if active_provider and active_provider.name == "CLI Simulation":
                    logger.info("📡 CLI AI: Logging market prompt for manual evaluation...")
                    await self._log_cli_prompt("trade_decision", {
                        "market_question": market.get("question"),
                        "city": market.get("city"),
                        "stat_edge": stat.get("edge"),
                        "prompt": prompt
                    })
                    
                    # Return a signal that indicates waiting for manual/assistant feedback
                    return {
                        "forecast_probability": stat.get("forecast_probability", 0.5),
                        "confidence": 70, # High enough to be noticed but signal is HOLD
                        "signal": "HOLD",
                        "reasoning": "CLI 模式已啟用。請在日誌中查看分析需求，或由助手 (Assistant) 提供模擬回饋。",
                        "source": "cli_simulation",
                    }

                # Use instructor for structured output (OpenAI SDK compatible)

                # Use instructor for structured output
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
                    "source": active_provider.name if active_provider else "unknown",
                }
            except Exception as e:
                logger.warning(f"⚠️ AI analysis failed on {self._provider.name if self._provider else 'default'}: {e}")
                
                # [Failover] Try next provider
                self._initialized = False # Force re-init
                next_key, next_prov = self._find_next_available_provider(tried_providers)
                if next_prov:
                    logger.info(f"🔄 Failover: Switching from {self._provider.name} to {next_prov.name}")
                    tried_providers.add(next_prov.name)
                    # Temporary override
                    from openai import AsyncOpenAI
                    import instructor
                    api_key = getattr(settings, next_prov.api_key_field)
                    openai_client = AsyncOpenAI(api_key=api_key, base_url=next_prov.base_url)
                    self._client = instructor.from_openai(openai_client)
                    self._provider = next_prov
                    self._model = next_prov.default_model
                    continue
                break
        return None

    def _find_next_available_provider(self, tried_names: set[str]) -> tuple[str, Optional[AIProvider]]:
        """Find the next configured provider that hasn't been tried yet."""
        for key, provider in PROVIDERS.items():
            if provider.name in tried_names:
                continue
            api_key = getattr(settings, provider.api_key_field, "")
            if api_key:
                return key, provider
        return "", None

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

    async def _opencode_cli_analysis(self, prompt: str, stat: dict) -> Optional[dict]:
        """Execute OpenCode CLI to get AI analysis."""
        import subprocess
        import json
        import shlex

        try:
            # We use 'opencode run' with the prompt. 
            # We ask for JSON format to parse it easily.
            # Note: We escaped the prompt for shell safety.
            cmd = f"opencode run {shlex.quote(prompt)} --format json"
            logger.info(f"🚀 Executing OpenCode CLI: {cmd[:100]}...")
            
            # Using asyncio subprocess for non-blocking execution
            proc = await asyncio.create_subprocess_shell(
                cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await proc.communicate()
            
            if proc.returncode != 0:
                logger.error(f"❌ OpenCode CLI failed ({proc.returncode}): {stderr.decode()}")
                return None
                
            output = stdout.decode().strip()
            # Try to find JSON in the output
            json_match = re.search(r"\{.*\}", output, re.DOTALL)
            if json_match:
                decision = json.loads(json_match.group(0))
                # Ensure it matches TradeDecision schema
                return {
                    "forecast_probability": decision.get("real_probability", stat.get("forecast_probability", 0.5)),
                    "confidence": decision.get("confidence", 50),
                    "signal": decision.get("signal", "HOLD"),
                    "reasoning": decision.get("reasoning", "Analysis via OpenCode CLI"),
                    "risk_factors": decision.get("risk_factors", []),
                    "source": "opencode_cli",
                }
            else:
                logger.warning(f"⚠️ No JSON found in OpenCode output: {output[:200]}")
                return {
                    "forecast_probability": stat.get("forecast_probability", 0.5),
                    "confidence": 40,
                    "signal": "HOLD",
                    "reasoning": output[:200],
                    "source": "opencode_cli_raw",
                }
                
        except Exception as e:
            logger.error(f"❌ Error running OpenCode CLI: {e}")
            return None

    async def _log_cli_prompt(self, type: str, data: dict) -> None:
        """Log a prompt to a local file for CLI simulation."""
        import json
        import os
        log_file = "/app/logs/ai_prompts.jsonl"
        os.makedirs("/app/logs", exist_ok=True)
        
        logger.debug(f"📝 CLI AI: Logging prompt of type '{type}' to {log_file}")
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "type": type,
            "data": data
        }
        
        try:
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
            logger.success(f"✅ CLI AI: Prompt logged to {log_file}")
        except Exception as e:
            logger.error(f"❌ Failed to log CLI prompt: {e}")

    async def ask_ai(self, question: str, context: dict) -> str:
        """
        Handle general user questions about the system or markets.
        """
        await self._ensure_client()
        
        # Build system context prompt
        context_str = (
            f"目前系統狀態:\n"
            f"- 模式: {context.get('mode')}\n"
            f"- 餘額: {context.get('current_balance'):.2f} USDC\n"
            f"- 已實現損益: {context.get('total_pnl', 0):.2f} USDC\n"
            f"- 未實現盈虧: {context.get('unrealized_pnl', 0):.2f} USDC\n"
            f"- 活躍市場數: {context.get('active_markets_count', 0)}\n"
            f"- 當前持倉數: {context.get('active_positions', 0)}\n"
            f"\n最近掃描到的市場:\n"
        )
        for m in context.get("recent_markets", []):
            context_str += f"- {m['city']}: {m['question']} (價格: {m['yes_price']})\n"

        prompt = (
            f"你是 POLY DREAM 助手。請根據以下背景資訊回答使用者的問題。\n"
            f"背景資訊:\n{context_str}\n\n"
            f"使用者問題: {question}\n\n"
            f"請用繁體中文回答，口吻要親切、專業且直白（白話文）。"
        )

        # Handle manual providers (CLI/OpenCode)
        if self._provider and self._provider.name in ["CLI Simulation", "OpenCode CLI"]:
            if self._provider.name == "OpenCode CLI":
                return await self._opencode_cli_analysis(prompt, "Text Response")
            else:
                logger.info(f"📟 [CLI MODE] Question: {question}")
                return "（模擬模式）我收到了您的問題，但我目前處於測試模式，無法實時連網回答。請配置真實的 AI Provider 以獲得完整功能。"

        try:
            from openai import AsyncOpenAI
            # Use raw client for non-structured chat
            raw_client = self._client.client if hasattr(self._client, "client") else self._client
            
            response = await raw_client.chat.completions.create(
                model=self._model,
                messages=[
                    {"role": "system", "content": "你是一個虛擬貨幣與預測市場交易系統的助手，名叫 POLY DREAM。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=500
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"❌ AI Q&A failed: {e}")
            return f"抱歉，我現在無法回答這個問題 (Error: {str(e)})"

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

# Project Research Summary

**Project:** Polymarket Weather Betting Automation
**Domain:** Automated Prediction Market Trading
**Researched:** 2026-03-15
**Confidence:** HIGH

## Executive Summary

This is an automated trading bot for Polymarket prediction markets, specifically focused on weather-related betting. The system compares official weather forecast probabilities against Polymarket market odds to identify arbitrage opportunities. The core value proposition is using AI (Claude API) to analyze weather data and detect when market prices diverge from actual forecast probabilities.

The recommended approach is a phased build starting with infrastructure and data collection, progressing through analysis and execution, and culminating in operations. The critical insight from research is that Polymarket trading requires a two-level authentication model (L1 private key + L2 API key) and explicit token approvals that trip up most developers. The system must enforce paper trading validation before live trading to avoid financial losses from untested strategies.

Key risks include: token allowance failures (most common pitfall), authentication confusion between L1/L2 levels, premature live trading without validation, and weather data mismatch with market resolution criteria. All of these have clear mitigation strategies documented in the research.

## Key Findings

### Recommended Stack

**Core technologies:**
- **Python 3.11+** — Required by all primary libraries (py_clob_client, anthropic, aiogram). 3.11+ recommended for performance.
- **py_clob_client** — Official Polymarket Python SDK. Supports market data, order creation, chain ID 137 (Polygon). Signature types: 0 (EOA), 1 (Email), 2 (Browser wallet).
- **anthropic** — Claude API SDK for AI probability analysis. Compares weather forecasts against market odds.
- **FastAPI** — Modern async web framework for REST API and dashboard. Built-in OpenAPI docs.
- **SQLite + aiosqlite** — Zero-config local database for single-instance deployment. Async operations via aiosqlite.
- **Open-Meteo** — Free weather API (no key required). 16-day forecast for global coordinates.
- **aiogram** — Modern async Telegram bot framework. Alternative: discord.py.

### Expected Features

**Must have (table stakes):**
- **Market Scanner** — Discovers active weather markets via Polymarket Gamma API
- **Price Fetcher** — Retrieves bid/ask/midpoint prices via CLOB client
- **Order Executor** — Places trades automatically via py_clob_client
- **Position Tracker** — Maintains holdings and P&L
- **Wallet Auth** — L1/L2 authentication (private key signing + API credentials)
- **Paper Trading Mode** — Simulates trades without real money
- **Basic Notifications** — Telegram/Discord alerts

**Should have (differentiators):**
- **Weather Data Integration** — Open-Meteo for forecast probabilities
- **AI Probability Analysis** — Claude API to compare forecast vs market odds
- **Arbitrage Detection** — Core value: find when forecast > odds by threshold (e.g., 5%)
- **Risk Management** — Position sizing, stop-loss, daily limits ($50/trade, $500/day)
- **Real-time Price Updates** — WebSocket feed for instant updates

**Defer (v2+):**
- Historical backtesting (needs data collection first)
- WebSocket feed (polling sufficient initially)
- Multi-strategy portfolio (single strategy first)

### Architecture Approach

The system uses an event-driven scanning pattern with mode-based execution (monitor/paper/live). Major components: Market Scanner, Price Fetcher, Weather Client, Signal Generator (AI), Arbitrage Detector, Risk Manager, Order Executor, Position Tracker, Notification Service. Data flows from scheduler through scanner → fetcher → weather → AI → arbitrage → risk → executor → position → notification.

Key patterns: Circuit breaker for API calls (handles Polymarket rate limits), repository pattern for data access, mode-based execution using strategy pattern.

### Critical Pitfalls

1. **Token Allowances Not Approved** — Most common failure. Both USDC and conditional tokens must be approved. Implement pre-trade checklist.
2. **Authentication Confusion (L1 vs L2)** — L1 (private key) for signing, L2 (API key) for faster requests. Orders require L1 signature.
3. **Premature Live Trading** — Enforce 1-week paper trading with documented P&L before live mode.
4. **Ignoring Market Liquidity** — Check order book, limit orders to <10% of visible liquidity.
5. **No Rate Limit Handling** — Implement caching, circuit breaker, exponential backoff to avoid IP bans.

## Implications for Roadmap

Based on research, suggested phase structure:

### Phase 1: Infrastructure
**Rationale:** Establishes foundation for all components. No external dependencies, low risk.
**Delivers:** Config management, database setup, repository classes, .gitignore for secrets
**Addresses:** Security (no hardcoded keys), data layer (storage/)
**Avoids:** Pitfall #10 (hardcoded private keys)

### Phase 2: Data Collection
**Rationale:** Must have market data and weather feeds before analysis. Can run in monitor mode without risk.
**Delivers:** Polymarket client (read-only), weather client (Open-Meteo), market scanner, price fetcher
**Addresses:** Market Scanner, Price Fetcher, Weather Data Integration
**Avoids:** Pitfalls #1 (token allowances - verify early), #6 (rate limits - implement caching), #7 (WebSocket freezes - fallback to REST)
**Research Flag:** Well-documented APIs, standard patterns — skip additional research

### Phase 3: Analysis
**Rationale:** Depends on data collection working. Core value generation.
**Delivers:** AI signal generator, arbitrage detector, liquidity checks
**Addresses:** AI Probability Analysis, Arbitrage Detection
**Avoids:** Pitfalls #5 (liquidity), #8 (weather data mismatch)
**Research Flag:** Claude API integration needs prompt tuning — consider small research task

### Phase 4: Execution
**Rationale:** Must validate in paper mode before risking real money.
**Delivers:** Order executor (paper first), position tracker, risk manager, stop-loss
**Addresses:** Order Executor, Position Tracker, Risk Management, Paper Trading Mode
**Avoids:** Pitfalls #3 (premature live), #4 (signature validation), #9 (no stop-loss), #11 (wallet mismatch)
**Research Flag:** Needs validation on test markets before live — add to requirements

### Phase 5: Operations
**Rationale:** Production hardening after basic functionality validated.
**Delivers:** Notification services, API/dashboard, P&L tracking, automated redemption
**Addresses:** Basic Notifications, P&L Calculator
**Avoids:** Pitfalls #12 (redemption issues), monitoring gaps

### Phase Ordering Rationale

- **1 → 2 → 3 → 4 → 5** follows natural dependencies: infrastructure enables data, data enables analysis, analysis enables execution, execution enables operations
- Mode-based execution pattern means all phases can run in monitor mode without financial risk
- Paper trading enforcement in Phase 4 prevents the most common cause of losses (premature live trading)
- Risk manager in Phase 4 is critical survival feature — must be in place before any live trading

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 3 (Analysis):** AI prompt engineering for weather vs odds comparison — needs iteration to optimize
- **Phase 4 (Execution):** Order signing edge cases between EOA and proxy wallet — verify with test trades

Phases with standard patterns (skip research-phase):
- **Phase 1 (Infrastructure):** Well-documented patterns for config, SQLite, .env handling
- **Phase 2 (Data Collection):** Polymarket APIs well-documented, Open-Meteo is simple REST

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All libraries verified against official sources (PyPI, docs). Version requirements confirmed. |
| Features | HIGH | Table stakes and differentiators clearly mapped to Polymarket API capabilities. |
| Architecture | MEDIUM | Patterns well-documented, but specific implementation details need validation during build. |
| Pitfalls | HIGH | Multiple sources (SDK docs, GitHub issues, community posts) confirm these pitfalls. |

**Overall confidence:** HIGH

### Gaps to Address

- **AI prompt optimization:** Signal generator quality depends on prompt engineering. Will need iteration during Phase 3.
- **Historical backtesting data:** Not currently available. Need to collect data first before implementing backtesting.
- **WebSocket reliability:** Research noted WebSocket can silently freeze. Need fallback mechanism tested in production.

## Sources

### Primary (HIGH confidence)
- Polymarket API Documentation (https://docs.polymarket.com) — Authentication, endpoints, CLOB client methods
- py_clob_client PyPI (https://pypi.org/project/py-clob-client/) — SDK installation, requirements, signature types
- Open-Meteo API Docs (https://open-meteo.com/en/docs) — Free weather API, no key required
- anthropic PyPI (https://pypi.org/project/anthropic/) — Claude SDK verified

### Secondary (MEDIUM confidence)
- py_clob_client GitHub Issues — Common pitfalls: signature failures, allowance errors, wallet mismatches
- Community posts on automated trading patterns

---

*Research completed: 2026-03-15*
*Ready for roadmap: yes*
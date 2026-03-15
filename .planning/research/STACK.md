# Stack Research

**Domain:** Automated Polymarket Trading Bot with AI Analysis
**Researched:** 2026-03-15
**Confidence:** HIGH

## Recommended Stack

### Core Technologies

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| Python | 3.10-3.13 | Core language | Required by all libraries below. Python 3.11+ recommended for performance. py_clob_client requires 3.9+, anthropic requires 3.9+, aiogram requires 3.10+. |
| py_clob_client | Latest (pip) | Polymarket API client | Official Python SDK from Polymarket. Supports market data, order creation, order management. Chain ID 137 (Polygon). Signature types 0 (EOA), 1 (Email), 2 (Browser wallet). |
| anthropic | 0.84.0+ | Claude API SDK | Official Python SDK for AI analysis. Requires Python 3.9+. Used to compare weather forecasts with market odds. |
| FastAPI | 3.x | Web framework | Modern async Python web framework. Built on Starlette and Pydantic. Automatic OpenAPI docs. Excellent for building REST APIs. uvicorn included in standard package. |

### Database

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| SQLAlchemy | 2.0.48 | ORM | Industry-standard Python ORM. Supports SQLite, PostgreSQL, MySQL. Async support via asyncio. Use with aiosqlite for async SQLite operations. |
| SQLite | Built-in | Local database | Zero-config, file-based. Perfect for single-instance trading bots. No setup required. Use aiosqlite for async operations. |

### Weather Data

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| Open-Meteo | API v1 | Weather forecasts | Free for non-commercial use. 16-day forecast. No API key required. HTTP GET endpoint. Alternative to OpenWeatherMap. |

### Notifications

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| aiogram | 3.26.0 | Telegram bot | Modern async Telegram framework. Full Bot API 9.5 support. Type hints, middleware, FSM support. MIT licensed. |
| discord.py | 2.7.1 | Discord bot | Modern async Discord framework. Proper rate limit handling. Optimized for speed and memory. |

### Supporting Libraries

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| aiohttp | Latest | Async HTTP client | When making concurrent API calls to Polymarket or weather services. Better than requests for async operations. |
| asyncio | Built-in | Async runtime | Required for all async operations. Built into Python 3.4+. |
| pydantic | Latest | Data validation | Required by FastAPI. Used for request/response validation and settings management. |
| python-dotenv | Latest | Environment variables | For loading API keys from .env files. Avoid hardcoding secrets. |
| APScheduler | Latest | Job scheduling | For running market scans on schedule (e.g., every 5 minutes). Alternative to cron. |

### Development Tools

| Tool | Purpose | Notes |
|------|---------|-------|
| pytest | Unit testing | Standard Python testing framework. Use pytest-asyncio for async tests. |
| black | Code formatting | Enforce consistent code style. |
| ruff | Linting | Fast Python linter, replaces flake8/isort. |
| mypy | Type checking | Catch type errors before runtime. All core libraries have type hints. |

## Installation

```bash
# Core dependencies
pip install python@3.11

# Polymarket & AI
pip install py-clob-client anthropic

# Web backend
pip install "fastapi[standard]" sqlalchemy aiosqlite

# Notifications (choose one or both)
pip install aiogram discord.py

# Supporting
pip install aiohttp python-dotenv pydantic-settings apscheduler

# Development
pip install pytest pytest-asyncio black ruff mypy
```

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| FastAPI | Flask | When you need synchronous-only operations or simpler setup. FastAPI preferred for async native support. |
| SQLite + aiosqlite | PostgreSQL | When you need multi-instance deployment or complex queries. SQLite simpler for single-instance bots. |
| Open-Meteo | OpenWeatherMap | OpenWeatherMap requires API key even for free tier. Open-Meteo is truly free for non-commercial. |
| aiogram | python-telegram-bot | aiogram is more modern and fully async. python-telegram-bot is older but well-maintained. |
| Claude (Anthropic) | OpenAI GPT | If you prefer OpenAI ecosystem. Claude recommended for cost-effectiveness per the project. |

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| requests library | Synchronous only, blocks event loop | aiohttp for async HTTP |
| psycopg2 (sync PostgreSQL) | Blocks event loop | asyncpg for async PostgreSQL |
| Celery + Redis | Overkill for single-bot deployment | APScheduler or asyncio.sleep in main loop |
| Django | Too heavy for a bot | FastAPI or Flask |
| Old polybag library | Deprecated, not maintained | py_clob_client (official) |
| asyncio.run in threads | Anti-pattern | Use proper async/await throughout |

## Stack Patterns by Variant

**If running on a single server with <1000 bets/day:**
- Use SQLite with aiosqlite
- Simple asyncio main loop with APScheduler for periodic scans
- No additional infrastructure needed

**If deploying on cloud with auto-scaling:**
- Use PostgreSQL (asyncpg)
- Separate worker processes for trading vs monitoring
- Redis for caching (optional)

**If paper trading mode:**
- Use SQLite (can reset easily)
- All same libraries, just don't call execute_order()
- Store simulated trades in database for P&L tracking

## Version Compatibility

| Package | Compatible With | Notes |
|---------|-----------------|-------|
| Python | 3.10-3.13 | aiogram requires 3.10+, others support 3.9+ |
| py_clob_client | Python 3.9+ | Official Polymarket SDK |
| anthropic | Python 3.9+ | Official Claude SDK |
| FastAPI | Python 3.8+ | Requires Pydantic v2 |
| aiogram | Python 3.10-3.14 | Requires 3.10+ |
| SQLAlchemy | Python 3.7-3.13 | 2.0+ requires 3.7+ |

## Sources

- https://docs.polymarket.com/api-reference/clients-sdks — Verified py_clob_client installation and methods
- https://github.com/Polymarket/py-clob-client — Verified Python 3.9+ requirement, signature types, order types
- https://pypi.org/project/anthropic/ — Verified version 0.84.0, Python >=3.9, MIT license
- https://pypi.org/project/sqlalchemy/ — Verified version 2.0.48, Python 3.7-3.13
- https://pypi.org/project/aiogram/ — Verified version 3.26.0, Python 3.10-3.14
- https://pypi.org/project/discord.py/ — Verified version 2.7.1, Python >=3.8
- https://open-meteo.com/en/docs — Verified free non-commercial use, no API key required
- https://fastapi.tiangolo.com/ — Verified FastAPI installation and Python 3.8+ requirement

---

*Stack research for: Polymarket Automated Trading Bot*
*Researched: 2026-03-15*
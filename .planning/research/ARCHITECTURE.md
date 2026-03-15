# Architecture Research

**Domain:** Polymarket Weather Betting Automation
**Researched:** 2026-03-15
**Confidence:** MEDIUM

## Standard Architecture

### System Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                        External APIs Layer                           │
├─────────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐ │
│  │ Polymarket  │  │  Open-Meteo │  │   NOAA      │  │ Notification│ │
│  │   CLOB      │  │    API      │  │   API       │  │  Services   │ │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘ │
│         │                │                │                │         │
├─────────┴────────────────┴────────────────┴────────────────┴─────────┤
│                      Core Engine Layer                               │
├─────────────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │                    Strategy Engine                            │    │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐        │    │
│  │  │ Arbitrage    │  │ Signal       │  │ Risk         │        │    │
│  │  │ Detector     │  │ Generator    │  │ Manager      │        │    │
│  │  └──────────────┘  └──────────────┘  └──────────────┘        │    │
│  └─────────────────────────────────────────────────────────────┘    │
├─────────────────────────────────────────────────────────────────────┤
│                    Execution Layer                                   │
├─────────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                  │
│  │ Order       │  │ Position    │  │ Paper       │                  │
│  │ Executor    │  │ Tracker     │  │ Trader      │                  │
│  └─────────────┘  └─────────────┘  └─────────────┘                  │
├─────────────────────────────────────────────────────────────────────┤
│                      Data Layer                                       │
├─────────────────────────────────────────────────────────────────────┤
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐             │
│  │ Market   │  │ Weather  │  │ Strategy │  │  P&L     │             │
│  │ Store    │  │ Store    │  │ Store    │  │ Store    │             │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘             │
└─────────────────────────────────────────────────────────────────────┘
```

### Component Responsibilities

| Component | Responsibility | Typical Implementation |
|-----------|----------------|----------------------|
| **Market Scanner** | Discovers active weather markets on Polymarket, filters by relevant events | Polls `get_simplified_markets()`, filters by condition title keywords |
| **Price Fetcher** | Retrieves real-time bid/ask/midpoint prices for market tokens | Calls `get_midpoint()`, `get_price()`, `get_order_book()` from ClobClient |
| **Weather Client** | Fetches weather forecasts for relevant geographic locations | Open-Meteo API (free) or NOAA API (paid), caches results |
| **Signal Generator** | Uses AI/LLM to compare weather probability vs market odds | Claude API calls with structured prompts comparing forecast to odds |
| **Arbitrage Detector** | Identifies when forecast probability exceeds market price by threshold | Simple threshold comparison (e.g., 5% spread) |
| **Risk Manager** | Enforces trading limits (max per trade, max daily, stop-loss) | In-memory checks before order submission |
| **Order Executor** | Places orders via ClobClient, handles retries and errors | `create_order()`, `post_order()` with exponential backoff |
| **Paper Trader** | Simulates trades without real money for validation | Records "trades" to local DB without API calls |
| **Position Tracker** | Maintains current holdings and calculates unrealized P&L | SQLite table tracking token_id, size, avg_price |
| **P&L Calculator** | Computes realized/unrealized profits and losses | Aggregates trade history with market settlement data |
| **Notification Service** | Sends alerts for trades, errors, daily summaries | Telegram Bot API or Discord webhooks |

## Recommended Project Structure

```
src/
├── config/
│   ├── settings.py          # Environment variables, mode (monitor/paper/live)
│   └── constants.py        # Trading limits, API endpoints
├── clients/
│   ├── polymarket/
│   │   ├── client.py       # ClobClient wrapper
│   │   ├── parser.py       # Parse market data responses
│   │   └── types.py        # Token, Market, Order dataclasses
│   ├── weather/
│   │   ├── open_meteo.py   # Open-Meteo API client
│   │   ├── noaa.py         # NOAA API client (optional)
│   │   └── types.py        # WeatherForecast, WeatherCondition
│   └── notification/
│       ├── telegram.py     # Telegram bot client
│       └── discord.py      # Discord webhook client
├── engine/
│   ├── scanner.py          # Market discovery
│   ├── fetcher.py          # Price data collection
│   ├── signal_generator.py # AI analysis
│   ├── arbitrage.py        # Opportunity detection
│   └── risk.py             # Risk checks
├── executor/
│   ├── order.py            # Order placement
│   ├── paper.py            # Paper trading simulation
│   └── position.py        # Position management
├── storage/
│   ├── database.py         # SQLite connection
│   ├── market_repo.py      # Market data persistence
│   ├── weather_repo.py     # Weather data persistence
│   ├── trade_repo.py       # Trade history
│   └── profit_repo.py      # P&L calculations
├── api/
│   ├── routes.py           # FastAPI endpoints
│   └── models.py           # Response schemas
├── main.py                 # Entry point, scheduler
└── tests/
    ├── unit/
    └── integration/
```

### Structure Rationale

- **clients/**: External API wrappers — isolated for easy testing and swapping implementations
- **engine/**: Core business logic — market scanning, signal generation, arbitrage detection
- **executor/**: Trade execution — order placement, paper trading, position tracking
- **storage/**: Data persistence — SQLite repositories for all data types
- **api/**: Web interface — FastAPI routes for dashboard
- **config/**: All configuration — single source of truth for settings

## Architectural Patterns

### Pattern 1: Event-Driven Scanning

**What:** Market scanning operates on a schedule (cron-like) rather than continuous polling
**When to use:** When market data doesn't require real-time sub-second updates
**Trade-offs:**
- Pro: Simple to implement, respects API rate limits
- Con: Misses opportunities between scans
- Mitigation: Use adaptive intervals (faster when opportunities detected)

**Example:**
```python
# main.py - scheduler loop
async def scan_loop():
    while True:
        markets = await scanner.find_weather_markets()
        for market in markets:
            price = await fetcher.get_price(market.token_id)
            weather = await weather_client.get_forecast(market.location)
            signal = await signal_generator.analyze(weather, price)
            if signal.opportunity:
                await arbitrage.check_and_execute(signal)
        await asyncio.sleep(SCAN_INTERVAL)
```

### Pattern 2: Mode-Based Execution

**What:** System supports three modes: monitor (observe only), paper (simulate), live (real trading)
**When to use:** Required for this project per constraints
**Trade-offs:**
- Pro: Safe validation path before real money
- Con: Additional code paths to maintain
- Mitigation: Use strategy pattern for executor

**Example:**
```python
class OrderExecutor:
    def __init__(self, mode: TradingMode):
        self.mode = mode

    async def execute(self, order: Order) -> TradeResult:
        if self.mode == TradingMode.MONITOR:
            logger.info(f"[MONITOR] Would execute: {order}")
            return TradeResult(success=True, simulated=True)
        elif self.mode == TradingMode.PAPER:
            return await self._simulate(order)
        else:
            return await self._submit_to_clob(order)
```

### Pattern 3: Circuit Breaker for API Calls

**What:** Wraps external API calls with retry logic and circuit breaker pattern
**When to use:** Polymarket CLOB API has rate limits; failures should not cascade
**Trade-offs:**
- Pro: Prevents cascade failures, provides backoff
- Con: Adds latency during outages
- Mitigation: Short timeouts, fallback to cached data

**Example:**
```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
async def get_price_with_retry(token_id: str) -> float:
    return await clob_client.get_midpoint(token_id)
```

### Pattern 4: Repository Pattern for Storage

**What:** Data access abstracted through repository classes
**When to use:** Any data persistence needed
**Trade-offs:**
- Pro: Testable, consistent API, easy to swap storage backend
- Con: Slight indirection overhead

**Example:**
```python
class MarketRepository:
    def __init__(self, db: Database):
        self.db = db

    async def save(self, market: Market) -> None:
        await self.db.execute(
            "INSERT OR REPLACE INTO markets VALUES (?, ?, ?, ?)",
            market.id, market.condition_id, market.question, market.token_id
        )
```

## Data Flow

### Trading Flow

```
[Scheduler Tick]
       │
       ▼
┌──────────────────┐
│ Market Scanner  │ ──► Find active weather markets
└────────┬─────────┘
         │ List[Market]
         ▼
┌──────────────────┐
│  Price Fetcher  │ ──► Get bid/ask for each token
└────────┬─────────┘
         │ Dict[token_id, PriceData]
         ▼
┌──────────────────┐
│ Weather Client  │ ──► Fetch forecasts for locations
└────────┬─────────┘
         │ Dict[location, WeatherForecast]
         ▼
┌──────────────────┐
│Signal Generator │ ──► LLM analyzes vs market odds
└────────┬─────────┘
         │ List[Signal]
         ▼
┌──────────────────┐
│Arbitrage Detector│ ──► Filter by threshold (5%)
└────────┬─────────┘
         │ List[Opportunity]
         ▼
┌──────────────────┐
│  Risk Manager   │ ──► Check limits (max $50/trade, $500/day)
└────────┬─────────┘
         │ List[ApprovedOpportunity]
         ▼
┌──────────────────┐
│ Order Executor  │ ──► Place order (or simulate)
└────────┬─────────┘
         │ TradeResult
         ▼
┌──────────────────┐
│ Position Tracker│ ──► Update holdings
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│Notification Serv│ ──► Send Telegram/Discord alert
└──────────────────┘
```

### State Management

```
┌─────────────────────────────────────────────────────────────────┐
│                        SQLite Database                           │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐            │
│  │ markets │  │ weather │  │ trades  │  │ positions│           │
│  └────┬────┘  └────┬────┘  └────┬────┘  └────┬────┘            │
└───────┼────────────┼────────────┼────────────┼──────────────────┘
        │            │            │            │
        ▼            ▼            ▼            ▼
┌─────────────────────────────────────────────────────────────────┐
│                     Repository Layer                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐           │
│  │MarketRepository│ │WeatherRepository│ │TradeRepository│        │
│  └──────────────┘  └──────────────┘  └──────────────┘           │
└─────────────────────────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Service Layer                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐           │
│  │ScannerService│  │SignalService │  │ExecutorService│          │
│  └──────────────┘  └──────────────┘  └──────────────┘           │
└─────────────────────────────────────────────────────────────────┘
```

### Key Data Flows

1. **Market Discovery Flow:** Scheduler → MarketScanner → PolymarketAPI → Database → Filtered Markets
2. **Signal Generation Flow:** Markets + PriceData + WeatherForecast → SignalGenerator (LLM) → Trading Signals
3. **Order Execution Flow:** Signal → RiskManager → OrderExecutor → ClobClient → TradeResult → PositionTracker → Notification
4. **P&L Calculation Flow:** Positions + MarketSettlement → P&L Calculator → Dashboard Data

## Scaling Considerations

| Scale | Architecture Adjustments |
|-------|--------------------------|
| 0-1K (current) | Single instance, SQLite, 5-minute scan interval fine |
| 1K-10K | Add Redis cache for weather data, reduce scan to 1 minute |
| 10K+ | Consider multiple scan workers, PostgreSQL, WebSocket for prices |

### Scaling Priorities

1. **First bottleneck: API rate limits**
   - Polymarket CLOB has request limits; cache market data locally
   - Implement exponential backoff with circuit breaker

2. **Second bottleneck: Database writes**
   - SQLite fine for single instance; migrate to PostgreSQL if multiple workers
   - Batch writes where possible

3. **Third bottleneck: LLM latency**
   - Signal generation is async; doesn't block scanning
   - Consider caching common scenarios

## Anti-Patterns

### Anti-Pattern 1: Real Trading Before Paper Validation

**What people do:** Jump straight to live trading to "test the system"
**Why it's wrong:** Strategy may be unprofitable; bugs cause real losses
**Do this instead:** Run in paper mode for at least 1 week, review P&L, then switch to live with small amounts

### Anti-Pattern 2: No Rate Limit Handling

**What people do:** Fire API requests as fast as possible
**Why it's wrong:** Polymarket will throttle/ban the IP; lost opportunities during cooldown
**Do this instead:** Implement request throttling, cache responses, use circuit breaker pattern

### Anti-Pattern 3: Hardcoded Credentials

**What people do:** Store private keys in source code
**Why it's wrong:** Accidental commit leaks funds
**Do this instead:** Use environment variables, secrets manager, or .env files with .gitignore

### Anti-Pattern 4: Ignoring Market Liquidity

**What people do:** Place large orders on thin markets
**Why it's wrong:** Slippage eats profits; may not fill at expected price
**Do this instead:** Check order book depth, limit order size to <10% of visible liquidity

### Anti-Pattern 5: No Stop-Loss

**What people do:** Hope positions recover
**Why it's wrong:** Weather markets can move against position significantly
**Do this instead:** Implement automatic stop-loss (e.g., 20% below entry), daily loss limit

## Integration Points

### External Services

| Service | Integration Pattern | Notes |
|---------|---------------------|-------|
| Polymarket CLOB | py_clob_client | Primary trading interface; supports read-only and trading modes |
| Open-Meteo | REST API (no key) | Free weather data; 7-day forecast; lat/long coordinates |
| NOAA Weather | REST API | More accurate but rate-limited; use as backup |
| Claude API | OpenAI-compatible | Signal generation via LLM; async calls |
| Telegram | Bot API | Notifications via bot messages |
| Discord | Webhook API | Notifications via embed messages |

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| Scanner ↔ Price Fetcher | Direct function call | Scanner passes market list; fetcher returns price dict |
| Price Fetcher ↔ Signal Generator | Direct function call | Both in same async loop |
| Signal Generator ↔ Risk Manager | Direct function call | Signal includes all info needed for risk checks |
| Risk Manager ↔ Order Executor | Direct function call | Executor receives approved opportunities |
| Any ↔ Database | Repository pattern | All data access via repository classes |

## Build Order (Dependencies)

Based on component dependencies, recommended build order:

1. **Phase 1: Infrastructure**
   - config/, database.py, repository classes
   - Establishes foundation for all other components

2. **Phase 2: Data Collection**
   - polymarket/client.py (read-only)
   - weather/open_meteo.py
   - Can test in monitor mode without risking funds

3. **Phase 3: Analysis**
   - signal_generator.py
   - arbitrage.py
   - Depends on data collection working

4. **Phase 4: Execution**
   - executor/order.py (paper mode first)
   - position_tracker.py
   - Risk manager

5. **Phase 5: Operations**
   - notification services
   - API/dashboard
   - P&L tracking

## Sources

- [Polymarket API Documentation](https://docs.polymarket.com)
- [py-clob-client PyPI](https://pypi.org/project/py-clob-client/)
- [Open-Meteo Weather API](https://open-meteo.com/en/docs)
- [ClobClient Source - Authentication and Order Methods](https://pypi.org/project/py-clob-client/)

---
*Architecture research for: Polymarket Weather Betting Automation*
*Researched: 2026-03-15*

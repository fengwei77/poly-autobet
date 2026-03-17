# 🌤️ Polymarket 天氣市場自動投注系統 — 完整系統機制規劃建置書

> **版本**: v2.0 (高併發多節點架構)  
> **日期**: 2026-03-15  
> **基礎框架**: Python 3.12 + uvloop + Redis Pub/Sub + Docker/OpenClaw  
> **目標平台**: Polymarket 天氣預測市場（415+ 活躍市場）  
> **執行環境**: Docker 主節點 + 手機端 (Termux/OpenClaw) 多節點協同

---

## 📋 目錄

1. [系統總覽](#1-系統總覽)
2. [系統架構圖](#2-系統架構圖)
3. [核心模組設計](#3-核心模組設計)
4. [數據源整合](#4-數據源整合)
5. [AI 分析引擎](#5-ai-分析引擎)
6. [自動投注策略引擎](#6-自動投注策略引擎)
7. [時間控制與篩選機制](#7-時間控制與篩選機制)
8. [利潤分析與風控系統](#8-利潤分析與風控系統)
9. [通知與監控系統](#9-通知與監控系統)
10. [技術棧與依賴](#10-技術棧與依賴)
11. [目錄結構](#11-目錄結構)
12. [部署與運行](#12-部署與運行)
13. [開發里程碑](#13-開發里程碑)
14. [風險評估](#14-風險評估)

---

## 1. 系統總覽

### 1.1 核心目標

建立一套**全自動化、高併發、多節點**的 Polymarket 天氣市場投注系統，能夠：

| 功能 | 說明 | 核心技術 |
|------|------|----------|
| 🔍 **即時市場掃描** | WebSocket 訂閱盤口，毫秒級接收價格變動 | aiohttp + uvloop |
| 🌡️ **多源天氣整合** | 非同步拉取 NOAA/OWM/Open-Meteo，交叉驗證 | httpx HTTP/2 |
| 🤖 **AI 結構化分析** | Claude + instructor 強制 JSON，貝葉斯機率更新 | anthropic + instructor |
| 🎯 **低延遲自動投注** | Redis Pub/Sub 派發訊號，多節點從利下單 | py_clob_client + Redis Lock |
| ⏰ **智慧時間控制** | 結算倒數篩選、自動平倉、黑名單時段 | asyncio 事件調度 |
| 💰 **即時損益追蹤** | Streamlit 儀表板 + 策略勝率分析 | Streamlit + PostgreSQL |
| 🛡️ **嚴格風控** | 停損停利、每日限額、分散式鎖防重複下單 | Redis Lock + Pydantic |
| 📢 **雙向通知** | Telegram Bot 推播 + 手動急停指令 | python-telegram-bot |
| 📱 **多節點協同** | Docker 大腦 + 手機純下單節點 | Redis Pub/Sub 跨網路 |

### 1.2 運作流程（高併發版）

```
┌────────────────┐    ┌─────────────────┐    ┌───────────────┐
│ 天氣 API (httpx) │──▶│ AI 引擎 (Claude)  │──▶│ 策略+風控     │
│ NOAA/OWM/Meteo  │    │ instructor JSON  │    │ 套利偵測+凱利  │
└────────────────┘    └─────────────────┘    └──────┬────────┘
                                                  │
┌────────────────┐    ┌─────────────────┐    │
│ Polymarket WS   │──▶│ ░░ Redis Pub/Sub ░░│◀─┘
│ 即時盤口串流    │    │ 交易訊號派發     │
└────────────────┘    └───┬──────┬──────┘
                         │          │
                    ┌────▼───┐ ┌──▼──────┐
                    │🐳 Docker│ │📱 手機端  │
                    │ 執行器  │ │ 執行器   │
                    └───┬────┘ └──┬──────┘
                         │          │
                    ┌────▼────────▼─────┐
                    │ Redis Lock ─▶ CLOB│
                    │ 防重複     ─▶ 下單│
                    └────────┬─────────┘
                             │
                    ┌────────▼─────────┐
                    │ Streamlit 儀表板   │
                    │ + Telegram 推播  │
                    └──────────────────┘
```

---

## 2. 系統架構圖（完整多節點高併發版）

### 2.1 總體系統架構

```mermaid
graph TB
    subgraph ExternalAPIs["☁️ 外部數據源"]
        NOAA["🌡️ NOAA Weather API"]
        OWM["🌦️ OpenWeatherMap"]
        OMETEO["🌍 Open-Meteo"]
        POLY_GAMMA["📊 Polymarket Gamma API<br/>(市場清單/快照)"]
        POLY_WS["⚡ Polymarket WebSocket<br/>(即時訂單簿串流)"]
    end

    subgraph DockerNode["🐳 Docker / OpenClaw 主節點 (大腦)"]
        direction TB

        subgraph DataIngestion["① 數據匯流層 (httpx + aiohttp)"]
            SCANNER["🔍 MarketScanner<br/>Gamma API 掃描<br/>+ WebSocket 訂閱盤口"]
            WEATHER["🌡️ WeatherCollector<br/>多源天氣數據非同步拉取<br/>(httpx HTTP/2)"]
        end

        subgraph AILayer["② AI 決策引擎 (Claude + instructor)"]
            STAT["📐 統計分析<br/>貝葉斯機率更新<br/>歷史準確率加權"]
            AI["🤖 AIAnalyzer<br/>Claude 結構化推理<br/>(instructor 強制 JSON)"]
            EDGE["📈 Edge 計算器<br/>套利空間 + 凱利公式<br/>信心度評分 0-100"]
        end

        subgraph StrategyRisk["③ 策略與風控層"]
            STRATEGY["🎯 StrategyEngine<br/>天氣套利 / 時間衰減<br/>動量跟蹤 / 多市場對沖"]
            RISK["🛡️ RiskManager<br/>停損停利 / 每日限額<br/>連續虧損暫停 / 倉位上限"]
            FILTER["⏰ MarketFilter<br/>時段控制 / 結算倒數篩選<br/>流動性門檻"]
        end
    end

    subgraph RedisHub["⚡ Redis 7+ (中央訊息匯流排)"]
        PUBSUB["📡 Pub/Sub Channel<br/>交易訊號即時派發"]
        LOCK["🔐 分散式鎖<br/>防重複下單保護"]
        CACHE["💾 快取層<br/>盤口快照 / 風控狀態"]
        STREAM["📜 Redis Stream<br/>交易日誌 / 審計軌跡"]
    end

    subgraph ExecutionNodes["⚙️ 交易執行節點 (可多實例)"]
        direction LR
        subgraph DockerExec["🐳 Docker 執行器"]
            EXEC1["TradeExecutor #1<br/>uvloop + orjson<br/>EIP-712 簽章"]
        end
        subgraph MobileExec["📱 手機端 (Termux/OpenClaw)"]
            EXEC2["TradeExecutor #2<br/>輕量 asyncio 模式<br/>純接單節點"]
        end
    end

    subgraph PolygonChain["⛓️ Polygon Mainnet"]
        CLOB["Polymarket CLOB API<br/>(限價單/市價單)"]
        CHAIN["Polygon PoS<br/>USDC 結算"]
    end

    subgraph MonitorLayer["📊 監控與報告層"]
        PNL["💰 PnLTracker<br/>即時損益 / 夏普比率<br/>最大回撤追蹤"]
        DASHBOARD["📺 Streamlit 儀表板<br/>策略勝率 / AI 推理日誌<br/>各城市績效熱圖"]
        TG["📱 Telegram Bot<br/>即時推播 + 手動急停<br/>持倉截圖回報"]
    end

    subgraph Storage["🗄️ 持久化存儲"]
        PG["🐘 PostgreSQL 15+<br/>(生產環境)"]
        SQLITE["📁 SQLite<br/>(開發/手機端)"]
    end

    %% 數據流入
    NOAA -->|"非同步 httpx"| WEATHER
    OWM -->|"非同步 httpx"| WEATHER
    OMETEO -->|"非同步 httpx"| WEATHER
    POLY_GAMMA -->|"REST 掃描"| SCANNER
    POLY_WS ==>|"WebSocket 持久連線<br/>(aiohttp)"| SCANNER

    %% 核心處理鏈
    SCANNER -->|"市場快照"| STAT
    WEATHER -->|"預報數據"| STAT
    STAT -->|"機率分佈"| AI
    AI -->|"結構化決策 JSON"| EDGE
    EDGE -->|"套利訊號"| STRATEGY
    STRATEGY --> FILTER
    FILTER -->|"合格市場"| RISK

    %% 風控通過後推送至 Redis
    RISK ==>|"✅ 通過風控"| PUBSUB
    RISK --> CACHE

    %% Redis 派發至執行節點
    PUBSUB ==>|"訂閱信號"| EXEC1
    PUBSUB ==>|"訂閱信號"| EXEC2
    EXEC1 --> LOCK
    EXEC2 --> LOCK
    LOCK -->|"獲鎖成功"| CLOB
    CLOB --> CHAIN

    %% 執行結果回流
    EXEC1 --> STREAM
    EXEC2 --> STREAM
    STREAM --> PNL
    PNL --> DASHBOARD
    PNL --> TG

    %% 持久化寫入
    SCANNER --> PG
    WEATHER --> PG
    AI --> PG
    PNL --> PG
    EXEC1 -.->|"手機端降級"| SQLITE

    %% 風控告警
    RISK -->|"⚠️ 觸發告警"| TG

    classDef external fill:#1a1a2e,stroke:#e94560,color:#fff
    classDef docker fill:#0f3460,stroke:#16213e,color:#fff
    classDef redis fill:#d63031,stroke:#e17055,color:#fff
    classDef exec fill:#00b894,stroke:#00cec9,color:#fff
    classDef monitor fill:#6c5ce7,stroke:#a29bfe,color:#fff
    classDef chain fill:#fdcb6e,stroke:#f39c12,color:#2d3436

    class NOAA,OWM,OMETEO,POLY_GAMMA,POLY_WS external
    class SCANNER,WEATHER,STAT,AI,EDGE,STRATEGY,RISK,FILTER docker
    class PUBSUB,LOCK,CACHE,STREAM redis
    class EXEC1,EXEC2 exec
    class PNL,DASHBOARD,TG monitor
    class CLOB,CHAIN chain
```

### 2.2 即時交易信號流程（毫秒級路徑）

```mermaid
sequenceDiagram
    autonumber
    participant WS as Polymarket WebSocket
    participant SC as MarketScanner<br/>(uvloop)
    participant REDIS as Redis Pub/Sub
    participant EX_D as Docker 執行器
    participant EX_M as 手機執行器
    participant LOCK as Redis Lock
    participant CLOB as Polymarket CLOB
    participant TG as Telegram Bot

    WS->>SC: 盤口變動推送 (WebSocket Frame)
    SC->>SC: orjson 極速解析 + Edge 快篩
    
    alt 發現套利機會 (Edge > 5%)
        SC->>REDIS: PUBLISH signal:trade {市場/方向/倉位}
        
        par 多節點並發接收
            REDIS->>EX_D: 訊號推送
            REDIS->>EX_M: 訊號推送
        end
        
        EX_D->>LOCK: SETNX 搶鎖 (market_id, TTL=30s)
        EX_M->>LOCK: SETNX 搶鎖 (market_id, TTL=30s)
        
        alt Docker 搶鎖成功
            LOCK-->>EX_D: ✅ 獲鎖
            LOCK-->>EX_M: ❌ 鎖已存在
            EX_D->>EX_D: EIP-712 離線簽章
            EX_D->>CLOB: POST /order (限價單/市價單)
            CLOB-->>EX_D: 訂單確認 (order_id)
            EX_D->>REDIS: PUBLISH result:trade {成交回報}
            EX_D->>LOCK: DEL 釋放鎖
            REDIS->>TG: 🟢 已下注通知
        else 手機搶鎖成功
            LOCK-->>EX_M: ✅ 獲鎖
            EX_M->>CLOB: POST /order
            CLOB-->>EX_M: 訂單確認
            EX_M->>LOCK: DEL 釋放鎖
            REDIS->>TG: 🟢 已下注通知 (手機端)
        end
    else 無套利機會
        SC->>SC: 繼續監聽下一幀
    end
```

### 2.3 AI 分析決策管線

```mermaid
flowchart LR
    subgraph INPUT["輸入數據"]
        W["🌡️ 天氣預報<br/>NOAA + OWM + Open-Meteo"]
        M["📊 市場盤口<br/>Polymarket 即時報價"]
        H["📚 歷史數據<br/>過去7天預報準確率"]
    end

    subgraph PROCESS["AI 處理管線"]
        direction TB
        S1["Step 1: 統計分析<br/>預報偏差 + 貝葉斯更新"]
        S2["Step 2: Claude 深度分析<br/>instructor 強制 JSON<br/>異常天氣模式識別"]
        S3["Step 3: 信心度評分<br/>綜合評分 0-100<br/>凱利公式倉位推薦"]
        S4["Step 4: 交易信號<br/>BUY / SELL / HOLD"]
        S1 --> S2 --> S3 --> S4
    end

    subgraph OUTPUT["輸出決策"]
        SIG["🎯 交易信號<br/>方向 + 價格 + 數量"]
        LOG["📝 AI 推理日誌<br/>分析理由 + 風險因素"]
    end

    W --> S1
    M --> S1
    H --> S1
    S4 --> SIG
    S4 --> LOG
```

### 2.4 多節點部署拓撲

```mermaid
graph LR
    subgraph CLOUD["☁️ 雲端 / VPS"]
        direction TB
        DC["🐳 Docker Compose 叢集"]
        DC --> APP["app 容器<br/>Python 3.12 + uvloop<br/>掃描 + AI + 策略"]
        DC --> RD["redis 容器<br/>Redis 7+<br/>Pub/Sub + Lock"]
        DC --> DB["postgres 容器<br/>PostgreSQL 15+<br/>持久化存儲"]
        DC --> ST["streamlit 容器<br/>Web 儀表板<br/>:8501"]
    end

    subgraph MOBILE["📱 手機端"]
        direction TB
        TM["Termux / UserLAnd"]
        TM --> PY["Python 3.12<br/>asyncio (fallback)"]
        PY --> CL["py_clob_client<br/>純下單執行器"]
        PY --> SQ["SQLite<br/>本地輕量日誌"]
    end

    subgraph OPENCLAW["🦞 OpenClaw 環境"]
        direction TB
        OC["Docker-in-Docker<br/>完整叢集鏡像"]
        OC --> APP2["完整 App 實例<br/>(與雲端同構)"]
        OC --> RD2["Redis 實例"]
    end

    RD <-->|"Redis Pub/Sub<br/>跨網路信號同步"| PY
    RD <-->|"Redis Pub/Sub<br/>叢集間同步"| RD2

    style CLOUD fill:#0f3460,stroke:#16213e,color:#fff
    style MOBILE fill:#00b894,stroke:#00cec9,color:#fff
    style OPENCLAW fill:#e17055,stroke:#d63031,color:#fff
```

---

## 3. 核心模組設計

### 3.1 市場掃描器 (`MarketScanner`)

```python
class MarketScanner:
    """掃描並追蹤 Polymarket 天氣市場 (即時極限優化版)"""
    
    # 核心功能
    - fetch_weather_markets()    # 透過 Gamma API 取得初始天氣市場列表
    - subscribe_orderbook()      # [即時] 建立 aiohttp Persistent WebSocket 訂閱目標盤口
    - filter_by_criteria()       # 按條件篩選（時間、交易量、類型）
    - stream_price_changes()     # [即時] 基於 uvloop 非阻塞處理報價 WebSocket 串流
    - publish_to_redis()         # [即時] 將異動盤口透過 Redis Pub/Sub 推播給分析節點或下單節點
    
    # 篩選條件
    - market_type: ["temperature", "precipitation", "earthquake", "extreme"]
    - min_volume: int            # 最低交易量門檻
    - min_liquidity: float       # 最低流動性門檻
    - time_to_resolution: tuple  # (最短, 最長) 結算時間
    - cities: list               # 指定城市
```

**Gamma API 調用方式**:
```
GET https://gamma-api.polymarket.com/events?tag_id={weather_tag_id}&active=true&closed=false
GET https://gamma-api.polymarket.com/markets?active=true&closed=false
```

### 3.2 天氣數據收集器 (`WeatherCollector`)

```python
class WeatherCollector:
    """整合多來源天氣預報數據 (非同步極速版)"""
    
    # 數據源 (全部透過 httpx HTTP/2 非同步並發拉取)
    - async noaa_forecast()            # NOAA 官方預報（美國城市）
    - async owm_forecast()             # OpenWeatherMap 全球預報
    - async open_meteo_forecast()      # Open-Meteo 免費全球預報 (無需 API Key)
    - async fetch_all_parallel()       # asyncio.gather() 並發拉取所有源
    - cross_validate()                 # 多源交叉驗證一致性
    - historical_accuracy()            # 歷史預報準確率分析
    
    # 支持的天氣指標
    - temperature_high/low       # 最高/最低溫度
    - precipitation              # 降雨量
    - wind_speed                 # 風速
    - humidity                   # 濕度
```

**NOAA API 調用流程** (httpx 非同步):
```python
async with httpx.AsyncClient(http2=True) as client:
    # Step 1: 取得該座標的預報網址
    points = await client.get(f"https://api.weather.gov/points/{lat},{lon}")
    # Step 2: 取得實際預報數據
    forecast = await client.get(points.json()["properties"]["forecast"])
```

**多源並發拉取範例**:
```python
async def fetch_all_parallel(self, city: str) -> dict:
    """asyncio.gather 同時拉取 3 個 API，總延遲 = 最慢的那個"""
    noaa, owm, meteo = await asyncio.gather(
        self.noaa_forecast(city),
        self.owm_forecast(city),
        self.open_meteo_forecast(city),
        return_exceptions=True  # 單一 API 失敗不影響其他
    )
    return self.cross_validate(noaa, owm, meteo)
```

### 3.3 AI 分析引擎 (`AIAnalyzer`)

```python
class AIAnalyzer:
    """使用 AI 模型分析市場機會 (結構化輸出版)"""
    
    # 分析流程 (全部 async)
    - async compare_forecast_vs_market()   # 預報 vs 市場賠率比對
    - async calculate_edge()               # 計算套利空間
    - async confidence_scoring()           # 信心度評分 (0-100)
    - async generate_recommendation()      # 生成投注建議 (instructor 強制 JSON)
    
    # AI 模型選擇
    - primary: Claude API + instructor     # 主分析 (強制 Pydantic Schema 輸出)
    - secondary: OpenAI GPT                # 備用/交叉驗證
    - local: 貝葉斯統計模型              # 本地快速計算 (無需 API 調用)
```

**instructor 結構化輸出範例**:
```python
import instructor
from pydantic import BaseModel
from anthropic import AsyncAnthropic

class TradeDecision(BaseModel):
    real_probability: float      # 真實機率估計 (0-1)
    confidence: int              # 信心度 0-100
    signal: str                  # BUY | SELL | HOLD
    reasoning: str               # 分析理由
    risk_factors: list[str]      # 風險因素

client = instructor.from_anthropic(AsyncAnthropic())
decision = await client.messages.create(
    model="claude-3-5-sonnet-20241022",
    response_model=TradeDecision,  # 強制輸出符合 Schema
    messages=[{"role": "user", "content": analysis_prompt}]
)
# decision.signal 保證是 "BUY"|"SELL"|"HOLD"，不會出現幻覺
```

### 3.4 策略引擎 (`StrategyEngine`)

```python
class StrategyEngine:
    """投注策略決策中心"""
    
    # 策略類型
    - weather_arbitrage()        # 天氣套利策略（核心）
    - momentum_strategy()        # 動量策略（跟隨價格趨勢）
    - mean_reversion()           # 均值回歸策略
    - multi_market_hedge()       # 多市場對沖策略
    
    # 決策參數
    - min_edge: float            # 最低套利空間 (預設 5%)
    - confidence_threshold: int  # 最低信心度 (預設 70)
    - kelly_fraction: float      # 凱利公式投注比例
```

---

## 4. 數據源整合

### 4.1 Polymarket API 矩陣

| API | 用途 | 認證 | 頻率限制 | 連線模式 |
|-----|------|------|----------|----------|
| **Gamma API** | 市場發現、價格快照 | 不需要 | 合理使用 | REST (httpx) |
| **WebSocket** | 即時盤口變動 | 不需要 | 持久連線 | aiohttp WS |
| **CLOB API** | 交易下單、訂單管理 | API Key + EIP-712 | 有限制 | REST (httpx) |
| **Data API** | 用戶倉位、歷史記錄 | API Key | 有限制 | REST (httpx) |

### 4.2 天氣數據 API 矩陣

| API | 覆蓋範圍 | 免費額度 | 認證 |
|-----|----------|----------|------|
| **NOAA NWS** | 美國 | 無限（需 User-Agent） | 免費 |
| **OpenWeatherMap** | 全球 | 1,000 次/天 | API Key（免費） |
| **Visual Crossing** | 全球 | 1,000 次/天 | API Key（免費） |
| **Open-Meteo** | 全球 | 無限 | 不需要 |

### 4.3 城市與市場對應表

```python
CITY_CONFIG = {
    "tokyo": {
        "lat": 35.6762, "lon": 139.6503,
        "weather_api": "openweathermap",
        "polymarket_tag": "tokyo-temperature",
        "timezone": "Asia/Tokyo"
    },
    "new_york": {
        "lat": 40.7128, "lon": -74.0060,
        "weather_api": "noaa",
        "polymarket_tag": "nyc-temperature",
        "timezone": "America/New_York"
    },
    "london": {
        "lat": 51.5074, "lon": -0.1278,
        "weather_api": "openweathermap",
        "polymarket_tag": "london-temperature",
        "timezone": "Europe/London"
    },
    # ... 更多城市配置
}
```

---

## 5. AI 分析引擎

### 5.1 分析管線 (Analysis Pipeline)

```
                    ┌────────────────────────────┐
                    │      輸入數據彙整           │
                    │  天氣預報 + 市場價格 + 歷史  │
                    └─────────┬──────────────────┘
                              │
                    ┌─────────▼──────────────────┐
                    │   Step 1: 統計分析           │
                    │   - 預報 vs 市場偏差計算     │
                    │   - 歷史準確率加權           │
                    │   - 貝葉斯機率更新           │
                    └─────────┬──────────────────┘
                              │
                    ┌─────────▼──────────────────┐
                    │   Step 2: AI 深度分析        │
                    │   - Claude/GPT 多因素評估    │
                    │   - 異常天氣模式識別         │
                    │   - 市場心理面分析           │
                    └─────────┬──────────────────┘
                              │
                    ┌─────────▼──────────────────┐
                    │   Step 3: 信心度評分          │
                    │   - 綜合評分 (0-100)         │
                    │   - 套利空間 (edge%)          │
                    │   - 建議倉位大小              │
                    └─────────┬──────────────────┘
                              │
                    ┌─────────▼──────────────────┐
                    │   Step 4: 輸出交易信號        │
                    │   BUY / SELL / HOLD          │
                    │   + 建議價格 + 數量           │
                    └──────────────────────────────┘
```

### 5.2 套利偵測邏輯

```python
def detect_arbitrage(forecast_prob: float, market_price: float) -> dict:
    """
    核心套利邏輯：比較天氣預報機率 vs Polymarket 價格
    
    例子：
    - NOAA 預報東京明天最高溫 13°C 的機率 = 95%
    - Polymarket 該市場目前價格 = $0.75 (75%)
    - 套利空間 = 95% - 75% = 20% → 買入信號！
    
    參數:
        forecast_prob: 天氣預報計算的真實機率 (0-1)
        market_price: Polymarket 當前市場價格 (0-1)
    
    回傳:
        {
            "signal": "BUY" | "SELL" | "HOLD",
            "edge": float,          # 套利空間百分比
            "confidence": int,      # 信心度 0-100
            "suggested_size": float, # 建議倉位 (USDC)
            "kelly_pct": float       # 凱利公式建議比例
        }
    """
    edge = forecast_prob - market_price
    
    # 凱利公式: f* = (bp - q) / b
    # b = 賠率, p = 勝率, q = 1-p
    if market_price > 0 and market_price < 1:
        b = (1 / market_price) - 1  # 賠率
        kelly = (b * forecast_prob - (1 - forecast_prob)) / b
    
    if edge > 0.05:  # 套利空間 > 5%
        return {"signal": "BUY", "edge": edge, ...}
    elif edge < -0.05:
        return {"signal": "SELL", "edge": abs(edge), ...}
    else:
        return {"signal": "HOLD", "edge": 0, ...}
```

### 5.3 AI Prompt 模板

```python
ANALYSIS_PROMPT = """
你是一個天氣預測市場分析師。根據以下數據進行分析：

## 市場資訊
- 市場: {market_question}
- 當前價格: {current_price} (代表 {current_price*100}% 機率)
- 交易量: ${volume}
- 結算時間: {resolution_time}

## 天氣預報數據
- NOAA 預報: {noaa_forecast}
- OpenWeatherMap: {owm_forecast}
- 預報一致性: {forecast_agreement}

## 歷史數據
- 過去 7 天該城市預報準確率: {historical_accuracy}%
- 類似市場的歷史結果: {similar_outcomes}

請分析並回傳 JSON 格式：
{
  "真實機率估計": float (0-1),
  "信心度": int (0-100),
  "套利方向": "BUY" | "SELL" | "HOLD",
  "分析理由": "string",
  "風險因素": ["string"]
}
"""
```

---

## 6. 自動投注策略引擎

### 6.1 策略一覽

| 策略名稱 | 核心邏輯 | 適用場景 | 風險等級 |
|----------|----------|----------|----------|
| **天氣套利** | 預報 vs 市場價差 | 溫度/降雨預測 | ⭐⭐ 中 |
| **時間衰減** | 結算前價格收斂 | 高確定性市場 | ⭐ 低 |
| **動量跟蹤** | 價格趨勢跟隨 | 快速變化市場 | ⭐⭐⭐ 高 |
| **多市場對沖** | 相關市場套利 | 同城市不同指標 | ⭐⭐ 中 |

### 6.2 天氣套利策略（核心策略）

```python
class WeatherArbitrageStrategy:
    """
    核心策略：比較官方天氣預報 vs Polymarket 市場價格
    當兩者之間存在顯著差異時，下注預報方向
    """
    
    config = {
        "min_edge": 0.05,           # 最低 5% 套利空間才下注
        "max_position_pct": 0.10,   # 單一市場最大倉位 = 總資金 10%
        "confidence_threshold": 70, # 信心度 >= 70 才下注
        "use_kelly": True,          # 使用凱利公式計算倉位
        "kelly_fraction": 0.25,     # 凱利公式打折（保守）
        "max_bet_amount": 50,       # 單筆最大下注 $50 USDC
        "min_bet_amount": 2,        # 單筆最小下注 $2 USDC
    }
```

### 6.3 交易執行流程 (毫秒級優化)

```python
class TradeExecutor:
    """透過 py_clob_client 執行交易 (低延遲/防重複架構)"""
    
    async def execute_trade(self, signal: dict) -> dict:
        """
        異步交易執行流程 (適用手機/Docker Node):
        1. 獲取 Redis 分散式鎖 (Lock) — 確保同一市場瞬間不重複下單
        2. 快取風控檢查（避免阻塞式 DB 查詢）
        3. 計算最佳下單價格和數量 (或採用 Market Order 搶單)
        4. EIP-712 離線極速簽章
        5. 透過 asyncio.gather() 或 Task 並發推播至 CLOB API
        6. 監控訂單狀態並釋放鎖
        7. 異步派發交易日誌 (Loguru + Redis Stream)
        """
        
    # py_clob_client 初始化
    # client = ClobClient(
    #     host="https://clob.polymarket.com",
    #     key=PRIVATE_KEY,
    #     chain_id=137,  # Polygon mainnet
    #     signature_type=2  # POLY_GNOSIS_SAFE
    # )
    
    # 下單範例
    # order = client.create_and_post_order(OrderArgs(
    #     token_id=token_id,
    #     price=target_price,
    #     size=position_size,
    #     side=BUY,
    #     fee_rate_bps=0
    # ))
```

---

## 7. 時間控制與篩選機制

### 7.1 時間控制參數

```python
TIME_CONTROL = {
    # 掃描排程
    "scan_interval_minutes": 15,        # 每 15 分鐘掃描一次市場
    "deep_analysis_interval": 60,        # 每 60 分鐘深度 AI 分析
    
    # 投注時段控制
    "trading_hours": {
        "enabled": True,
        "start_utc": "00:00",           # UTC 開始時間
        "end_utc": "23:59",             # UTC 結束時間
        "blackout_periods": [            # 禁止交易時段
            {"start": "03:00", "end": "05:00"},  # 低流動性時段
        ]
    },
    
    # 結算時間篩選
    "resolution_time_filter": {
        "min_hours_before": 2,           # 至少距結算 2 小時才投注
        "max_hours_before": 48,          # 最多距結算 48 小時內的市場
        "sweet_spot_hours": (4, 24),     # 最佳投注時段：結算前 4-24 小時
    },
    
    # 自動結束
    "auto_exit_hours_before_resolution": 1,  # 結算前 1 小時自動出場
}
```

### 7.2 篩選邏輯

```python
class MarketFilter:
    """市場篩選器"""
    
    def apply_filters(self, markets: list) -> list:
        """
        篩選條件（按順序執行）：
        
        1. 市場類型篩選  → 只保留天氣相關市場
        2. 活躍狀態篩選  → 只保留未結算的活躍市場
        3. 交易量篩選    → volume >= $1,000
        4. 流動性篩選    → 訂單簿深度足夠
        5. 時間篩選      → 距結算時間在合理範圍內
        6. 城市篩選      → 只追蹤已配置天氣 API 的城市
        7. 重複篩選      → 避免同一城市/指標重複投注
        """
```

### 7.3 排程器配置

```python
SCHEDULER_CONFIG = {
    "jobs": [
        {
            "name": "market_scan",
            "function": "scanner.scan_all_weather_markets",
            "trigger": "interval",
            "minutes": 15
        },
        {
            "name": "weather_update",
            "function": "collector.update_all_forecasts",
            "trigger": "interval",
            "minutes": 30
        },
        {
            "name": "ai_analysis",
            "function": "analyzer.run_full_analysis",
            "trigger": "interval",
            "minutes": 60
        },
        {
            "name": "portfolio_check",
            "function": "portfolio.check_positions",
            "trigger": "interval",
            "minutes": 5
        },
        {
            "name": "daily_report",
            "function": "pnl.generate_daily_report",
            "trigger": "cron",
            "hour": 23,
            "minute": 59
        }
    ]
}
```

---

## 8. 利潤分析與風控系統

### 8.1 利潤追蹤 (`PnLTracker`)

```python
class PnLTracker:
    """即時利潤/損失追蹤"""
    
    # 追蹤指標
    - total_invested: float        # 總投入金額
    - total_returned: float        # 總回收金額
    - realized_pnl: float          # 已實現損益
    - unrealized_pnl: float        # 未實現損益
    - win_rate: float              # 勝率
    - avg_return: float            # 平均回報率
    - sharpe_ratio: float          # 夏普比率
    - max_drawdown: float          # 最大回撤
    
    # 報表功能
    - daily_summary()              # 每日損益摘要
    - weekly_report()              # 每週績效報告
    - strategy_breakdown()         # 各策略績效拆分
    - city_performance()           # 各城市投注績效
```

### 8.2 風控系統 (`RiskManager`)

```python
class RiskManager:
    """風險控制系統 — 每筆交易都必須通過風控檢查"""
    
    RISK_LIMITS = {
        # 金額限制
        "max_single_bet": 50,           # 單筆最大 $50
        "max_daily_exposure": 500,       # 每日最大總曝險 $500
        "max_total_exposure": 2000,      # 最大總曝險 $2,000
        
        # 停損機制
        "stop_loss_pct": 0.20,           # 單一倉位停損 -20%
        "daily_stop_loss": 100,          # 每日最大虧損 $100
        "weekly_stop_loss": 300,         # 每週最大虧損 $300
        
        # 倉位管理
        "max_positions": 20,             # 最多同時 20 個倉位
        "max_per_city": 3,               # 同一城市最多 3 個倉位
        "max_correlation": 0.7,          # 相關市場倉位限制
        
        # 暫停機制
        "consecutive_loss_pause": 5,     # 連續虧損 5 次暫停交易
        "pause_duration_hours": 6,       # 暫停 6 小時
    }
    
    def check_trade(self, trade: dict) -> tuple[bool, str]:
        """
        風控檢查清單:
        ✅ 單筆金額未超限
        ✅ 每日曝險未超限
        ✅ 今日虧損未達停損
        ✅ 未達連續虧損暫停條件
        ✅ 同一城市倉位未滿
        ✅ 流動性足夠（能順利出場）
        ✅ 距結算時間合理
        """
```

### 8.3 利潤分析儀表板數據

```python
DASHBOARD_METRICS = {
    "realtime": {
        "current_balance": "USDC 餘額",
        "open_positions": "未結倉位數/金額",
        "unrealized_pnl": "未實現損益",
        "today_pnl": "今日損益",
    },
    "performance": {
        "total_return": "累計回報率",
        "win_rate": "勝率",
        "avg_profit_per_trade": "平均每筆收益",
        "best_trade": "最佳交易",
        "worst_trade": "最差交易",
        "sharpe_ratio": "夏普比率",
    },
    "breakdown": {
        "by_city": "各城市績效",
        "by_strategy": "各策略績效",
        "by_weather_type": "各天氣類型績效",
        "by_time_of_day": "各時段績效",
    }
}
```

---

## 9. 通知與監控系統

### 9.1 通知渠道

| 渠道 | 用途 | 雙向能力 | 設定方式 |
|------|------|----------|----------|
| **Telegram Bot** | 主要通知 + 手動控制 | ✅ 支援「急停」「清倉」「狀態」指令 | BotFather |
| **Streamlit Dashboard** | 即時監控儀表板 | ✅ Web UI 操作 | 本地/雲端 :8501 |
| **Redis Stream** | 內部事件日誌 | ❌ 單向審計 | 自動配置 |

### 9.2 Telegram Bot 雙向指令

```python
# 推播通知 (系統 → 用戶)
NOTIFICATION_TYPES = {
    "trade_executed": "🟢 已下注 | {market} | {side} ${amount} @ {price}",
    "opportunity_found": "🔍 發現機會 | {market} | 套利: {edge}%",
    "position_resolved": "💰 已結算 | {market} | P&L: ${pnl}",
    "risk_alert": "⚠️ 風控警報 | {alert_type} | {details}",
    "daily_report": "📊 每日報告 | P&L: ${pnl} | 勝率: {win_rate}%",
}

# 接收指令 (用戶 → 系統)
BOT_COMMANDS = {
    "/status": "查詢當前持倉、餘額、未實現損益",
    "/stop": "緊急停止所有交易活動",
    "/resume": "恢復交易活動",
    "/close <market_id>": "手動平倉特定市場",
    "/pnl": "查詢今日損益摘要",
    "/config <key> <value>": "動態調整風控參數",
}
```

### 9.2 通知類型

```python
NOTIFICATION_TYPES = {
    "trade_executed": {
        "template": "🟢 已下注 | {market} | {side} ${amount} @ {price}",
        "channels": ["telegram", "discord"],
        "priority": "high"
    },
    "opportunity_found": {
        "template": "🔍 發現機會 | {market} | 套利空間: {edge}%",
        "channels": ["telegram"],
        "priority": "medium"
    },
    "position_resolved": {
        "template": "💰 已結算 | {market} | {result} | P&L: ${pnl}",
        "channels": ["telegram", "discord"],
        "priority": "high"
    },
    "risk_alert": {
        "template": "⚠️ 風控警報 | {alert_type} | {details}",
        "channels": ["telegram", "discord", "email"],
        "priority": "critical"
    },
    "daily_report": {
        "template": "📊 每日報告 | P&L: ${pnl} | 勝率: {win_rate}%",
        "channels": ["telegram", "email"],
        "priority": "low"
    }
}
```

---

## 10. 技術棧與依賴 (優化版)

### 10.1 核心架構與依賴

> **優化建議**: 建議捨棄純 `requirements.txt`，改用 **Poetry** 或 **uv** 進行現代化套件與虛擬環境管理，確保生產環境依賴的穩定性。同時引入 `Redis` 與 `httpx` 以強化高併發處理能力與鎖機制。

```toml
# pyproject.toml / 主要依賴

# 基礎架構 & 異步網路 (極致效能版)
httpx = "^0.27.0"               # 替代 requests，提供原生全異步 HTTP 支援 (搭配 HTTP/2)
aiohttp = "^3.9.3"              # 用於建立持久化 WebSocket 連線 (Polymarket 即時報價)
asyncio = "^3.4.3"              # 異步核心
uvloop = "^0.19.0"              # 取代預設 asyncio loop，提供 CPython 下與 Node.js 匹敵的極致 IO 效能 (Linux/Docker 限定)
orjson = "^3.9.15"              # 極速 JSON 序列化/反序列化 (Rust 核心，比標準庫快 10 倍以上)

# Polymarket 交易
py-clob-client = "^0.18.0"      # Polymarket CLOB 客戶端
web3 = "^6.0.0"                 # Ethereum/Polygon 互動 (支援 Websocket Provider)

# AI 分析與數據提取
anthropic = "^0.25.0"           # Claude API
instructor = "^1.2.0"           # 優化 LLM 輸出結構化 JSON 的神器（搭配 Claude）
openai = "^1.30.0"              # OpenAI GPT API（備用）

# 數據處理
pandas = "^2.2.0"               # 數據分析
numpy = "^1.26.0"               # 數值計算

# 快取、派發與資料庫
redis = "^5.0.3"                # 必備：Pub/Sub 即時分發、分散式鎖、API Rate Limit 防護
sqlalchemy = "^2.0.29"          # ORM (支援 asyncpg)
asyncpg = "^0.29.0"             # PostgreSQL 異步驅動（生產環境建議替代 SQLite）
alembic = "^1.13.1"             # 資料庫 Schema 遷移

# Web 儀表板與通知
fastapi = "^0.110.0"            # Web API 框架
uvicorn = "^0.29.0"             # ASGI 伺服器
streamlit = "^1.33.0"           # 內部管理儀表板（大幅節省前端開發工時）
python-telegram-bot = "^21.0"   # Telegram Bot 異步版

# 工程化工具
pydantic = "^2.6.0"             # 嚴格的型別與數據驗證
loguru = "^0.7.2"               # 非同步日誌記錄
pytest = "^8.1.1"               # 單元與整合測試框架
ruff = "^0.3.5"                 # 極速 Linter & Formatter
```

### 10.2 運行環境與執行端優化

- **語言版本**: Python 3.12+ (利用最新的 asyncio 效能優化與型別推斷)
- **非同步事件迴圈**: **強制使用 `uvloop`** (大幅降低 Socket 延遲，提升高頻並發量)
- **資料庫**: 
  - 開發期：SQLite
  - 生產期：PostgreSQL 15+ + Redis 7+
- **容器化與多端配置**: 
  1. **Docker / OpenClaw 環境**: 主力執行環境，分配足夠 CPU 核心跑 `uvloop` 與多進程(multiprocessing) worker，專門負責 AI 高耗能分析與 Redis Pub/Sub 派發。
  2. **手機端 (Termux/UserLAnd 或輕量化 Client)**: 若計畫在手機本地跑節點，系統將自動偵測架構降級 (禁用 `uvloop` 若不支援、改用輕量 Sqlite)，並作為獨立的「觀測節點」或「純下單節點」(接收主伺服器 Redis 推送的交易訊號直接調用 Clob client 下單，達成毫秒級延遲)。

### 10.3 外部基礎設施費用預估

| 服務 | 用途 | 規格/頻率 | 預估月費 |
|------|------|----------|----------|
| **Polymarket/Polygon**| 交易 API & Gas | 低頻率寫入 | 免費 / 微量 MATIC |
| **天氣 API (NOAA等)** | 即時天氣數據 | 高頻輪詢 | 免費層級即可涵蓋 |
| **Claude 3.5 Sonnet** | AI 決策引擎 | 每日 ~100 次分析 | ~$5 - $15 USD |
| **VPS (DigitalOcean/AWS)** | 系統託管 | 2 vCPU / 4GB RAM | ~$20 USD |
| **Managed DB (可選)** | PostgreSQL+Redis | 基礎規格 | ~$15 USD |

---

## 11. 目錄結構（高併發多節點版）

```
poly-autobet/
│
├── 📁 config/
│   ├── settings.py              # 全局設定 (Pydantic BaseSettings)
│   ├── cities.py                # 城市配置 + 座標 + 時區
│   ├── strategies.py            # 策略參數
│   └── .env                     # 環境變數（API Keys）
│
├── 📁 core/
│   ├── __init__.py
│   ├── scanner.py               # 市場掃描器 (WebSocket + Gamma API)
│   ├── weather_collector.py     # 天氣數據收集器 (httpx 並發)
│   ├── ai_analyzer.py           # AI 分析引擎 (Claude + instructor)
│   ├── strategy_engine.py       # 策略引擎
│   ├── trade_executor.py        # 交易執行器 (async + Redis Lock)
│   ├── risk_manager.py          # 風控系統 (Redis 快取狀態)
│   └── portfolio_manager.py     # 倉位管理
│
├── 📁 infra/                     # ★ 新增：基礎設施層
│   ├── __init__.py
│   ├── redis_client.py          # Redis 連線池 + Pub/Sub + Lock 封裝
│   ├── event_loop.py            # uvloop 初始化 + 環境偵測 (Linux/手機)
│   └── json_utils.py            # orjson 序列化工具
│
├── 📁 data/
│   ├── __init__.py
│   ├── models.py                # SQLAlchemy 2.0 異步模型
│   ├── database.py              # 資料庫連接 (asyncpg/SQLite 雙模式)
│   └── migrations/              # Alembic 遷移
│
├── 📁 analysis/
│   ├── __init__.py
│   ├── pnl_tracker.py           # 利潤追蹤
│   ├── backtest.py              # 回測引擎
│   ├── statistics.py            # 貝葉斯統計分析
│   └── reports.py               # 報表生成
│
├── 📁 notifications/
│   ├── __init__.py
│   └── telegram_bot.py          # Telegram 雙向 Bot (推播 + 接收指令)
│
├── 📁 dashboard/
│   └── streamlit_app.py         # Streamlit 儀表板 (單檔即可運作)
│
├── 📁 tests/
│   ├── test_scanner.py
│   ├── test_analyzer.py
│   ├── test_strategy.py
│   ├── test_executor.py
│   ├── test_risk.py
│   └── test_infra.py            # ★ 新增：Redis Lock / uvloop 測試
│
├── 📁 scripts/
│   ├── setup_wallet.py          # 錢包設定腳本
│   ├── backtest_runner.py       # 回測執行腳本
│   └── mobile_node.py           # ★ 新增：手機端純下單節點啟動器
│
├── main.py                      # 主程式入口 (Docker 主節點)
├── pyproject.toml               # Poetry 依賴管理 (替代 requirements.txt)
├── Dockerfile                   # 生產環境 Docker 映像
├── docker-compose.yml           # 多容器編排 (app+redis+pg+streamlit)
└── README.md                    # 使用說明
```

---

## 12. 部署與運行（多節點版）

### 12.1 部署架構

| 方式 | 適合場景 | 花費 | 角色 |
|------|----------|------|------|
| **Docker Compose (本地)** | 開發測試 | 免費 | 全功能主節點 |
| **VPS (DigitalOcean/AWS)** | 24/7 生產運行 | ~$20/月 | 大腦節點 |
| **OpenClaw Docker** | 備援運算節點 | 衍生費用 | 完整叢集鏡像 |
| **手機 Termux** | 行動下單節點 | 免費 | 純執行器 |

### 12.2 Docker Compose 多容器編排

```yaml
# docker-compose.yml
version: "3.9"
services:
  app:
    build: .
    environment:
      - TRADING_MODE=paper
      - REDIS_URL=redis://redis:6379
      - DATABASE_URL=postgresql+asyncpg://user:pass@postgres:5432/polybet
    depends_on: [redis, postgres]
    restart: always

  redis:
    image: redis:7-alpine
    ports: ["6379:6379"]
    volumes: ["redis_data:/data"]

  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: polybet
      POSTGRES_USER: user
      POSTGRES_PASSWORD: pass
    volumes: ["pg_data:/var/lib/postgresql/data"]

  streamlit:
    build: .
    command: streamlit run dashboard/streamlit_app.py --server.port 8501
    ports: ["8501:8501"]
    depends_on: [redis, postgres]

volumes:
  redis_data:
  pg_data:
```

### 12.3 運行模式

```bash
# Docker 主節點
docker compose up -d                          # 啟動全部服務
docker compose logs -f app                    # 查看主程式日誌

# 單機運行模式
python main.py --mode monitor                 # 僅監控（不下單）
python main.py --mode paper                   # 模擬交易
python main.py --mode live                    # 實盤交易
python main.py --mode backtest --start 2026-01-01  # 回測

# 手機端純下單節點
python scripts/mobile_node.py --redis-url redis://<主節點 IP>:6379
```

### 12.4 環境變數

```env
# .env 檔案

# Polymarket
POLYMARKET_PRIVATE_KEY=your_private_key_here
POLYMARKET_API_KEY=your_api_key
POLYMARKET_API_SECRET=your_api_secret
POLYMARKET_PASSPHRASE=your_passphrase

# 天氣 API
OPENWEATHERMAP_API_KEY=your_owm_key
NOAA_USER_AGENT=poly-autobet/1.0

# AI
ANTHROPIC_API_KEY=your_claude_key

# Redis & DB
REDIS_URL=redis://localhost:6379
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/polybet

# 通知
TELEGRAM_BOT_TOKEN=your_telegram_token
TELEGRAM_CHAT_ID=your_chat_id

# 交易設定
TRADING_MODE=paper  # monitor | paper | live
MAX_DAILY_EXPOSURE=500
MAX_SINGLE_BET=50
NODE_ROLE=brain     # brain | executor (手機端設為 executor)
```

---

## 13. 開發里程碑與工時估算 (優化版)

> **估算基準**: 以下工時基於「1 位具備量化/區塊鏈開發經驗的資深工程師」之全職投入所作的敏捷式 Sprint 拆分。  
> **總計預估**: 約 240 小時（約 1.5 個月單人全職開發，不含觀察期）。

### Sprint 1: 基礎設施與數據匯流 (預估: 40 小時 / 5天)
- [ ] **環境與架構建置 (8h)**：Poetry 環境、Docker Compose (PG+Redis)、Loguru 日誌。
- [ ] **資料庫 Schema 設計 (8h)**：SQLAlchemy 2.0 異步模型設計與 Alembic 遷移腳本。
- [ ] **Polymarket 市場掃描 (12h)**：串接 Gamma API 解析活躍天氣市場，實作 Redis 快取機制以避免 Rate Limit。
- [ ] **天氣 API 整合 (12h)**：實作 NOAA, OpenWeatherMap 的非同步請求與重試機制 (httpx)，建立城市資料字典。

### Sprint 2: 核心 AI 引擎與機率分析 (預估: 48 小時 / 6天)
- [ ] **分析管線架構設計 (8h)**：正規化天氣數據輸入轉換，與 Polymarket 市場盤口參數統一。
- [ ] **AI 結構化輸出實作 (16h)**：結合 `anthropic` 與 `instructor`，強制 Claude 高品質回傳穩定的 JSON 決策數據。
- [ ] **套利與演算法模組 (16h)**：實作貝葉斯更新邏輯、凱利公式推薦部位、歷史準確率加權與 Edge 計算。
- [ ] **靜態回測與驗證基準 (8h)**：以過去 7 日的已知天氣與盤口，驗證評分機制的準確度。

### Sprint 3: 交易執行與強韌風控 (預估: 56 小時 / 7天)
- [ ] **Polymarket 交易整合 (16h)**：串接 `py_clob_client`，實作安全的 API Key 管理與 EIP-712 簽發機制。
- [ ] **分散式鎖與訂單狀態 (16h)**：導入 Redis Lock 確保買賣單執行絕對不重複，建立訂單追蹤狀態機。
- [ ] **嚴格風控引擎實作 (16h)**：實作 8.2 提及的模組（含停損停利％數、最大日賠付額、同市場曝險上限）。
- [ ] **循環調度與排程 (8h)**：結合 Asyncio 調度掃描與即將結算自動平倉的事件管理。

### Sprint 4: 監控、視覺化與部署實裝 (預估: 48 小時 / 6天)
- [ ] **即時通知與雙向 Bot (16h)**：Telegram Bot 建置（支援傳送截圖、接收持倉回報與「手動急停」指令）。
- [ ] **Streamlit 數據儀表板 (16h)**：取代耗時的傳統前端，快速視覺化 PnL 報表、各策略勝率、及 AI 推理日誌供追蹤。
- [ ] **容器化部署與 CI/CD (8h)**：撰寫 Production Dockerfile，整合 GitHub Actions 做基礎 Lint/Test。
- [ ] **Paper Trading 系統架設 (8h)**：實作「模擬交易」引擎，銜接真實市場報價但虛擬記帳。

### Sprint 5: 測試、實盤與營運調配 (預估: 48 小時 / 6天 + 後續觀察)
- [ ] **單元與極限壓力測試 (16h)**：針對 API 異常斷線、AI 幻覺邊界、超額下單防衛做 Mock Test。
- [ ] **Paper Trading 觀察期 (日常維運, 為期 2-4 週)**：依據模擬盤報表校準 AI Prompt 與凱利公式保守度。
- [ ] **實盤極小額驗證 (16h)**：打通 Polygon USDC 金流與 Gas，以極細微注碼 (< $2) 走完開平倉全流程。
- [ ] **合規與安全清查 (16h)**：日誌敏感資訊遮蔽檢閱、API Rate Limit 調校、交接文件與運作 SLA 訂定。

---

## 14. 風險評估

### 14.1 技術風險

| 風險 | 影響 | 緩解措施 |
|------|------|----------|
| API 速率限制 | 無法即時取得數據 | Redis 快取 + 多 API 源備援 + httpx 重試 |
| WebSocket 斷線 | 錯過盤口變動 | 自動重連 + 心跳檢測 + Telegram 斷線通知 |
| 網路中斷 | 交易失敗/延遲 | 多節點備援 (Docker+手機) + 指數退避重試 |
| 預報不準確 | 下注方向錯誤 | 多來源交叉驗證 + 保守凱利比例 |
| 鏈上交易失敗 | 訂單無法執行 | Gas 價格監控 + Polygon PoS 低 Gas |
| Redis 單點故障 | 全系統停擺 | Redis Sentinel / 快速重啟 + 倉位凍結 |
| AI 幻覺輸出 | 錯誤交易決策 | instructor 強制 Pydantic Schema + 本地統計模型交叉驗證 |

### 14.2 市場風險

| 風險 | 影響 | 緩解措施 |
|------|------|----------|
| 流動性不足 | 無法按目標價成交 | 限價單 + 流動性篩選 |
| 市場操縱 | 價格異常波動 | 異常偵測 + 暫停機制 |
| 競爭加劇 | 套利空間縮小 | 策略多元化 + 速度優化 (uvloop) |
| 極端天氣事件 | 預報大幅偏差 | 停損機制 + 倉位限制 |
| 重複下單 | 資金曝險過大 | Redis 分散式鎖 + 單一市場倉位上限 |

### 14.3 合規風險

> [!CAUTION]
> Polymarket 的合規狀態因地區而異。在使用前請確認您所在地區的法律法規。
> 自動化交易涉及金融風險，請僅使用您能承受損失的資金。

---

## User Review Required

> [!IMPORTANT]
> **在開始實作之前，需要您確認以下事項：**
> 
> 1. **Polymarket API Key** — 是否已有 Polymarket 帳戶和 API credentials？  
>    （Private Key、API Key、Secret、Passphrase）
> 
> 2. **Claude API Key** — 是否已有 Anthropic API Key？（主要分析引擎）
> 
> 3. **天氣 API** — 是否需要申請 OpenWeatherMap API Key？（NOAA 和 Open-Meteo 免費）
> 
> 4. **Telegram Bot** — 是否已有 Bot Token？（用於雙向通知與控制）
> 
> 5. **初始資金** — 預計投入多少 USDC？（影響風控參數，建議 Paper Trading 先行）
> 
> 6. **重點城市** — 優先追蹤哪些城市的天氣市場？
> 
> 7. **執行環境** — 您的 Docker/OpenClaw 環境規格？手機端是 Android (Termux) 還是 iOS？
> 
> 8. **開發優先順序** — 建議順序：  
>    Sprint 1 (基礎設施) → Sprint 2 (AI) → Sprint 3 (交易) → Sprint 4 (監控) → Sprint 5 (實盤)

---

## Verification Plan

### 自動化測試
```bash
# 單元測試 (包含 Redis Lock / uvloop / orjson)
pytest tests/ -v

# 特定模組
pytest tests/test_scanner.py -v       # 市場掃描 + WebSocket
pytest tests/test_analyzer.py -v      # AI + instructor
pytest tests/test_infra.py -v         # Redis Lock + 事件迴圈

# 整合測試（使用模擬 API）
pytest tests/integration/ -v --mock-api
```

### 手動驗證
1. **監控模式** — `python main.py --mode monitor`，確認 WebSocket 訂閱盤口並能通過 Redis Pub/Sub 派發
2. **紙上交易** — `python main.py --mode paper`，確認模擬交易邏輯正確且 Redis Lock 防重複有效
3. **多節點測試** — 同時啟動 Docker 執行器與手機節點，確認只有一個節點成功搶鎖下單
4. **Telegram Bot** — 確認推播通知 + `/stop` `/status` 雙向指令正常
5. **Streamlit 儀表板** — 確認 `http://localhost:8501` 能正確顯示 PnL 與策略數據

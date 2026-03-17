# Poly-AutoBet

Polymarket 天氣市場自動投注系統。當天氣預報機率高於市場價格 5% 以上時，自動執行套利交易。

## 功能特點

- **市場掃描**: 自動爬取 Polymarket 天氣市場
- **天氣數據**: 整合 NOAA / OpenWeatherMap / Open-Meteo API
- **AI 分析**: 使用 LLM 比對預報與市場賠率
- **策略引擎**: 套利偵測與決策
- **自動交易**: 透過 py_clob_client 下單
- **風控系統**: 停損/停利、倉位管理
- **通知系統**: Telegram 推播
- **P&L 追蹤**: 即時損益儀表板

## 運行模式

| 模式 | 說明 |
|------|------|
| `monitor` | 只監控市場，不交易 |
| `paper` | 紙上交易，模擬執行 |
| `live` | 真實交易，用戶資金 |
| `backtest` | 回測模式 |

## 快速開始

### 1. 環境要求

- Python 3.12+
- Redis
- Docker & Docker Compose (可選)

### 2. 安裝依賴

```bash
# 使用 Poetry
poetry install

# 或使用 pip
pip install -r requirements.txt
```

### 3. 配置環境變數

```bash
cp .env.example .env
# 編輯 .env 填入你的 API Keys
```

### 4. 啟動服務

```bash
# 方式一：直接運行
python main.py --mode paper

# 方式二：Docker Compose
docker-compose up -d
```

### 5. 訪問服務

| 服務 | URL |
|------|-----|
| Dashboard | http://localhost:8501 |
| API | http://localhost:8601 |

## 配置說明

### Polymarket

| 變數 | 說明 |
|------|------|
| `POLYMARKET_PRIVATE_KEY` | 錢包私鑰 (live 模式必需) |
| `POLYMARKET_API_KEY` | Polymarket API Key |
| `POLYMARKET_API_SECRET` | Polymarket API Secret |

### 天氣 API

| 變數 | 說明 |
|------|------|
| `OPENWEATHERMAP_API_KEY` | OpenWeatherMap API Key |
| `NOAA_USER_AGENT` | NOAA 請求識別 |

### AI 分析

| 變數 | 說明 |
|------|------|
| `AI_PROVIDER` | AI 供應商 (minimax/openai/deepseek/kimi/qwen/glm/gemini) |
| `AI_MODEL` | 模型名稱 (留空使用預設) |
| `MINIMAX_API_KEY` | MiniMax M2.5 API Key |
| `OPENAI_API_KEY` | OpenAI API Key |

### 交易設置

| 變數 | 預設值 | 說明 |
|------|--------|------|
| `TRADING_MODE` | paper | 運行模式 |
| `MAX_DAILY_EXPOSURE` | 500 | 每日最大投入 ($) |
| `MAX_SINGLE_BET` | 50 | 單筆最大投注 ($) |
| `MIN_EDGE` | 0.05 | 最小套利邊緣 (5%) |
| `LIVE_BANKROLL` | 1000 | 實盤資金 ($) |

### 通知

| 變數 | 說明 |
|------|------|
| `TELEGRAM_BOT_TOKEN` | Telegram Bot Token |
| `TELEGRAM_CHAT_ID` | 接收通知的 Chat ID |
| `TELEGRAM_WEBHOOK_BASE_URL` | Webhook URL (可選) |

## 架構

```
poly-autobet/
├── api/              # FastAPI 伺服器
├── config/           # 配置管理
├── core/             # 核心邏輯
│   ├── scanner.py        # 市場掃描
│   ├── weather_collector.py  # 天氣數據
│   ├── ai_analyzer.py   # AI 分析
│   ├── trade_executor.py    # 交易執行
│   └── risk_manager.py  # 風控
├── data/             # 數據庫模型
├── dashboard/        # Streamlit 儀表板
├── infra/            # 基礎設施 (Redis, WebSocket)
└── notifications/    # 通知系統
```

## 風險控制

- 單筆最大投注: $50
- 每日最大投入: $500
- 最小套利邊緣: 5%
- 停損: 20%
- 停利: 15% (scalping 模式)

## 許可證

MIT License

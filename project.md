# POLY DREAM: 全自動氣象市場交易系統

## 1. 專案目的 (Project Purpose)
POLY DREAM 是一個專門針對 **Polymarket 氣象預測市場** 設計的自動化交易系統。它結合了即時天氣數據、AI 深度解析與精準的風險管理，旨在透過自動化掃描、分析與執行交易，在高度波動的市場中捕捉套利機會與價值偏差。

## 2. 核心架構 (System Architecture)
系統採用模組化設計，各組件透過異步 (Asyncio) 協同運作：
- **Orchestrator (`main.py`)**: 負責啟動循環掃描、監聽價格更新與協調各組件。
- **Scanner (`core/scanner.py`)**: 負責從 Polymarket CLOB 與數據源擷取市場列表。
- **AI Analyzer (`core/ai_analyzer.py`)**: 整合 MiniMax/OpenAI 模型，對天氣趨勢與市場報價進行對比分析，給出買賣信號與信心度。
- **Trade Executor (`core/trade_executor.py`)**: 透過 `py_clob_client` 執行單子，支援全自動 (Auto) 與半自動 (Semi-Auto) 模式。
- **Risk Manager (`core/risk_manager.py`)**: 執行資金管理、持倉上限與**城市密度檢查**。
- **Position Manager (`core/position_manager.py`)**: 監控主動持倉，執行**剝頭皮 (Scalping)** 止盈止損回補。
- **Notification Server (`api/`)**: 基於 FastAPI，接收來自 Telegram 的 Webhook 回調進行人工確認。
- **Dashboard (`dashboard/`)**: 基於 Streamlit 的數據終端，顯示即時收益、AI 信號與市場分佈。

## 3. 技術棧 (Tech Stack)
- **語言**: Python 3.12 (Asyncio)
- **通訊**: Redis (Pub/Sub & Distributed Lock)
- **數據存儲**: SQLite (aiosqlite) / SQLAlchemy
- **Web 框架**: FastAPI (API) / Streamlit (Dashboard)
- **API 整合**: `py_clob_client` (Polymarket), `httpx` (Weather API/AI)
- **日誌與監控**: Loguru
- **部署**: Docker / Docker Compose
- **網路通訊**: Cloudflare Tunnel (Webhook 穿透)

## 4. Docker 服務說明
- **`redis`**: 核心數據中轉站，處理異步信號傳遞。
- **`app` (poly-autobet)**: 交易大腦，負責掃描與執行。
- **`api` (poly-autobet-api)**: Webhook 接收器，與 Telegram Bot 通訊。
- **`streamlit` (poly-autobet-dashboard)**: 前端視覺化終端。

## 5. 整合亮點與痛點解決

### 🌐 Cloudflare & Telegram
- **問題**: 本地開發環境無法直接接收 Telegram Webhook 的 HTTPS POST。
- **解決**: 使用 Cloudflare Tunnel (cloudflared) 將 `https://telegram-webhook.otter-labs.website` 安全映射至容器 `api:8601`。
- **優化**: 修復了 Secret Token 驗證機制，並解決了 502 Bad Gateway (主機名稱不匹配) 的網路配置問題。

### 📊 Polymarket & City Risk
- **特性**: 氣象市場多按城市分類（如 City: New York, Atlanta）。
- **問題**: 傳統風險管理未考慮地域密度，可能導致單一城市過度暴露。
- **解決**: 在 `RiskManager` 中實作了 `_check_city_limit`，確保同一城市的活躍持倉不超過預設上限（預設 3 筆）。

### 🛠️ 遇到問題與修復方案 (Issue Resolution)

| 類別 | 遇到的問題 | 修復方案 |
| :--- | :--- | :--- |
| **穩定性** | Redis 連線失敗導致系統崩潰 | 優化 `RedisClient` 加入重連機制與本地 In-memory 降級處理。 |
| **安全性** | Webhook 負載處理可能引發 KeyError | 實作嚴格的類型檢查與 Pydantic 數據校驗。 |
| **邏輯** | Settings 重載無效 | 新增 `reload_settings()` 函數，確保動態模式切換能即時生效。 |
| **基礎設施** | 缺少 `close_db()` 定義 | 完善數據庫連接池關閉邏輯，實現優雅退出 (Graceful Shutdown)。 |
| **功能** | Live 訂單狀態斷裂 | 實作背景追蹤任務 (Background Poller)，同步鏈上成交狀態至資料庫。 |
| **啟動** | 缺少 API Key 時隱形失敗 | 加入 `.env` 啟動自動校驗機制與系統健康檢查端點 (`/health`)。 |

## 6. 當前狀態
- ✅ **全自動交易模式** 已啟用。
- ✅ **GitHub 備份** 已完成 [fengwei77/poly-autobet](https://github.com/fengwei77/poly-autobet)。
- ✅ **系統監控** 已透過 Streamlit 實時輸出。

# 🌤️ POLY DREAM 系統核心說明與作業手冊 (v2.1)

本手冊旨在說明 Poly-AutoBet 自動投注系統的架構、投資判斷邏輯以及參數調整方式，協助您掌握系統運行並優化勝率。

---

## 一、 系統架構概念 (System Architecture)

系統採用 **「大腦-執行器 (Brain-Executor)」** 異步架構，確保在高併發市場行情下依然能穩定運行。

1.  **Scanner (掃描器)**: 每 15 分鐘全量掃描 Polymarket 全球天氣市場，過濾出與 8 大指標城市相關的合約。
2.  **Weather Collector (天氣採集)**: 同時抓取 NOAA (美國)、OpenWeatherMap (全球) 與 Open-Meteo (歐洲) 三方數據進行交叉驗證。
3.  **AI Strategy Engine (策略大腦)**: 這是系統的核心，負責執行**統計模型**與 **LLM (AI) 深度分析**的雙重驗證。
4.  **Trade Executor (執行器)**: 負責 Redis 分布式鎖控制（防止重複下單）與 Polymarket CLOB 協議的訂單送出。
5.  **Dashboard (儀表板)**: 提供視覺化的損益 (PnL) 監控、AI 推理日誌與實時盤口追蹤。

---

## 二、 投資判斷邏輯 (Investment Logic)

系統不依賴單一指標，而是採用 **「混合信號模型 (Hybrid Signal Model)」**：

### 1. 統計模型 (第一層過濾)
系統會計算天氣預報的 **「期望概率 (Expected Probability)」**。
*   **溫度市場**: 使用「常態分佈 (Normal Distribution)」模型。若預報為 30°C，系統會根據過往誤差 (σ) 計算出「高於 25°C」的數學概率。
*   **套利空間 (Edge)**: `Edge = 預報概率 - 市場價格`。
    *   例如：統計模型算出降雨率 80%，但市場 Yes 價格僅 0.6 (60%)，則產生 **20% 的 Edge**。

### 2. AI 深度分析 (第二層驗證)
當統計模型發現 Edge > 3% (模擬盤為 1%) 時，會召喚 AI (如 Gemini 1.5 Pro) 進行推理：
*   **上下文感知**: AI 會考慮統計模型忽略的細節，如「季節趨勢」、「近期天氣異常」或「Polymarket 交易量異常」。
*   **信心度評分**: 若 AI 給出的信心度 (Confidence) 低於設定值，系統將放棄交易。

---

## 三、 勝率掌控與風險管理 (Risk Management)

### 1. 凱利準則 (Kelly Criterion)
系統不是固定金額投注，而是根據 **Edge** 大小自動縮放注碼：
*   公式：`投注比例 = (期望概率 * 賠率 - 失敗概率) / 賠率`
*   **作用**: 確保在勝率高、利潤空間大的機會下重倉，在不確定性高的機會下輕倉，從數學上實現總資產增長。

### 2. 快進快出策略 (Scalping)
針對高波動市場，系統內建自動翻轉邏輯：
*   **15% 停利 (Take Profit)**: 當市場價格上漲達到成本的 15% 時，系統會自動平倉獲利了結，避免回撤。
*   **10% 停損 (Stop Loss)**: 當預測錯誤且價格下跌 10% 時，果斷止損，保護本金。

### 3. 硬性防護牆
透過 [.env](file:///d:/Docker_Site/poly-autobet/.env) 內的參數，您可以嚴格控制風險：
*   `MAX_DAILY_EXPOSURE`: 每日總投注額上限（預設 $500）。
*   `MAX_SINGLE_BET`: 單筆最大注碼（預設 $50）。
*   `MIN_EDGE`: 至少要有幾 % 的利潤空間才出手。

---

## 四、 調整方式 (Adjustment Guide)

所有操作都可以透過修改根目錄下的 [.env](file:///d:/Docker_Site/poly-autobet/.env) 文件完成：

### 1. 切換交易模式
*   `TRADING_MODE=paper` (模擬盤：使用真實數據，不花真錢)
*   `TRADING_MODE=live` (實盤：使用私鑰進行真實交易)

### 2. 調整獲利野心
*   如果您希望機器人更頻繁出手：
    *   調低 `MIN_EDGE` (例如: 0.03 -> 0.01)
    *   調低 `CONFIDENCE_THRESHOLD` (例如: 70 -> 50)
*   如果您希望追求更高勝率（更穩健）：
    *   調高 `MIN_EDGE` (例如: 0.05)
    *   調高 `CONFIDENCE_THRESHOLD` (例如: 80)

### 3. 變更 AI 大腦
*   `AI_PROVIDER=gemini` / `deepseek` / `gpt`
*   建議：實盤建議使用 `gpt-4o` 或 `gemini-2.0-pro`，模擬期可使用 `glm-4-flash` 以節省 API 成本。

---

## 五、 維護與監控 (Maintenance)

*   **啟動指令**: `docker-compose up -d --build` (建議在 Docker 環境運行，最穩定)
*   **查看日誌**: `docker logs -f poly-autobet`
*   **數據導出**: 系統數據儲存在 [/data/polybet.db](file:///d:/Docker_Site/poly-autobet/data/polybet.db) (SQLite)，可使用任何 SQL 工具讀取。

---
> [!TIP]
> **勝率建議**: 初次運行建議維持 `PAPER` 模式 48 小時，觀察 AI 的 `reasoning` (理由) 是否符合邏輯。若發現連錯，請先調高 `MIN_EDGE` 門檻。

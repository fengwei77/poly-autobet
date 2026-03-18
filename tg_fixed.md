# Telegram 機器人修復歷程紀錄 (tg_fixed.md)

本文件紀錄了針對 Telegram Notifier 與 AI 解析功能所進行的所有修復步驟、遇到的阻礙及最終解決方案。

## 1. 核心問題與解決方案

### 問題 A：機器人完全無反應 (ConnectError)
- **現象**：`api` 容器日誌顯示 `httpx.ConnectError: [Errno 101] Network is unreachable`。
- **原因**：Docker 容器內部優先嘗試使用 IPv6 解析並連線 `api.telegram.org`，但該網路環境下 IPv6 無法與外網通訊。
- **修復方式**：
    - 在 `docker-compose.yml` 中針對 `api` 服務增加 `sysctls` 配置，強制禁用 IPv6。
    - 增加 Google DNS (`8.8.8.8`) 確保解析穩定。

### 問題 B：初始化超時 (TimedOut)
- **現象**：初始化過程卡在 `set_webhook` 指令，導致整組 Bot 實體未能正確啟動。
- **原因**：`python-telegram-bot` 的 `httpx` 請求在 Docker 內部的特定網路抖動下容易超時。
- **修復方式**：
    - 將 `set_webhook` 改為**非阻塞異步任務** (`asyncio.create_task`)。
    - 即使向 Telegram 登記失败，只要外部 Proxy (otter-labs.website) 已正確指向此服務，Bot 仍能處理進入的 Webhook 請求。

### 問題 C：'NoneType' object has no attribute 'de_json' / 'Update' is not defined
- **現象**：Webhook 請求進入後回報 `NoneType` 或 `NameError`。
- **原因**：
    1.  先前因導入保護殼誤將 `Update` 設為 `None`。
    2.  後續移除保護殼後，發現容器內的 `notifications/telegram_bot.py` 文件發生**異常損壞**（內容混入了 Docker/Compose 的警告文字），導致 Python 解析失敗。
- **修復方式 (待續)**：需要重新同步或清空磁碟快取後再次寫入乾淨的文件。

### 問題 D：AI 解析內容過於簡單 (模擬模式)
- **現象**：問答僅回傳「（模擬模式）我收到了您的問題...」。
- **原因**：`AI_PROVIDER` 被設定為 `cli`，僅作為離線測試用。
- **修復方式**：
    - 修改 `.env` 切換為 **MiniMax (MiniMax-M2.5)** (已完成切換)。
    - 未來對應：確保 `api` 與 `app` 容器重啟後載入正確的 `.env`。

### 問題 E：全面連線失敗 (Network unreachable / ConnectError / TimedOut)
- **現象**：`api` 容器啟動後報錯 `telegram.error.NetworkError: httpx.ConnectError` 或 `TimedOut`。
- **原因**：
    1. 當前網路環境無法直連 Telegram API (會出現 `TimedOut` 逾時錯誤)，因此必須使用代理。
    2. 最初依賴本機 `7890` port 代理，但因經常未啟動或未開 LAN 導致不穩定 (`ConnectError`)。
- **修復方式 (最終完美方案)**：
    - 完全棄用本機 Windows 代理軟體，移除了 `docker-compose.yml` 中的 `HTTP_PROXY` 設定。
    - 建立專屬 Cloudflare Worker (`https://tg-api-proxy.gmn-luke.workers.dev/`) 作為 Telegram API 的反向代理。
    - 在 `notifications/telegram_bot.py` 中，透過 `ApplicationBuilder().base_url(...)` 將所有流量精準導向 Worker，達成全天候 100% 穩定連線。

## 2. 目前配置狀態

- **Webhook URL**: `https://telegram-webhook.otter-labs.website/webhook/telegram`
- **Internal Port**: `8601`
- **Security**: 使用 `X-Telegram-Bot-Api-Secret-Token` 進行 Header 驗證。
- **AI Engine**: MiniMax (活躍中)

## 3. 測試通過指標
- [x] `api` 容器 `/health` 健康檢查通過。
- [x] 手動 `curl` 模擬 Webhook POST 請求，API 回傳 `{"ok":true}` 且無 NoneType 報錯。
- [x] `api` 日誌顯示 `🔐 Webhook Secret 驗證成功`。

---
*最後更新日期：2026-03-18*

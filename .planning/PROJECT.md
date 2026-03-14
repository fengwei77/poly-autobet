# Polymarket 天氣市場自動投注系統

## What This Is

全自動化 Polymarket 天氣預測市場投注系統，透過 AI 分析官方天氣預報與市場價格的套利機會，自動執行交易。

## Core Value

當天氣預報機率高於市場價格 5% 以上時，自動下注獲利。

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] 市場掃描器 — 自動爬取 Polymarket 天氣市場
- [ ] 天氣數據整合 — 整合 NOAA/OpenWeatherMap API
- [ ] AI 分析引擎 — 使用 LLM 比對預報與市場賠率
- [ ] 策略引擎 — 套利偵測與決策
- [ ] 自動交易 — 透過 py_clob_client 下單
- [ ] 風控系統 — 停損/停利、倉位管理
- [ ] 通知系統 — Telegram/Discord 推播
- [ ] P&L 追蹤 — 損益儀表板

### Out of Scope

- 行動 App — Web 儀表板已足夠
- 即時聊天功能 — 通知系統已覆蓋
- OAuth 登入 — 錢包 Private Key 直接認證

## Context

- **基礎框架**: OpenClaw + Python + AI 分析
- **目標平台**: Polymarket（415+ 活躍天氣市場）
- **技術棧**: Python 3.11+, py_clob_client, Claude API, FastAPI, SQLite

## Constraints

- **資金限制**: 單筆最大 $50，每日最大 $500 — 避免過度曝險
- **運行模式**: 支援 monitor/paper/live 三種模式切換
- **API 限制**: Polymarket CLOB API 有頻率限制，需實作重試機制

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| 紙上交易優先上線 | 驗證策略有效性前不投入真實資金 | — Pending |
| Claude 作為主要 AI 模型 | 成本效益較佳，分析品質足夠 | — Pending |
| Open-Meteo 作為備用天氣 API | 完全免費，無需 API Key | — Pending |

---
*Last updated: 2026-03-15 after initialization*

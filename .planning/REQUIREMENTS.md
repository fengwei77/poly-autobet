# Requirements: Polymarket Weather Betting Bot

**Defined:** 2026-03-15
**Core Value:** 當天氣預報機率高於市場價格 5% 以上時，自動下注獲利

## v1 Requirements

### Infrastructure

- [ ] **INF-01**: 專案初始化與依賴管理 (requirements.txt)
- [ ] **INF-02**: 配置管理系統 (環境變數、API Keys)
- [ ] **INF-03**: SQLite 資料庫模型設計
- [ ] **INF-04**: 日誌系統 (loguru)

### Data Collection

- [ ] **DATA-01**: Polymarket Gamma API 整合 (市場發現、價格查詢)
- [ ] **DATA-02**: Polymarket CLOB API 客戶端初始化
- [ ] **DATA-03**: Open-Meteo 天氣 API 整合
- [ ] **DATA-04**: NOAA 天氣 API 整合
- [ ] **DATA-05**: 市場掃描器 (天氣市場過濾)
- [ ] **DATA-06**: 價格追蹤與歷史數據儲存

### Analysis

- [ ] **ANAL-01**: 天氣預報機率計算
- [ ] **ANAL-02**: 市場 vs 預報偏差計算
- [ ] **ANAL-03**: Claude API 整合 (AI 分析)
- [ ] **ANAL-04**: 套利偵測邏輯 (5% 門檻)
- [ ] **ANAL-05**: 信心度評分系統 (0-100)

### Execution

- [ ] **EXEC-01**: 交易執行器 (py_clob_client)
- [ ] **EXEC-02**: 限價單/市價單邏輯
- [ ] **EXEC-03**: 倉位管理器
- [ ] **EXEC-04**: 風控規則引擎 (停損/停利)
- [ ] **EXEC-05**: 每日限額檢查
- [ ] **EXEC-06**: 紙上交易模式 (paper mode)
- [ ] **EXEC-07**: 三種運行模式 (monitor/paper/live)

### Operations

- [ ] **OPS-01**: Telegram 通知 Bot
- [ ] **OPS-02**: Discord Webhook 通知
- [ ] **OPS-03**: 交易通知模板
- [ ] **OPS-04**: P&L 追蹤系統
- [ ] **OPS-05**: 每日損益報告
- [ ] **OPS-06**: FastAPI Web 儀表板

## v2 Requirements

### Advanced Features

- **ADV-01**: OpenWeatherMap API 備用
- **ADV-02**: WebSocket 實時價格更新
- **ADV-03**: 歷史回測引擎
- **ADV-04**: 多策略引擎 (動量/均值回歸)
- **ADV-05**: 自動化倉位展期

### Scale

- **SCL-01**: 多錢包支持
- **SCL-02**: 分散式部署 (Celery)
- **SCL-03**: Redis 快取層

## Out of Scope

| Feature | Reason |
|---------|--------|
| 行動 App | Web 儀表板已足夠監控 |
| OAuth 登入 | 錢包 Private Key 認證已足夠 |
| 即時聊天 | 通知系統已覆蓋 |
| 槓桿交易 | 增加風險，MVP 暫不需要 |
| 跨交易所套利 | 專注 Polymarket 單一市場 |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| INF-01 | Phase 1 | Pending |
| INF-02 | Phase 1 | Pending |
| INF-03 | Phase 1 | Pending |
| INF-04 | Phase 1 | Pending |
| DATA-01 | Phase 2 | Pending |
| DATA-02 | Phase 2 | Pending |
| DATA-03 | Phase 2 | Pending |
| DATA-04 | Phase 2 | Pending |
| DATA-05 | Phase 2 | Pending |
| DATA-06 | Phase 2 | Pending |
| ANAL-01 | Phase 3 | Pending |
| ANAL-02 | Phase 3 | Pending |
| ANAL-03 | Phase 3 | Pending |
| ANAL-04 | Phase 3 | Pending |
| ANAL-05 | Phase 3 | Pending |
| EXEC-01 | Phase 4 | Pending |
| EXEC-02 | Phase 4 | Pending |
| EXEC-03 | Phase 4 | Pending |
| EXEC-04 | Phase 4 | Pending |
| EXEC-05 | Phase 4 | Pending |
| EXEC-06 | Phase 4 | Pending |
| EXEC-07 | Phase 4 | Pending |
| OPS-01 | Phase 5 | Pending |
| OPS-02 | Phase 5 | Pending |
| OPS-03 | Phase 5 | Pending |
| OPS-04 | Phase 5 | Pending |
| OPS-05 | Phase 5 | Pending |
| OPS-06 | Phase 5 | Pending |

**Coverage:**
- v1 requirements: 27 total
- Mapped to phases: 27
- Unmapped: 0 ✓

---
*Requirements defined: 2026-03-15*
*Last updated: 2026-03-15 after research synthesis*

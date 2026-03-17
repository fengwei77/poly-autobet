# Poly-AutoBet 問題修復清單

> 建立日期: 2026-03-17

---

## 修復順序總覽

```
【第1批 - Critical 立即修復】
  1 → 2 → 3 → 4

【第2批 - High Priority 邏輯修正】
  5 → 6 → 7 → 8 → 9 → 10

【第3批 - Medium Priority 功能補全】
  11 → 12 → 13 → 14

【第4批 - Low Priority 優化】
  15 → 16 → 17 → 18 → 19 → 20
```

---

## 🔴 Critical - 會導致運行時錯誤

### #1 main.py:126 - 訊息類型未檢查
**問題**: 直接用 `message["data"]`，若訊息類型不是 message 會 KeyError
**位置**: `main.py:126`
```python
# 當前問題代碼
result = json_loads(message["data"])
```
**修復方向**: 先檢查 `message.get("type")` 或使用 `message.get("data")` 並處理 None

---

### #2 main.py:329 - 設定重載方式錯誤
**問題**: `settings.__init__()` 不會正確重新載入 .env，應使用 `Settings()` 重建實例
**位置**: `main.py:329`
```python
# 當前問題代碼
def reload_settings():
    global settings
    settings = Settings()  # 會重複執行 __init__，但 pydantic 不會重新讀取 .env
```
**修復方向**: 清除 env 緩存後重建 Settings

---

### #3 telegram_bot.py:43 - Webhook URL 寫死
**問題**: WEBHOOK_BASE_URL 寫死為 `https://telegram-webhook.otter-labs.website`，應該從 settings 讀取
**位置**: `notifications/telegram_bot.py:43-45`
```python
# 當前問題代碼
WEBHOOK_BASE_URL = "https://telegram-webhook.otter-labs.website"
```
**修復方向**: 從 `settings.telegram_webhook_url` 或環境變數讀取

---

### #4 risk_manager.py:144 - city_limit 是空殼
**問題**: `_check_city_limit` 直接返回 True，沒有實際檢查城市數量限制
**位置**: `core/risk_manager.py:143-144`
```python
# 當前問題代碼
def _check_city_limit(self) -> bool:
    return True  # 空殼，永遠通過
```
**修復方向**: 實作實際的城市數量限制檢查

---

## 🟠 High Priority - 邏輯錯誤或數據問題

### #5 trade_executor.py:179 - 缺少訂單成交確認
**問題**: Live 交易只記錄 pending，沒有檢查訂單是否真的成交
**位置**: `core/trade_executor.py:179-241`
**修復方向**: 添加 order status tracking 迴圈，輪詢訂單狀態直到成交/失敗

---

### #6 trade_executor.py:58 - 半自動模式條件錯誤
**問題**: 比較字串用 `== "semi-auto"`，但 `settings.trading_strategy` 是 TradingMode enum
**位置**: `core/trade_executor.py:58`
```python
# 當前問題代碼
if settings.trading_strategy == "semi-auto":
```
**修復方向**: 改用 `settings.trading_strategy == TradingStrategy.SEMI_AUTO`

---

### #7 risk_manager.py:109 - live 模式 nav 寫死
**問題**: `_get_total_nav()` 在 live 模式返回固定 1000.0，應該從錢包餘額查詢
**位置**: `core/risk_manager.py:109`
```python
# 當前問題代碼
return 1000.0  # 寫死
```
**修復方向**: 從 web3/錢包餘額查詢實際資產

---

### #8 redis_client.py:48 - Redis 失敗時默默 fallback
**問題**: 沒有發出錯誤警告，生產環境可能導致資料丟失
**位置**: `infra/redis_client.py:48-49`
**修復方向**: 添加 warning log，區分 cache 和 pub/sub 失敗

---

### #9 main.py:302 - 異常處理太廣泛
**問題**: `except: pass` 吞掉所有錯誤，應該記錄日誌
**位置**: `main.py:302-313`
```python
# 當前問題代碼
try:
    ...
except: pass
```
**修復方向**: 改用具體異常類型並記錄日誌

---

### #10 main.py:247 - Settings.validate() 缺失
**問題**: 調用 `settings.validate()`，但 Settings 類沒有這個方法，會導致 AttributeError
**位置**: `main.py:247`
```python
# 當前問題代碼
missing = settings.validate()
```
**修復方向**: 在 Settings 類中添加 validate() 方法，或移除此調用

---

## 🟡 Medium Priority - 功能不完整

### #11 config/settings.py - 缺少啟動參數驗證
**問題**: 無 API keys、private key 驗證機制
**修復方向**: 添加 `validate()` 方法檢查必要參數

---

### #12 ai_analyzer.py:193 - trigger_threshold 寫死
**問題**: paper 模式用 0.01，live 用 0.03，應從 settings 讀取
**位置**: `core/ai_analyzer.py:193`
**修復方向**: 從 settings 讀取配置

---

### #13 core/__init__.py - 導出不完整
**問題**: 缺少導出 position_manager, strategy_engine, city_resolver
**位置**: `core/__init__.py`
```python
# 當前導出
from core.scanner import MarketScanner, scanner
from core.weather_collector import WeatherCollector, weather_collector
from core.ai_analyzer import AIAnalyzer, ai_analyzer
from core.risk_manager import RiskManager, risk_manager
from core.trade_executor import TradeExecutor, trade_executor

# 缺少
from core.position_manager import PositionManager, position_manager
from core.strategy_engine import StrategyEngine, strategy_engine
from core.city_resolver import CityResolver, city_resolver
```

---

### #14 tests/ - 測試覆蓋不足
**問題**: 缺少 scanner, weather_collector, ai_analyzer 測試
**現有測試**:
- ✅ test_sprint1.py
- ✅ test_position_manager.py
- ✅ test_strategy_engine.py
- ❌ test_trade_executor.py (有失敗)

**缺失測試**:
- core/scanner.py
- core/weather_collector.py
- core/ai_analyzer.py
- core/city_resolver.py

---

## 🟢 Low Priority - 優化建議

### #15 專案根目錄 - 缺少 README.md

### #16 docker-compose.yml - 缺少 healthcheck

### #17 pyproject.toml - 缺少 poetry.lock

### #18 data/ - 缺少 Alembic 遷移腳本

### #19 Dockerfile - 依賴安裝不完整 fallback

### #20 .env.example - 缺少完整參數說明

---

## 測試失敗記錄 (err.txt)

| 測試 | 問題 |
|------|------|
| test_exceeding_max_exposure_rejected | risk_manager 沒有 settings 屬性 |
| test_live_execution_token_mapping | py_clob_client 模組未安裝 |

---

## 備註

- 修復時請參考 `err.txt` 和 `test_log*.txt` 了解具體錯誤
- 優先確保 Critical 問題不影響系統啟動
- High Priority 問題會影響交易邏輯正確性

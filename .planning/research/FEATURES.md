# Feature Landscape: Polymarket Weather Betting Automation

**Domain:** Automated prediction market trading (Polymarket)
**Researched:** 2026-03-15

## Executive Summary

This document catalogs features for an automated Polymarket weather betting system. The ecosystem relies on Polymarket's REST APIs (Gamma for markets, CLOB for trading) and Python client library (py_clob_client). Weather data comes from free APIs (Open-Meteo, OpenWeatherMap) or NOAA. Key differentiators emerge from AI-driven analysis that compares official forecast probabilities against market odds.

## Table Stakes

Features users expect. Missing = product feels incomplete.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| **Market Scanner** | Must discover active weather markets | Low | Gamma API `/markets` endpoint with weather tag filter |
| **Price Fetcher** | Get current bid/ask to calculate implied probability | Low | CLOB API `get_midpoint()`, `get_price()` methods |
| **Order Executor** | Place trades automatically | Medium | py_clob_client `create_market_order()`, `create_order()` |
| **Position Tracker** | Know current holdings and P&L | Low | Data API `get_positions()` endpoint |
| **Wallet Auth** | Connect private key for signing | Low | py_clob_client accepts EOA private key or proxy wallet |
| **Paper Trading Mode** | Test strategies without real money | Medium | Replicate all trading logic with mock execution |
| **Basic Notifications** | Alert on trades, errors | Low | Telegram/Discord webhooks |

## Differentiators

Features that set product apart. Not expected, but valued.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| **Weather Data Integration** | Source of truth for actual probabilities | Medium | Open-Meteo (free, no key), OpenWeatherMap, NOAA |
| **AI Probability Analysis** | Compare forecast vs market odds | High | Claude API for natural language analysis of forecasts |
| **Arbitrage Detection** | Find mispriced markets (forecast > odds) | High | Core value: bet when difference > threshold (e.g., 5%) |
| **Multi-Location Tracking** | Scan weather across many cities | Medium | Open-Meteo supports global coordinates |
| **Historical Backtesting** | Validate strategies on past data | High | Need historical market prices + weather data |
| **Risk Management** | Position sizing, stop loss, daily limits | Medium | Enforce per-trade max ($50) and daily max ($500) |
| **Dynamic Threshold Tuning** | Adjust betting threshold based on confidence | High | ML model to set threshold per market |
| **Real-time WebSocket Feed** | Instant price updates vs polling | Medium | Polymarket WebSocket API for market channel |
| **Strategy Portfolio** | Multiple betting strategies simultaneously | High | Different thresholds per weather type |

## Anti-Features

Features to explicitly NOT build.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| **Mobile App** | Web dashboard sufficient for monitoring | Focus on responsive web UI |
| **OAuth/Social Login** | Wallet private key authentication is standard in crypto | Keep key-based auth |
| **Real-time Chat Support** | Notification system covers alerts | Community Discord if needed |
| **Multi-wallet Support** | Adds complexity, single wallet sufficient | Single wallet, single strategy |
| **Cross-exchange Arbitrage** | Polymarket is mostly isolated | Focus on forecast-vs-odds arbitrage |
| **Leverage/Margin Trading** | Prediction markets don't support this | Stick to cash markets |
| **Social Trading/Follow** | Not relevant for automated systems | Skip feature |

## Feature Dependencies

```
Market Scanner
    ↓
Price Fetcher ← Weather Data Integration
    ↓              ↓
AI Probability Analysis ← AI Probability Analysis
    ↓
Arbitrage Detection
    ↓
Order Executor
    ↓
Position Tracker ← Risk Management
    ↓
Notifications
```

**Dependency Notes:**
- Weather data feeds AI analysis (independent of market data)
- Position tracker feeds risk management (daily limits)
- All components need access to configuration (API keys, thresholds)

## MVP Recommendation

Prioritize in this order:

1. **Market Scanner** — Find weather markets (table stakes)
2. **Price Fetcher** — Get current odds (table stakes)
3. **Weather Integration** — Pull forecast data (differentiator enabler)
4. **AI Analysis** — Compare forecast to odds (core value)
5. **Paper Trading** — Validate before risking money (risk reduction)
6. **Order Executor** — Go live (table stakes)
7. **Risk Management** — Enforce limits (survival)
8. **Notifications** — Stay informed (table stakes)

**Defer:**
- Historical backtesting (need data collection first)
- WebSocket feed (polling sufficient initially)
- Multi-strategy portfolio (single strategy first)

## Sources

- Polymarket API Documentation: https://docs.polymarket.com/
- py_clob_client (PyPI): https://pypi.org/project/py-clob-client/
- Open-Meteo API: https://open-meteo.com/en/docs
- Polymarket Gamma API endpoints: https://docs.polymarket.com/llms.txt

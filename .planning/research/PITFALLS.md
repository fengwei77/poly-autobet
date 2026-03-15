# Pitfalls Research

**Domain:** Automated Polymarket Trading (Weather Betting)
**Researched:** 2026-03-15
**Confidence:** HIGH

## Executive Summary

This document catalogs the critical pitfalls specific to automated Polymarket trading bots, particularly for weather betting automation. Based on documentation analysis and community issues, the most dangerous pitfalls involve authentication/allowance setup, API error handling, and premature live trading. Many failures stem from misunderstandings about the two-level authentication model (L1 private key + L2 API key) and token approval requirements.

## Critical Pitfalls

### Pitfall 1: Token Allowances Not Approved

**What goes wrong:**
Orders fail with "not enough balance / allowance" errors despite having correct USDC balances and approved wallet. This is the most common failure point for automated trading systems.

**Why it happens:**
- MetaMask/EOA users must manually set token allowances before trading — this is not automatic
- Both USDC and Conditional Tokens must be approved for three specific contracts
- Email/Magic wallet users have allowances set automatically, but EOA users do not
- Many developers assume approvals are automatic like centralized exchanges

**How to avoid:**
- Implement a pre-trade checklist that verifies token allowances before attempting orders
- Use the `approve_token()` method in py_clob_client for both USDC and conditional tokens
- Log allowance status in the dashboard so users can see approval state
- Add retry logic that attempts approval if the first order fails due to allowance

**Warning signs:**
- First order always fails with allowance error
- "Insufficient balance" error even with funded wallet
- Test trades work in web UI but fail via API

**Phase to address:**
- Phase 2 (Data Collection): Include allowance verification as part of the initial setup
- Phase 4 (Execution): Add pre-flight checks before any order submission

---

### Pitfall 2: Authentication Confusion (L1 vs L2)

**What goes wrong:**
401 Unauthorized errors, signature validation failures, or inability to access authenticated endpoints. The two-level authentication model confuses many developers.

**Why it happens:**
- L1 (private key) signs EIP-712 messages to prove wallet ownership
- L2 (API key/secret/passphrase) is derived from L1 for faster request signing
- Methods that create user orders still require L1 signature even with valid L2 credentials
- Proxy wallets must be deployed before L2 auth if user has never logged into Polymarket.com

**How to avoid:**
- Use SDK methods: `create_or_derive_api_creds()` to get L2 credentials
- Ensure proxy wallet is deployed (call `deploy_proxy_wallet()` if needed)
- For order creation, always sign with the private key (L1), not just L2 credentials
- Verify `POLY_ADDRESS` header matches the wallet that signed the message

**Warning signs:**
- 401 errors on trading endpoints
- `INVALID_SIGNATURE` errors
- `NONCE_ALREADY_USED` errors
- API key works for read-only but fails for trading

**Phase to address:**
- Phase 2 (Data Collection): Implement authentication wrapper with proper L1/L2 handling
- Phase 4 (Execution): Test all authenticated endpoints before going live

---

### Pitfall 3: Premature Live Trading

**What goes wrong:**
System goes live with untested strategies, resulting in real financial losses from bugs or unprofitable strategies.

**Why it happens:**
- Excitement to see "real money" working
- Paper trading被视为"慢"或"不够真实"
- Insufficient data to validate strategy profitability
- No baseline to compare performance

**How to avoid:**
- Enforce minimum 1-week paper trading with documented P&L
- Require positive expected value (EV) calculation before live trading
- Start with minimum bet sizes ($1-5) even in live mode
- Set up automated paper/live mode switch with clear criteria

**Warning signs:**
- "Let's just try it with real money" discussions
- No historical P&L data from paper mode
- Strategy hasn't been backtested or validated
- No stop-loss or daily loss limits configured

**Phase to address:**
- Phase 4 (Execution): Paper trading mode is mandatory before live
- Phase 5 (Operations): Review P&L weekly, require profitability proof before increasing bet sizes

---

### Pitfall 4: Signature Validation Failures

**What goes wrong:**
Orders fail with invalid signature errors, especially when switching between proxy wallet (signature type 2) and EOA (signature type 0).

**Why it happens:**
- Maker/taker amount semantics can be reversed between modes
- Proxy mode requires different signing logic than EOA
- Timestamp expiration not handled correctly
- Nonce reuse without proper derivation

**How to avoid:**
- Use SDK's `create_order()` method which handles signing internally
- If implementing custom signing, verify signature_type matches wallet type
- Ensure timestamps are fresh (within last 60 seconds)
- Use `deriveApiKey()` with same nonce to retrieve existing credentials instead of creating new ones

**Warning signs:**
- First trade succeeds, subsequent trades fail
- Works in EOA mode but fails with proxy wallet
- `INVALID_SIGNATURE` in logs

**Phase to address:**
- Phase 4 (Execution): Test order placement with both EOA and proxy wallet types

---

### Pitfall 5: Ignoring Market Liquidity

**What goes wrong:**
Large orders on thin markets cause significant slippage, eating into or eliminating profits. Orders may not fill at expected price.

**Why it happens:**
- Weather markets can have low liquidity, especially for niche locations
- Market orders immediately cross the spread
- No check of order book depth before placing orders

**How to avoid:**
- Check order book with `get_order_book()` before placing orders
- Limit order size to <10% of visible liquidity
- Use limit orders instead of market orders when possible
- Add slippage tolerance parameter (e.g., reject fills >5% from expected price)

**Warning signs:**
- Executed price significantly differs from quoted price
- Large positions in low-volume markets
- No order book inspection in the code

**Phase to address:**
- Phase 3 (Analysis): Add liquidity checks to signal-to-order pipeline
- Phase 4 (Execution): Implement limit orders and slippage protection

---

### Pitfall 6: No Rate Limit Handling

**What goes wrong:**
API requests fail with throttling errors, IP gets temporarily banned, lost trading opportunities during cooldown periods.

**Why it happens:**
- Polymarket CLOB API has implicit rate limits (not always documented)
- Fire API requests as fast as possible in loops
- No exponential backoff on failures

**How to avoid:**
- Implement request throttling (max N requests per second)
- Cache market and price data locally to reduce API calls
- Use circuit breaker pattern: fail fast after N consecutive failures
- Add retry logic with exponential backoff (2s, 4s, 8s, max 30s)

**Warning signs:**
- 429 Too Many Requests errors
- Connection timeouts
- Sporadic failures during high-frequency scanning

**Phase to address:**
- Phase 2 (Data Collection): Implement caching and rate limiting from the start
- Phase 4 (Execution): Add circuit breaker to order submission

---

### Pitfall 7: WebSocket Silent Freezes

**What goes wrong:**
WebSocket connections appear to succeed (server accepts connection) but never receive book data. System hangs waiting for updates.

**Why it happens:**
- Server accepts connection but doesn't send data until subscription is confirmed
- Subscription format incorrect
- Network issues drop connection without error

**How to avoid:**
- Don't rely solely on WebSocket for critical data
- Implement heartbeat/ping-pong to detect stale connections
- Fall back to REST polling if WebSocket doesn't receive data within timeout
- Log WebSocket state transitions for debugging

**Warning signs:**
- Connected but no data received after 10+ seconds
- Prices not updating in dashboard
- WebSocket logs show "subscribed" but no messages

**Phase to address:**
- Phase 2 (Data Collection): Implement WebSocket with fallback to REST polling
- Phase 5 (Operations): Add monitoring for WebSocket health

---

### Pitfall 8: Weather Data Mismatch with Market Resolution

**What goes wrong:**
Bets lose because weather data source differs from how Polymarket resolves markets. Forecast shows 80% chance but actual outcome is different.

**Why it happens:**
- Weather APIs use different measurement standards (e.g., "rain" vs "precipitation > 0.1mm")
- Location mismatch between API coordinates and market definition
- Time zone differences (forecast for 3 PM vs market resolving at midnight)
- Using probability forecasts instead of actual outcome predictions

**How to avoid:**
- Carefully map market question to weather API parameters
- Use NOAA or official sources that match market resolution criteria
- Verify location coordinates match market's defined location
- Account for time zone and forecast lead time
- Test with historical data to verify API matches resolution

**Warning signs:**
- AI analysis shows high confidence but bets consistently lose
- Different weather APIs give different probabilities for same market
- Market resolves differently than expected based on forecast

**Phase to address:**
- Phase 3 (Analysis): Validate weather data mapping before strategy implementation
- Phase 5 (Operations): Track prediction accuracy per weather source

---

### Pitfall 9: No Stop-Loss or Risk Limits

**What goes wrong:**
Positions move against the bot significantly with no exit strategy. Daily losses accumulate beyond acceptable thresholds.

**Why it happens:**
- "Hope" that positions will recover
- No automated risk checks before trading
- Missing daily loss limits

**How to avoid:**
- Implement automatic stop-loss (e.g., exit at 20% below entry price)
- Set daily loss limit (e.g., stop trading if daily loss exceeds $100)
- Add maximum position size per market
- Require risk manager approval before each trade

**Warning signs:**
- Large drawdowns in P&L
- No exit orders placed
- Risk checks commented out "for testing"

**Phase to address:**
- Phase 4 (Execution): Implement risk manager with stop-loss and daily limits
- Phase 5 (Operations): Review risk metrics daily

---

### Pitfall 10: Hardcoded Private Keys

**What goes wrong:**
Private keys committed to version control, accidentally shared, or exposed. Funds stolen.

**Why it happens:**
- Developer convenience
- "It's just a test wallet anyway"
- Forgetting .env files in git

**How to avoid:**
- Store all secrets in environment variables or .env files
- Add .env to .gitignore
- Use secrets manager for production
- Never log private keys or include in error reports
- Rotate keys regularly

**Warning signs:**
- Private key found in code search
- .env files in git history
- Keys logged in error messages

**Phase to address:**
- Phase 1 (Infrastructure): Set up proper secrets management from day one

---

### Pitfall 11: Wallet Address Mismatches

**What goes wrong:**
Trades execute via CLOB API but don't appear in the Polymarket UI. Can't verify positions.

**Why it happens:**
- Using different wallet addresses for API vs web UI
- Proxy wallet address differs from funder address
- Network/chain mismatch (wrong chain ID)

**How to avoid:**
- Verify wallet address matches between API client and web UI
- Use signature type 2 (proxy) consistently
- Ensure chain_id is 137 (Polygon mainnet)
- Log the full wallet address for debugging

**Warning signs:**
- Trades succeed (no error) but don't appear in UI
- Position tracker shows different balance than web UI
- "Wallet mismatch" errors

**Phase to address:**
- Phase 2 (Data Collection): Verify wallet address before trading
- Phase 4 (Execution): Cross-check position with web UI after each trade

---

### Pitfall 12: Closed Market Redemption Issues

**What goes wrong:**
Unable to redeem winnings from closed/resolved markets. Positions stuck, can't realize profits.

**Why it happens:**
- Redemption logic not implemented
- Trying to redeem too early before resolution is finalized
- Conditional token addresses change after market resolution

**How to avoid:**
- Implement market resolution monitoring
- Add scheduled redemption task that runs daily
- Handle case where market condition_id changes after resolution
- Test redemption on test markets first

**Warning signs:**
- Won trades but balance doesn't increase
- Market shows "Resolved" but no redemption possible
- Redemption API calls fail

**Phase to address:**
- Phase 5 (Operations): Implement automated redemption workflow
- Phase 4 (Execution): Track market resolution dates

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Skip paper trading | Faster to live | Real money losses | Never — enforce paper first |
| Hardcode API keys | Simpler setup | Security breach risk | Never |
| Disable rate limiting | Faster scans | IP ban | Never |
| Use market orders | Simpler code | Slippage losses | Only on high-liquidity markets < $10 |
| Skip order book check | Less code | Poor fill prices | Never |
| Disable stop-loss | Fewer restrictions | Unlimited losses | Never |
| Cache only in memory | Simpler code | Data loss on restart | Only for < 1 hour caches |

---

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| Polymarket CLOB | Not setting token allowances | Call `approve()` for USDC and conditional tokens before trading |
| Polymarket CLOB | Using L2 only for orders | Orders require L1 signature, use SDK's order methods |
| Polymarket CLOB | Wrong chain ID | Must use chain_id=137 (Polygon) |
| Open-Meteo | Ignoring coordinate accuracy | Use exact lat/long from market, not city center |
| Claude API | No timeout handling | Requests can hang; set 30s timeout |
| Telegram/Discord | Blocking sends | Use async webhooks to avoid blocking trading loop |

---

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| No caching | Rate limit errors | Cache market data for 60s | > 60 API calls/minute |
| Synchronous HTTP | Event loop blocked | Use aiohttp for all HTTP | Any concurrent operations |
| Large order books | Memory bloat | Limit depth to top 10 | Markets with > 1000 orders |
| Unbounded history | DB bloat | Prune trades > 90 days | After 10,000+ trades |
| No batch processing | DB contention | Batch writes every 5s | > 10 scans/second |

---

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| Private key in source code | Total fund loss | Environment variables only |
| Private key in logs | Fund theft via log exposure | Sanitize all logs |
| No IP whitelisting | Unauthorized API access | If available, restrict API key |
| No 2FA on wallet | Social engineering attacks | Use hardware wallet for main funds |
| Test wallet with real funds | Accidental loss | Keep test wallet small (< $100) |

---

## "Looks Done But Isn't" Checklist

- [ ] **Authentication:** L1 and L2 credentials both working — verify with test order
- [ ] **Token Allowances:** Both USDC and conditional tokens approved — verify before first trade
- [ ] **Paper Trading:** Has run for 1+ week with documented P&L — not just "works"
- [ ] **Risk Limits:** Stop-loss AND daily loss limit implemented — not just one
- [ ] **Liquidity Check:** Order book inspected before placing orders — not skipped
- [ ] **Rate Limiting:** Implemented and tested — not just "planned"
- [ ] **Wallet Match:** Position matches web UI — verified manually
- [ ] **Market Resolution:** Redemption workflow tested — not just implemented
- [ ] **Error Handling:** All API errors handled — not just logged and ignored
- [ ] **Secret Management:** No keys in code — verified with git grep

---

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|-----------------|
| Lost funds from hack | HIGH | Cannot recover — use hardware wallet, small test wallet |
| Stuck position (no liquidity) | MEDIUM | Wait for market resolution; redeem if won |
| Banned IP | LOW | Wait 1 hour; implement rate limiting before retry |
| Bad strategy (losing money) | MEDIUM | Switch to paper; analyze why; adjust threshold |
| Stuck redemption | MEDIUM | Check market resolution status; try different endpoint |

---

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| Token Allowances | Phase 2: Data Collection | Pre-flight check before first order |
| Authentication | Phase 2: Data Collection | Test all authenticated endpoints |
| Live Trading Premature | Phase 4: Execution | Enforce paper mode duration |
| Signature Failures | Phase 4: Execution | Test with both EOA and proxy |
| Liquidity Ignored | Phase 3: Analysis | Add order book checks |
| Rate Limits | Phase 2: Data Collection | Implement and stress test |
| WebSocket Freezes | Phase 2: Data Collection | Fallback to REST |
| Weather Mismatch | Phase 3: Analysis | Historical accuracy test |
| No Stop-Loss | Phase 4: Execution | Risk manager in pipeline |
| Hardcoded Keys | Phase 1: Infrastructure | Git grep verification |
| Wallet Mismatch | Phase 4: Execution | Cross-check with UI |
| Redemption Issues | Phase 5: Operations | Test on closed market |

---

## Sources

- [Polymarket API Documentation](https://docs.polymarket.com/api-reference/authentication) — L1/L2 authentication model, headers required
- [py-clob-client GitHub Issues](https://github.com/polymarket/py-clob-client/issues) — Common pitfalls: signature failures, allowance errors, wallet mismatches
- [Polymarket SDK Documentation](https://docs.polymarket.com/sdks/python) — Token approval requirements
- [Polymarket GitHub README](https://github.com/polymarket/py-clob-client) — Allowance warnings, signature types
- Project constraints: $50 max per trade, $500 max daily, monitor/paper/live modes

---
*Pitfalls research for: Polymarket Weather Betting Automation*
*Researched: 2026-03-15*

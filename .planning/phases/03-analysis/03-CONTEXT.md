# Phase 3: Analysis - Context

**Gathered:** 2026-03-15
**Status:** Verified - Ready for next phase

<domain>
## Phase Boundary

System generates actionable trading signals by comparing weather forecasts against market odds.

**Status:** ALREADY IMPLEMENTED and VERIFIED

</domain>

<decisions>
## Implementation Decisions

### ANAL-01: Weather Probability Calculation
- **Decision:** Statistical analysis from forecast data
- **Status:** ✓ Implemented - _statistical_analysis()

### ANAL-02: Deviation Calculation
- **Decision:** Compare forecast probability vs market price
- **Status:** ✓ Implemented - _statistical_analysis()

### ANAL-03: Claude API Integration
- **Decision:** Use anthropic SDK + instructor for structured output
- **Status:** ✓ Implemented - _ai_analysis()

### ANAL-04: Arbitrage Detection
- **Decision:** 5% edge threshold from settings
- **Status:** ✓ Implemented - returns BUY/SELL/HOLD signals

### ANAL-05: Confidence Scoring
- **Decision:** 0-100 scale based on data quality
- **Status:** ✓ Implemented - confidence field in TradeDecision

### Key Features
- **Fallback:** Statistical analysis works without API key
- **Structured output:** Pydantic model enforced by instructor
- **Kelly sizing:** Automatic position sizing

### Verification Results
- All modules import successfully
- All required methods present

</decisions>

<specifics>
## Existing Code Features

**AIAnalyzer:**
- `analyze_opportunity()` - Main entry point
- `_statistical_analysis()` - Local probability calculation
- `_ai_analysis()` - Claude API with instructor
- `_kelly_criterion()` - Kelly formula sizing
- `_merge_analysis()` - Combines stat + AI results

**TradeDecision Schema:**
```python
real_probability: float (0-1)
confidence: int (0-100)
signal: str (BUY/SELL/HOLD)
reasoning: str
risk_factors: list[str]
```

**Config Parameters:**
- min_edge: 5% (from settings)
- confidence_threshold: 70
- kelly_fraction: 0.25 (conservative)

</specifics>

<deferred>
## Deferred Ideas

None — Phase 3 Analysis is complete and verified.

</deferred>

---

*Phase: 03-analysis*
*Context gathered: 2026-03-15*

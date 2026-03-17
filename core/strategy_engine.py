"""
Core: Strategy Engine — Advanced statistical arbitrage calculations.
Calculates exact probabilities using statistical distributions (e.g. Normal Distribution)
for specific market types to provide mathematical edge before AI analysis.
"""

import math
import re
from typing import Optional, Tuple
from loguru import logger

class StrategyEngine:
    """Mathematical probability estimator for different weather markets."""
    
    def estimate_probability(self, market: dict, weather: dict) -> float:
        """
        Estimate the true objective probability of a market resolving to YES 
        based on the market's category and current weather data.
        """
        category = market.get("category", "weather")
        
        if category == "temperature":
            return self._eval_temperature_market(market, weather)
        elif category == "precipitation":
            return self._eval_precipitation_market(market, weather)
            
        # Fallback to a naive estimate
        return self._naive_estimate(market, weather)
        
    def _eval_temperature_market(self, market: dict, weather: dict) -> float:
        """
        Evaluate temperature markets.
        Uses a Normal Distribution approximation. 
        Assumes forecast High represents the Mean (μ) and sets a default Standard Deviation (σ).
        """
        question = market.get("question", "").lower()
        forecast_high = weather.get("temp_high_c")
        
        if forecast_high is None:
            return 0.5
            
        # Parse target temperature condition from question
        # E.g. "Will the high temperature be 15°C or higher?" or "> 15"
        condition, target_temp = self._parse_temperature_condition(question)
        
        if target_temp is None:
            return 0.5
            
        # Standard deviation depends on forecast agreement
        agreement = weather.get("agreement", "medium")
        if agreement == "high":
            sigma = 1.0  # High confidence, narrow distribution (1°C std dev)
        elif agreement == "low":
            sigma = 3.0  # Low confidence, wide distribution
        else:
            sigma = 1.8  # Default
            
        # Calculate cumulative probability using Normal Distribution CDF
        # P(X >= x) = 1 - CDF(x)
        # P(X < x) = CDF(x)
        try:
            cdf = self._normal_cdf(target_temp, mu=forecast_high, sigma=sigma)
            
            if condition == ">=":
                prob = 1.0 - cdf
            elif condition == "<":
                prob = cdf
            else:
                prob = 0.5
                
            logger.debug(f"📐 Target: {condition}{target_temp}°C | Forecast Mean: {forecast_high}°C (σ={sigma}) -> Prob: {prob:.2%}")
            return prob
            
        except Exception as e:
            logger.error(f"Error in temperature math: {e}")
            return 0.5

    def _eval_precipitation_market(self, market: dict, weather: dict) -> float:
        """Evaluate precipitation markets (rain/snow)."""
        question = market.get("question", "").lower()
        forecast_precip = weather.get("precipitation_mm", 0.0)
        
        # Simple threshold detection
        is_asking_for_rain = any(kw in question for kw in ["rain", "precipitation", "wet"])
        is_asking_for_dry = "dry" in question
        
        if is_asking_for_rain:
            # S-curve (logistic function) to map rain mm to probability
            # 0mm = ~10%, 1mm = ~50%, >5mm = ~95%
            prob = 1.0 / (1.0 + math.exp(-2.0 * (forecast_precip - 1.0)))
            return prob
        elif is_asking_for_dry:
            prob = 1.0 / (1.0 + math.exp(-2.0 * (forecast_precip - 1.0)))
            return 1.0 - prob
            
        return self._naive_estimate(market, weather)
        
    def _parse_temperature_condition(self, text: str) -> Tuple[str, Optional[float]]:
        """Extract the target temperature and condition (>= or <) from text."""
        # Clean text
        text = text.replace("°c", "").replace("celsius", "").replace(",", "")
        
        # Look for numbers
        nums = re.findall(r"[-+]?\d*\.\d+|\d+", text)
        if not nums:
            return "==", None
            
        # Assume the main number is the last or most prominent one (simple heuristic)
        target = float(nums[-1])
        
        # Determine condition
        if any(w in text for w in ["higher", "more", "above", "greater", ">=", ">", "at least"]):
            return ">=", target
        if any(w in text for w in ["lower", "less", "below", "under", "<=", "<", "at most"]):
            return "<", target
            
        # Default assumption for Polymarket temperature markets is typically ">= X"
        return ">=", target

    def _normal_cdf(self, x: float, mu: float, sigma: float) -> float:
        """Cumulative distribution function for normal distribution."""
        return (1.0 + math.erf((x - mu) / (sigma * math.sqrt(2.0)))) / 2.0
        
    def _naive_estimate(self, market: dict, weather: dict) -> float:
        market_price = market.get("yes_price", 0.5)
        source_count = weather.get("source_count", 1)
        if source_count >= 2:
            return max(0.05, min(0.95, market_price + 0.03 * (source_count - 1)))
        return market_price

strategy_engine = StrategyEngine()

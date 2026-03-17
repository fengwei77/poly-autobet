import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.strategy_engine import strategy_engine
from loguru import logger

logger.remove()
logger.add(sys.stdout, level="DEBUG")

def test_temperature_market():
    # Example: "Will the highest temperature in Tokyo be 15°C or higher?"
    market = {
        "category": "temperature",
        "question": "Will the high temperature be 15°C or higher tomorrow?",
        "yes_price": 0.50
    }
    
    # 1. Forecast matches target exactly
    weather = {"temp_high_c": 15.0, "agreement": "high"}
    prob = strategy_engine.estimate_probability(market, weather)
    print(f"Target=15, Forecast=15, High Conf -> Prob = {prob:.2%}")
    assert abs(prob - 0.5) < 0.01
    
    # 2. Forecast is much higher (18) than target (15)
    weather = {"temp_high_c": 18.0, "agreement": "high"}
    prob = strategy_engine.estimate_probability(market, weather)
    print(f"Target=15, Forecast=18, High Conf -> Prob = {prob:.2%}")
    assert prob > 0.90
    
    # 3. Forecast is much lower (12) than target (15)
    weather = {"temp_high_c": 12.0, "agreement": "high"}
    prob = strategy_engine.estimate_probability(market, weather)
    print(f"Target=15, Forecast=12, High Conf -> Prob = {prob:.2%}")
    assert prob < 0.10
    
    # 4. Low agreement makes probability closer to 0.5
    weather = {"temp_high_c": 16.0, "agreement": "high"}
    prob_high = strategy_engine.estimate_probability(market, weather)
    weather = {"temp_high_c": 16.0, "agreement": "low"}
    prob_low = strategy_engine.estimate_probability(market, weather)
    print(f"Target=15, Forecast=16, High Conf -> Prob = {prob_high:.2%}")
    print(f"Target=15, Forecast=16, Low Conf  -> Prob = {prob_low:.2%}")
    assert prob_high > prob_low
    
if __name__ == "__main__":
    test_temperature_market()
    print("✅ Strategy engine tests passed!")

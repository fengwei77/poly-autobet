"""
Tests: Basic test suite for Sprint 1 modules.
"""

import pytest
import asyncio


class TestConfig:
    def test_settings_load(self):
        from config.settings import settings
        assert settings.trading_mode.value in ("monitor", "paper", "live", "backtest")
        assert settings.max_single_bet > 0
        assert settings.min_edge > 0

    def test_cities_loaded(self):
        from config.cities import CITIES, get_city
        assert len(CITIES) > 0
        ny = get_city("new_york")
        assert ny is not None
        assert ny.lat == 40.7128

    def test_node_role(self):
        from config.settings import settings
        assert settings.node_role.value in ("brain", "executor")


class TestInfra:
    def test_json_utils(self):
        from infra.json_utils import json_dumps, json_loads, JSON_ENGINE
        data = {"name": "test", "value": 42, "nested": [1, 2, 3]}
        serialized = json_dumps(data)
        deserialized = json_loads(serialized)
        assert deserialized == data

    def test_event_loop_detect(self):
        from infra.event_loop import detect_environment
        env = detect_environment()
        assert "platform" in env
        assert "python_version" in env

    def test_redis_client_init(self):
        from infra.redis_client import RedisClient
        client = RedisClient("redis://localhost:6379")
        assert not client.connected


class TestModels:
    def test_market_model(self):
        from data.models import Market
        m = Market(condition_id="test123", question="Will it rain?", city="new_york", is_active=True)
        assert m.condition_id == "test123"
        assert m.is_active is True

    def test_trade_model(self):
        from data.models import Trade
        t = Trade(
            market_condition_id="test123",
            side="BUY",
            price=0.65,
            size=10,
            amount_usdc=6.5,
            is_paper=True,
            status="pending",
        )
        assert t.is_paper is True
        assert t.status == "pending"


class TestScanner:
    def test_weather_keyword_detection(self):
        from core.scanner import MarketScanner
        s = MarketScanner()
        assert s._detect_category("Will NYC high temperature exceed 80°F?") == "temperature"
        assert s._detect_category("Will it rain more than 2 inches?") == "precipitation"
        assert s._detect_category("Some random question") == "weather"

    # City detection moved to config/cities.py


class TestRiskManager:
    def test_single_bet_limit(self):
        from core.risk_manager import RiskManager
        rm = RiskManager()
        ok, _ = rm._check_single_bet_limit({"suggested_size_usdc": 10})
        assert ok is True
        fail, reason = rm._check_single_bet_limit({"suggested_size_usdc": 999})
        assert fail is False

    def test_kelly_criterion(self):
        from core.ai_analyzer import AIAnalyzer
        ai = AIAnalyzer()
        # High edge → positive Kelly
        k = ai._kelly_criterion(0.8, 0.5)
        assert k > 0
        # No edge → zero Kelly
        k = ai._kelly_criterion(0.5, 0.5)
        assert k == 0.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

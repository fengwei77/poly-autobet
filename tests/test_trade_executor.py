import sys
import os
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.trade_executor import trade_executor as executor
from core.risk_manager import risk_manager
from data.models import Trade
from config.settings import TradingMode
import contextlib

@contextlib.asynccontextmanager
async def mock_distributed_lock(*args, **kwargs):
    yield True

@contextlib.asynccontextmanager
async def mock_async_session(*args, **kwargs):
    mock_db = AsyncMock()
    yield mock_db

@pytest.fixture(autouse=True)
def mock_clean_executor():
    """Ensure tests run with isolated settings."""
    with patch.multiple("core.trade_executor.settings", max_daily_exposure=500.0, trading_mode=TradingMode.PAPER, max_single_bet=50.0):
        with patch.multiple("core.risk_manager.settings", max_daily_exposure=500.0):
            yield

@pytest.mark.asyncio
async def test_exceeding_max_exposure_rejected():
    """Test that a trade is rejected if daily exposure has been surpassed."""
    # The mock_clean_executor fixture automatically enforces settings (500 limit).
    
    with patch("core.trade_executor.redis_client") as mock_exec_redis:
        mock_exec_redis.distributed_lock = mock_distributed_lock
        
        with patch("core.risk_manager.redis_client", new_callable=AsyncMock) as mock_rm_redis:
            mock_rm_redis.cache_get.return_value = "500.0"
        
            # Try to execute a single bet of 30.0 -> total will be 510.0 > 500.0
            # Should be rejected
            signal = {"signal": "BUY", "suggested_size_usdc": 30.0}
            market = {"condition_id": "0xMAX1", "question": "Will it be sunny?", "city": "Taipei", "tokens": "111_YES", "yes_price": 0.50}
            
            trade_result = await executor.execute(signal, market)
            
            assert trade_result["status"] == "blocked"
            assert "daily exposure" in trade_result["reason"].lower() or "limit" in trade_result["reason"].lower()

@pytest.mark.asyncio
async def test_live_execution_token_mapping():
    """Verify that LIVE trades pass the correct side and token_id to Clob Client."""
    # Mock py_clob_client to prevent ImportError during live trade execution
    with patch.dict("sys.modules", {"py_clob_client": MagicMock(), "py_clob_client.order_builder": MagicMock(), "py_clob_client.order_builder.constants": MagicMock()}):
        # Force live mode
        with patch.multiple("core.trade_executor.settings", trading_mode=TradingMode.LIVE, max_single_bet=50.0):
            with patch("core.trade_executor.redis_client") as mock_exec_redis:
                mock_exec_redis.distributed_lock = mock_distributed_lock
                mock_exec_redis.publish = AsyncMock()
                
                # Mock PyClobClient inside executor
                with patch("core.trade_executor.trade_executor._clob_client") as mock_client:
                    # Setup mock return for create_market_order
                    mock_order_result = {"orderID": "live_order_123"}
                    mock_client.create_and_post_order.return_value = mock_order_result
                    
                    signal = {"signal": "BUY", "suggested_size_usdc": 20.0}
                    market = {"condition_id": "0xLIVE1", "question": "Live bet?", "city": "Taipei", "tokens": "555_YES", "yes_price": 0.50}
                    
                    # In live mode _init_clob_client is called, mock async_session so it doesn't try hitting DB
                    with patch("core.trade_executor.async_session", mock_async_session):
                        trade_result = await executor.execute(signal, market)
                            
                        assert trade_result["status"] == "pending"
                        assert trade_result["is_paper"] is False
                        assert mock_client.create_and_post_order.called
                            
                        # Verify args sent to Polymarket
                        call_kwargs = mock_client.create_and_post_order.call_args[0][0]
                        assert call_kwargs["token_id"] == "555_YES"


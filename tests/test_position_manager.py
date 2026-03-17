import sys
import os
import pytest
import uuid
from decimal import Decimal
from unittest.mock import AsyncMock, patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.position_manager import position_manager
from data.models import Trade

# Mock the settings so tests aren't prone to environment differences
@pytest.fixture(autouse=True)
def mock_scalp_settings():
    with patch("core.position_manager.settings") as mock_settings:
        mock_settings.scalping_take_profit_pct = 0.15  # +15%
        mock_settings.scalping_stop_loss_pct = 0.10    # -10%
        yield mock_settings

@pytest.fixture
def mock_trade():
    """Returns a mock open BUY trade for paper mode."""
    trade = Trade(
        id=1,
        market_condition_id="0xTEST123",
        order_id="test-order-1",
        side="BUY",
        token_id="12345",
        price=0.50,
        size=100.0,
        amount_usdc=50.0,  # size * price
        status="filled",
        fill_price=0.50,
        is_paper=True,
        resolved=False,
        pnl=0.0
    )
    return trade

@pytest.mark.asyncio
async def test_take_profit_trigger(mock_trade):
    """Test that a +15% gain triggers a TAKE_PROFIT sell."""
    # 0.50 -> 0.60 is a +20% gain. (60 / 50 = 1.20 >= 1.15)
    current_price = 0.60
    
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [mock_trade]
    mock_session.execute.return_value = mock_result
    
    with patch("core.position_manager.async_session") as mock_db_ctx:
        # Mock the context manager behavior of async_session()
        mock_db_ctx.return_value.__aenter__.return_value = mock_session
        
        # Mock Redis so it doesn't try to connect
        with patch("core.position_manager.redis_client"):
            await position_manager.scan_positions_for_exit("0xTEST123", current_price)
            
    # Session should have had add() called for the new SELL trade
    assert mock_session.add.called
    sell_trade_arg = mock_session.add.call_args[0][0]
    
    assert sell_trade_arg.side == "SELL"
    assert sell_trade_arg.price == 0.60
    assert sell_trade_arg.size == 100.0
    assert sell_trade_arg.amount_usdc == 60.0
    assert sell_trade_arg.pnl == 10.0  # 60 - 50 = +10
    assert "take_profit" in sell_trade_arg.order_id
    
    # Original trade should be marked resolved
    assert mock_trade.resolved is True
    # Session commit should be called
    assert mock_session.commit.called

@pytest.mark.asyncio
async def test_stop_loss_trigger(mock_trade):
    """Test that a -10% loss triggers a STOP_LOSS sell."""
    # 0.50 -> 0.40 is a -20% loss. (40 / 50 = 0.80 <= 0.90)
    current_price = 0.40
    
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [mock_trade]
    mock_session.execute.return_value = mock_result
    
    with patch("core.position_manager.async_session") as mock_db_ctx:
        mock_db_ctx.return_value.__aenter__.return_value = mock_session
        
        with patch("core.position_manager.redis_client"):
            await position_manager.scan_positions_for_exit("0xTEST123", current_price)
            
    # Session should have had add() called for the new SELL trade
    assert mock_session.add.called
    sell_trade_arg = mock_session.add.call_args[0][0]
    
    assert sell_trade_arg.side == "SELL"
    assert sell_trade_arg.price == 0.40
    assert sell_trade_arg.pnl == -10.0  # 40 - 50 = -10
    assert "stop_loss" in sell_trade_arg.order_id
    assert mock_trade.resolved is True

@pytest.mark.asyncio
async def test_no_action_in_neutral_zone(mock_trade):
    """Test that no action is taken if the price is within the safe zone."""
    # 0.50 -> 0.52 is a +4% gain. Safe zone.
    current_price = 0.52
    
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [mock_trade]
    mock_session.execute.return_value = mock_result
    
    with patch("core.position_manager.async_session") as mock_db_ctx:
        mock_db_ctx.return_value.__aenter__.return_value = mock_session
        
        with patch("core.position_manager.redis_client"):
            await position_manager.scan_positions_for_exit("0xTEST123", current_price)
            
    # Session should NOT have had add() called
    assert not mock_session.add.called
    # Original trade should still be unresolved
    assert mock_trade.resolved is False

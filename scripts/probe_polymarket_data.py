
import asyncio
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.append(str(Path(__file__).parent.parent))

from config.settings import settings
from loguru import logger

async def probe_balances():
    if not settings.polymarket_private_key or settings.polymarket_private_key == "your_private_key_here":
        logger.error("No private key configured")
        return

    try:
        from py_clob_client.client import ClobClient
        client = ClobClient(
            host=settings.polymarket_host,
            key=settings.polymarket_private_key,
            chain_id=settings.polymarket_chain_id,
            signature_type=2,
        )
        
        # 1. Get Address
        address = client.get_address()
        logger.info(f"Wallet Address: {address}")
        
        # 2. Try get_balance_allowance (Note: likely needs asset_id or similar)
        # Polymarket USDC on Polygon is usually 0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174 (bridged) 
        # or 0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359 (native)
        # We can try to get it from collateral address
        collateral = client.get_collateral_address()
        logger.info(f"Collateral Address: {collateral}")
        
        try:
            balance = client.get_balance_allowance(collateral)
            logger.info(f"Balance/Allowance: {balance}")
        except Exception as e:
            logger.error(f"Failed get_balance_allowance: {e}")

        # 3. Try get_trades
        try:
            trades = client.get_trades(maker_address=address)
            logger.info(f"Recent Trades (Maker): {len(trades)}")
            if trades:
                logger.info(f"First trade sample: {trades[0]}")
        except Exception as e:
            logger.error(f"Failed get_trades: {e}")

    except Exception as e:
        logger.error(f"Probe failed: {e}")

if __name__ == "__main__":
    asyncio.run(probe_balances())

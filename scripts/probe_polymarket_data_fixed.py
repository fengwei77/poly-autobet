
import asyncio
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.append(str(Path(__file__).parent.parent))

from config.settings import settings
from loguru import logger

async def probe_balances_fixed():
    if not settings.polymarket_private_key:
        logger.error("No private key configured")
        return

    try:
        from py_clob_client.client import ClobClient
        client = ClobClient(
            host=settings.polymarket_host,
            key=settings.polymarket_private_key,
            chain_id=settings.polymarket_chain_id,
            signature_type=2,
            api_key=settings.polymarket_api_key,
            api_secret=settings.polymarket_api_secret,
            api_passphrase=settings.polymarket_passphrase,
        )
        
        # 1. Get Address
        address = client.get_address()
        logger.info(f"Wallet Address: {address}")
        
        # 2. Get Balance/Allowance
        collateral = client.get_collateral_address()
        try:
            bal_data = client.get_balance_allowance(collateral)
            logger.info(f"Successfully fetched balance: {bal_data}")
        except Exception as e:
            logger.error(f"Failed get_balance_allowance: {e}")

        # 3. Get Trades
        try:
            trades = client.get_trades()
            logger.info(f"Successfully fetched trades: {len(trades)}")
        except Exception as e:
            logger.error(f"Failed get_trades: {e}")

    except Exception as e:
        logger.error(f"Probe failed: {e}")

if __name__ == "__main__":
    asyncio.run(probe_balances_fixed())

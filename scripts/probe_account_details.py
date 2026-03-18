
import os
import json
from py_clob_client.client import ClobClient
from py_clob_client.clob_types import ApiCreds, BalanceAllowanceParams, TradeParams, AssetType
from dotenv import load_dotenv

load_dotenv()

def probe():
    pk = os.getenv("POLYMARKET_PRIVATE_KEY")
    creds = ApiCreds(
        api_key=os.getenv("POLYMARKET_API_KEY"),
        api_secret=os.getenv("POLYMARKET_API_SECRET"),
        api_passphrase=os.getenv("POLYMARKET_PASSPHRASE")
    )
    
    client = ClobClient("https://clob.polymarket.com", key=pk, chain_id=137, creds=creds)
    address = client.get_address()
    print(f"Address: {address}")
    
    print("\n--- Testing get_balance_allowance (COLLATERAL) ---")
    try:
        params = BalanceAllowanceParams(asset_type=AssetType.COLLATERAL)
        bal_collateral = client.get_balance_allowance(params)
        print(f"Collateral Balance Response: {json.dumps(bal_collateral, indent=2)}")
    except Exception as e:
        print(f"Collateral Balance Error: {e}")

    print("\n--- Testing get_balance_allowance (CONDITIONAL) ---")
    try:
        params = BalanceAllowanceParams(asset_type=AssetType.CONDITIONAL)
        bal_conditional = client.get_balance_allowance(params)
        print(f"Conditional Balance Response (truncated): {str(bal_conditional)[:200]}...")
    except Exception as e:
        print(f"Conditional Balance Error: {e}")

    print("\n--- Testing get_trades ---")
    try:
        params = TradeParams(maker_address=address)
        trades = client.get_trades(params)
        print(f"Trades Count: {len(trades)}")
        if trades:
            print(f"First Trade: {json.dumps(trades[0], indent=2)}")
    except Exception as e:
        print(f"Trades Error: {e}")

    print("\n--- Inspecting Client Methods for Transfers/History ---")
    methods = [m for m in dir(client) if not m.startswith('_')]
    print(f"Available methods: {methods}")
    
    # Try looking for anything related to funds, transfers, or history
    keywords = ['transfer', 'payment', 'deposit', 'withdraw', 'history', 'transaction', 'notification']
    relevant = [m for m in methods if any(k in m.lower() for k in keywords)]
    print(f"Potentially relevant methods: {relevant}")

if __name__ == "__main__":
    probe()

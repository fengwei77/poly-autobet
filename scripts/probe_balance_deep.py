
import os
import json
from py_clob_client.client import ClobClient
from py_clob_client.clob_types import ApiCreds, BalanceAllowanceParams, AssetType
from dotenv import load_dotenv

load_dotenv()

def probe_deep():
    pk = os.getenv("POLYMARKET_PRIVATE_KEY")
    creds = ApiCreds(
        api_key=os.getenv("POLYMARKET_API_KEY"),
        api_secret=os.getenv("POLYMARKET_API_SECRET"),
        api_passphrase=os.getenv("POLYMARKET_PASSPHRASE")
    )
    host = "https://clob.polymarket.com"
    chain_id = 137

    for sig_type in [0, 1, 2, None]:
        print(f"\n===== Testing signature_type={sig_type} =====")
        try:
            client = ClobClient(host, key=pk, chain_id=chain_id, creds=creds, signature_type=sig_type)
            address = client.get_address()
            print(f"Address: {address}")
            
            params = BalanceAllowanceParams(asset_type=AssetType.COLLATERAL)
            bal = client.get_balance_allowance(params)
            print(f"Balance: {bal.get('balance', '0')} (Wei), {int(bal.get('balance', '0'))/1e6} (USDC)")
            print(f"Allowance (first 10 chars): {str(bal.get('allowances', {}))[:100]}...")
            
            # Check notifications
            notes = client.get_notifications()
            print(f"Notifications: {len(notes)} found")
            if notes:
                for n in notes[:3]:
                    print(f"  - {n.get('created_at')}: {n.get('type')} {n.get('amount')}")
                    
            # Check orders
            orders = client.get_orders()
            print(f"Open Orders: {len(orders)}")

        except Exception as e:
            print(f"Error with sig_type {sig_type}: {e}")

if __name__ == "__main__":
    probe_deep()


import os
import json
from py_clob_client.client import ClobClient
from py_clob_client.clob_types import ApiCreds, BalanceAllowanceParams, AssetType
from dotenv import load_dotenv

load_dotenv()

def probe_deep():
    pk = os.getenv("POLYMARKET_PRIVATE_KEY")
    host = "https://clob.polymarket.com"
    chain_id = 137

    # Token Addresses
    USDC_E = "0x2791bca1f2de4661ed88a30c99a7a9449aa84174"
    USDC_NATIVE = "0x3c499c542cef5e3811e1192ce70d8cc03d5c3359"

    for sig_type in [None, 0, 1, 2]:
        print(f"\n===== Testing signature_type={sig_type} =====")
        try:
            # Initialize with PK only first to derive fresh keys for this sig_type
            client = ClobClient(host, key=pk, chain_id=chain_id, signature_type=sig_type)
            address = client.get_address()
            print(f"Address: {address}")
            
            print("Deriving fresh API keys for this sig_type...")
            creds = client.create_or_derive_api_creds()
            client.set_api_creds(creds)
            print(f"Derived Key: {creds.api_key[:10]}...")

            # 1. Test standard COLLATERAL
            print("Checking AssetType.COLLATERAL...")
            try:
                params = BalanceAllowanceParams(asset_type=AssetType.COLLATERAL)
                bal = client.get_balance_allowance(params)
                print(f"  COLLATERAL Balance: {bal.get('balance', '0')} (Wei)")
            except Exception as e:
                print(f"  COLLATERAL Error: {e}")

            # 2. Test USDC.e specifically
            print(f"Checking USDC.e ({USDC_E})...")
            try:
                params = BalanceAllowanceParams(asset_id=USDC_E)
                bal = client.get_balance_allowance(params)
                print(f"  USDC.e Balance: {bal.get('balance', '0')} (Wei)")
            except Exception as e:
                print(f"  USDC.e Error: {e}")

            # 3. Test Native USDC specifically
            print(f"Checking Native USDC ({USDC_NATIVE})...")
            try:
                params = BalanceAllowanceParams(asset_id=USDC_NATIVE)
                bal = client.get_balance_allowance(params)
                print(f"  Native USDC Balance: {bal.get('balance', '0')} (Wei)")
            except Exception as e:
                print(f"  Native USDC Error: {e}")

            # 4. Check Notifications for recent deposit
            notes = client.get_notifications()
            print(f"Notifications: {len(notes)} found")
            if notes:
                for n in notes[:5]:
                    print(f"  - {n.get('created_at')}: {n.get('type')} {n.get('amount')} {n.get('data')}")

        except Exception as e:
            print(f"Error with sig_type {sig_type}: {e}")

if __name__ == "__main__":
    probe_deep()

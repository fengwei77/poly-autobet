
import os
import json
from py_clob_client.client import ClobClient
from py_clob_client.clob_types import ApiCreds, BalanceAllowanceParams, AssetType
from dotenv import load_dotenv

load_dotenv()

def diagnostic():
    pk = os.getenv("POLYMARKET_PRIVATE_KEY")
    api_key = os.getenv("POLYMARKET_API_KEY")
    api_secret = os.getenv("POLYMARKET_API_SECRET")
    api_passphrase = os.getenv("POLYMARKET_PASSPHRASE")
    
    print(f"Testing with API_KEY: {api_key}")
    
    creds = ApiCreds(
        api_key=api_key,
        api_secret=api_secret,
        api_passphrase=api_passphrase
    )
    
    host = "https://clob.polymarket.com"
    chain_id = 137

    print("\n--- Testing signature_type=1 with EXISTING .env keys ---")
    try:
        client = ClobClient(host, key=pk, chain_id=chain_id, creds=creds, signature_type=1)
        params = BalanceAllowanceParams(asset_type=AssetType.COLLATERAL)
        bal = client.get_balance_allowance(params)
        print(f"Success! Balance: {bal.get('balance')}")
    except Exception as e:
        print(f"Failed with existing keys: {e}")

    print("\n--- Testing signature_type=1 with FRESHLY DERIVED keys ---")
    try:
        client_fresh = ClobClient(host, key=pk, chain_id=chain_id, signature_type=1)
        creds_fresh = client_fresh.create_or_derive_api_creds()
        client_fresh.set_api_creds(creds_fresh)
        params = BalanceAllowanceParams(asset_type=AssetType.COLLATERAL)
        bal_fresh = client_fresh.get_balance_allowance(params)
        print(f"Success with fresh keys! Balance: {bal_fresh.get('balance')}")
        print(f"New Key: {creds_fresh.api_key}")
        print(f"New Secret: {creds_fresh.api_secret}")
        print(f"New Passphrase: {creds_fresh.api_passphrase}")
    except Exception as e:
        print(f"Failed even with fresh keys: {e}")

if __name__ == "__main__":
    diagnostic()

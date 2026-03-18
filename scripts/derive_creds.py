import os
from py_clob_client.client import ClobClient
from py_clob_client.clob_types import ApiCreds
from dotenv import load_dotenv

# Load .env
load_dotenv()

pk = os.getenv("POLYMARKET_PRIVATE_KEY")
host = "https://clob.polymarket.com"
chain_id = 137

print(f"Using PK: {pk[:10]}...")

try:
    # 1. Initialize with ONLY PK first to derive
    client = ClobClient(host, key=pk, chain_id=chain_id)
    print("Agent address:", client.get_address())
    
    # 2. Derive/Create API Creds
    print("Deriving API credentials...")
    creds = client.create_or_derive_api_creds()
    
    print("-" * 20)
    print(f"API_KEY={creds.api_key}")
    print(f"API_SECRET={creds.api_secret}")
    print(f"API_PASSPHRASE={creds.api_passphrase}")
    print("-" * 20)
    
    # 3. Test if they work
    client.set_api_creds(creds)
    print("Testing balance fetch...")
    from py_clob_client.clob_types import BalanceAllowanceParams, AssetType
    params = BalanceAllowanceParams(asset_type=AssetType.COLLATERAL)
    resp = client.get_balance_allowance(params)
    print(f"Balance result: {resp}")
    
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()

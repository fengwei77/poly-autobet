
from py_clob_client.client import ClobClient
import inspect

methods = ['set_api_creds', 'get_trades', 'get_balance_allowance', 'get_collateral_address']
for m in methods:
    try:
        sig = inspect.signature(getattr(ClobClient, m))
        print(f"{m} signature: {sig}")
    except Exception as e:
        print(f"Could not get signature for {m}: {e}")

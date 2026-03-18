
from py_clob_client.client import ClobClient
import inspect

# Get signature of set_api_creds
sig = inspect.signature(ClobClient.set_api_creds)
print(f"set_api_creds signature: {sig}")

# Get signature of get_trades
sig_trades = inspect.signature(ClobClient.get_trades)
print(f"get_trades signature: {sig_trades}")

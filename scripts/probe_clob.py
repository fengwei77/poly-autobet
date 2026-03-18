
from py_clob_client.client import ClobClient
import inspect

methods = sorted([m for m, _ in inspect.getmembers(ClobClient, predicate=inspect.isfunction) if not m.startswith("_")])
for m in methods:
    print(m)

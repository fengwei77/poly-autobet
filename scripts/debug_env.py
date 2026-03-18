
import os
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.append(str(Path(__file__).parent.parent))

try:
    from config.settings import settings
    print(f"OS ENV PK: {os.environ.get('POLYMARKET_PRIVATE_KEY', 'NOT FOUND')[:10]}...")
    print(f"SETTINGS PK: {settings.polymarket_private_key[:10]}...")
    print(f"IS LIVE: {settings.is_live}")
    print(f"TRADING MODE: {settings.trading_mode}")
    print(f"API KEY: {settings.polymarket_api_key}")
    print(f"SECRET: {settings.polymarket_api_secret[:10]}...")
except Exception as e:
    print(f"ERROR: {e}")

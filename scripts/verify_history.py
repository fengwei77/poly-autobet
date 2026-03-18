
import os
import json
from py_clob_client.client import ClobClient
from py_clob_client.clob_types import ApiCreds, TradeParams
from dotenv import load_dotenv

load_dotenv()

def verify_history():
    pk = os.getenv("POLYMARKET_PRIVATE_KEY")
    host = "https://clob.polymarket.com"
    chain_id = 137
    sig_type = 1 # The confirmed working type

    print(f"===== Testing History with signature_type={sig_type} =====")
    try:
        client = ClobClient(host, key=pk, chain_id=chain_id, signature_type=sig_type)
        address = client.get_address()
        print(f"Address: {address}")
        
        creds = client.create_or_derive_api_creds()
        client.set_api_creds(creds)
        
        print("Checking get_trades()...")
        try:
            params = TradeParams(maker_address=address)
            trades = client.get_trades(params)
            print(f"Trades found: {len(trades)}")
            if trades:
                print(f"First trade: {json.dumps(trades[0], indent=2)}")
        except Exception as e:
            print(f"Trades Error: {e}")

        print("Checking get_notifications()...")
        try:
            notes = client.get_notifications()
            print(f"Notifications: {len(notes)}")
            if notes:
                for n in notes[:5]:
                    print(f"  - {n.get('created_at')}: {n.get('type')} {n.get('amount')}")
        except Exception as e:
            print(f"Notifications Error: {e}")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    verify_history()

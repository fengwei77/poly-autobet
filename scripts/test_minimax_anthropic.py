import httpx
import json
import os
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("MINIMAX_API_KEY")
url = "https://api.minimax.io/anthropic/v1/messages"  # Modified based on typical Anthropic route

headers = {
    "x-api-key": api_key,
    "anthropic-version": "2023-06-01",
    "Content-Type": "application/json"
}

payload = {
    "model": "MiniMax-M2.5",
    "max_tokens": 1024,
    "messages": [
        {"role": "user", "content": "Hello, are you working?"}
    ]
}

def test_anthropic():
    print(f"Testing MiniMax Anthropic endpoint...")
    print(f"URL: {url}")
    try:
        with httpx.Client() as client:
            resp = client.post(url, json=payload, headers=headers, timeout=30)
            print(f"Status Code: {resp.status_code}")
            if resp.status_code == 200:
                print("Success!")
                print(json.dumps(resp.json(), indent=2, ensure_ascii=False))
            else:
                print(f"Error: {resp.text}")
    except Exception as e:
        print(f"Exception: {e}")

if __name__ == "__main__":
    test_anthropic()

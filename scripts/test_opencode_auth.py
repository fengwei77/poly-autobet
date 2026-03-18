import httpx
import json
import os
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("MINIMAX_API_KEY")
url = "https://opencode.ai/zen/go/v1/messages"

payload = {
    "model": "minimax-m2.5",
    "max_tokens": 1024,
    "messages": [
        {"role": "user", "content": "Hello"}
    ]
}

def test_auth(method):
    print(f"\n--- Testing with {method} ---")
    headers = {
        "anthropic-version": "2023-06-01",
        "Content-Type": "application/json"
    }
    if method == "x-api-key":
        headers["x-api-key"] = api_key
    else:
        headers["Authorization"] = f"Bearer {api_key}"
        
    try:
        with httpx.Client() as client:
            resp = client.post(url, json=payload, headers=headers, timeout=10)
            print(f"Status Code: {resp.status_code}")
            print(f"Response: {resp.text}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    if not api_key:
        print("No API key found in .env")
    else:
        test_auth("x-api-key")
        test_auth("Bearer")

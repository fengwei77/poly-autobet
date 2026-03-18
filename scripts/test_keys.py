import asyncio
import httpx
from loguru import logger

async def test_key(name, key):
    logger.info(f"🔍 Testing {name}...")
    url = "https://api.minimax.io/v1/text/chatcompletion_v2"
    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "MiniMax-M2.5",
        "messages": [{"role": "user", "content": "Hi, just say 'ready'"}]
    }
    
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(url, json=payload, headers=headers, timeout=10)
            data = resp.json()
            if resp.status_code == 200:
                choices = data.get('choices', [])
                content = choices[0].get('message', {}).get('content') if choices else "No content"
                logger.success(f"✅ {name} works! Content: {content}")
                return True
            else:
                logger.error(f"❌ {name} failed: {resp.status_code} - {data}")
                return False
    except Exception as e:
        logger.error(f"❌ {name} error: {e}")
        return False

async def main():
    keys = {
        "API Key (sk-api)": "sk-api-4voKVKD87nCwiyBd53OesUaSi3FKv25z4SYxcQBXebGWZogHQ6euw_oLWinvVNTgkKJiy2JCiGAM7RR9yoytCj8a_2Wbc6WLOPdQ9NlJCX9W-2qhbxuTOD4",
        "Coding Plan Key (sk-cp)": "sk-cp-mzoI2NrkyJbP2APYwVRHVoOUdHjrVhkBM15Fk0NgjFX7B2N_655EHAvncU00A4s-peaszIH_43azp7pUPl03EbBAVdUvGZRxAtW5u8kX-p_LW9LpdDcn548"
    }
    
    for name, key in keys.items():
        await test_key(name, key)

if __name__ == "__main__":
    asyncio.run(main())

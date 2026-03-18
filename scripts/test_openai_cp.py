import asyncio
from openai import AsyncOpenAI
from loguru import logger

async def test_openai_sdk():
    key = "sk-cp-mzoI2NrkyJbP2APYwVRHVoOUdHjrVhkBM15Fk0NgjFX7B2N_655EHAvncU00A4s-peaszIH_43azp7pUPl03EbBAVdUvGZRxAtW5u8kX-p_LW9LpdDcn548"
    base_url = "https://api.minimax.io/v1"
    
    logger.info("🧪 Testing sk-cp with OpenAI SDK...")
    client = AsyncOpenAI(api_key=key, base_url=base_url)
    
    try:
        resp = await client.chat.completions.create(
            model="MiniMax-M2.5",
            messages=[{"role": "user", "content": "hi"}]
        )
        logger.success(f"✅ OpenAI SDK Success: {resp.choices[0].message.content}")
    except Exception as e:
        logger.error(f"❌ OpenAI SDK Failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_openai_sdk())

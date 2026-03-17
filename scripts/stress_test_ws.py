import asyncio
import sys
import time
import os
import json
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from infra.redis_client import redis_client

async def run_stress_test(num_messages: int = 5000, batch_size: int = 500):
    print(f"🚀 Starting WebSocket / Redis stress test...")
    print(f"📦 Total messages to send: {num_messages}")
    print(f"🚅 Batch size: {batch_size}")
    
    start_time = time.time()
    messages_sent = 0
    
    # We will simulate a fake market
    fake_market_id = f"0xSTRESS_{uuid.uuid4().hex[:8]}"
    
    # Ensure Redis is connected
    await redis_client.connect()
    print("✅ Connected to Redis")

    try:
        while messages_sent < num_messages:
            tasks = []
            for _ in range(batch_size):
                if messages_sent >= num_messages:
                    break
                
                # Mock a Polymarket price update message
                price_msg = {
                    "condition_id": fake_market_id,
                    "tokens": "YES_TOKEN,NO_TOKEN",
                    "yes_price": 0.50 + (messages_sent % 10) * 0.01, # Fluctuating price
                    "timestamp": time.time()
                }
                
                tasks.append(
                    redis_client.publish("market:price_update", json.dumps(price_msg))
                )
                messages_sent += 1
            
            # Fire the batch asynchronously
            await asyncio.gather(*tasks)
            print(f"Sent {messages_sent} / {num_messages} messages...")
            # Short sleep to not completely overwhelm the local network stack, but fast enough to stress test
            await asyncio.sleep(0.05)
            
    except Exception as e:
        print(f"❌ Error during stress test: {e}")
        
    finally:
        end_time = time.time()
        duration = end_time - start_time
        print("\n🏁 Stress Test Completed!")
        print(f"⏱️ Duration: {duration:.2f} seconds")
        print(f"⚡ Throughput: {num_messages / duration:.2f} messages/second")
        await redis_client.close()

if __name__ == "__main__":
    if os.name == "nt":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(run_stress_test())

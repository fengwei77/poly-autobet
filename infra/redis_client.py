"""
Infrastructure: Redis client with Pub/Sub, distributed locks, and caching.
"""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator, Optional

import redis.asyncio as aioredis
from loguru import logger
from config.settings import settings


class RedisClient:
    """Async Redis client with Pub/Sub, Lock, and cache capabilities."""

    def __init__(self, url: Optional[str] = None):
        self._url = url or settings.redis_url
        self._pool: Optional[aioredis.Redis] = None
        self._in_memory_cache: dict[str, str] = {}
        self._in_memory_subs: dict[str, list[asyncio.Queue]] = {}

    async def connect(self) -> None:
        # If url is from settings and contains 'redis', try localhost first if on Windows
        candidate_urls = [self._url]
        if "redis:" in self._url:
            candidate_urls.insert(0, self._url.replace("redis:", "localhost:"))

        for url in candidate_urls:
            try:
                logger.debug(f"🔄 Attempting Redis connection: {url}")
                new_pool = aioredis.from_url(
                    url,
                    decode_responses=True,
                    max_connections=20,
                    socket_connect_timeout=2
                )
                await new_pool.ping()
                self._pool = new_pool
                logger.success(f"✅ Redis connected successfully: {url}")
                return
            except Exception as e:
                logger.debug(f"Redis connection to {url} failed: {e}")
                pass
        
        logger.warning("⚠️ Redis connection failed. Using IN-MEMORY fallback for testing.")
        self._pool = None

    async def close(self) -> None:
        if self._pool:
            await self._pool.close()
            logger.info("Redis connection closed.")

    @property
    def connected(self) -> bool:
        return self._pool is not None

    @property
    def pool(self) -> aioredis.Redis:
        if not self._pool:
            raise RuntimeError("Redis not connected. Call connect() first.")
        return self._pool

    # === Cache Operations ===

    async def cache_get(self, key: str) -> Optional[str]:
        if not self.connected:
            return self._in_memory_cache.get(key)
        return await self.pool.get(key)

    async def cache_set(self, key: str, value: str, ttl: int = 300) -> None:
        if not self.connected:
            self._in_memory_cache[key] = value
            return
        await self.pool.set(key, value, ex=ttl)

    async def cache_delete(self, key: str) -> None:
        if not self.connected:
            self._in_memory_cache.pop(key, None)
            return
        await self.pool.delete(key)

    # === Distributed Lock ===

    @asynccontextmanager
    async def distributed_lock(
        self, lock_name: str, timeout: int = 30, blocking_timeout: int = 5
    ) -> AsyncGenerator[bool, None]:
        if not self.connected:
            yield True
            return

        lock = self.pool.lock(
            f"lock:{lock_name}",
            timeout=timeout,
            blocking_timeout=blocking_timeout,
        )
        acquired = False
        try:
            acquired = await lock.acquire()
            yield acquired
        finally:
            if acquired:
                try:
                    await lock.release()
                except Exception:
                    pass

    # === Pub/Sub ===

    async def publish(self, channel: str, message: str) -> int:
        """Publish a message to a Redis channel."""
        if not self.connected:
            logger.info(f"📣 [In-Memory Pub] {channel} -> {message}")
            if channel in self._in_memory_subs:
                for q in self._in_memory_subs[channel]:
                    await q.put({"type": "message", "channel": channel, "data": message})
                return len(self._in_memory_subs[channel])
            return 0
        return await self.pool.publish(channel, message)

    async def subscribe(self, channel: str):
        """Subscribe to a Redis channel. Returns an async iterator/mock object."""
        if not self.connected:
            logger.info(f"📡 [In-Memory Sub] Subscribing to: {channel}")
            q = asyncio.Queue()
            if channel not in self._in_memory_subs:
                self._in_memory_subs[channel] = []
            self._in_memory_subs[channel].append(q)
            
            # Mock object for compat
            class MockPubSub:
                def __init__(self, queue): self.queue = queue
                async def listen(self):
                    while True: yield await self.queue.get()
                async def get_message(self, ignore_subscribe_messages=True, timeout=1.0):
                    try:
                        return await asyncio.wait_for(self.queue.get(), timeout=timeout)
                    except asyncio.TimeoutError:
                        return None
                async def unsubscribe(self, *args): pass
                async def __aenter__(self): return self
                async def __aexit__(self, *args): pass
            
            return MockPubSub(q)
            
        pubsub = self.pool.pubsub()
        await pubsub.subscribe(channel)
        return pubsub

    # === Rate Limiting ===

    async def rate_limit_check(self, key: str, max_calls: int, window_seconds: int) -> bool:
        """
        Sliding window rate limiter.
        Returns True if the request is within limits.
        """
        if not self.connected:
            return True  # No Redis → no rate limiting

        current = await self.pool.incr(f"ratelimit:{key}")
        if current == 1:
            await self.pool.expire(f"ratelimit:{key}", window_seconds)
        return current <= max_calls


# Module-level singleton (initialized in main.py)
redis_client = RedisClient()

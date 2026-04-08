"""FIFO scheduler — per-device execution queue backed by Redis."""

import asyncio
import json
import logging
from typing import Optional

import redis.asyncio as redis

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class Scheduler:
    """FIFO queue per device using Redis lists."""

    def __init__(self):
        self._redis: Optional[redis.Redis] = None

    async def connect(self):
        self._redis = redis.from_url(settings.REDIS_URL, decode_responses=True)
        logger.info("Scheduler connected to Redis")

    async def disconnect(self):
        if self._redis:
            await self._redis.aclose()

    def _queue_key(self, device_id: str) -> str:
        return f"exec_queue:{device_id}"

    async def enqueue(self, device_id: str, execution_id: str) -> int:
        """Add execution to device queue. Returns queue position (0-based)."""
        key = self._queue_key(device_id)
        await self._redis.rpush(key, execution_id)
        length = await self._redis.llen(key)
        logger.info("Enqueued %s on %s (pos=%d)", execution_id, device_id, length - 1)
        return length - 1

    async def dequeue(self, device_id: str) -> Optional[str]:
        """Pop next execution from device queue."""
        key = self._queue_key(device_id)
        return await self._redis.lpop(key)

    async def peek(self, device_id: str) -> Optional[str]:
        """Look at next execution without removing."""
        key = self._queue_key(device_id)
        items = await self._redis.lrange(key, 0, 0)
        return items[0] if items else None

    async def queue_length(self, device_id: str) -> int:
        key = self._queue_key(device_id)
        return await self._redis.llen(key)

    async def get_queue(self, device_id: str) -> list[str]:
        key = self._queue_key(device_id)
        return await self._redis.lrange(key, 0, -1)

    async def remove(self, device_id: str, execution_id: str):
        key = self._queue_key(device_id)
        await self._redis.lrem(key, 1, execution_id)


scheduler = Scheduler()

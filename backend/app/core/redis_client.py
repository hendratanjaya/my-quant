"""Redis client singletons — sync for Celery/emitter, async for SSE endpoints."""

from __future__ import annotations

import redis
import redis.asyncio as aioredis

from app.core.settings import settings

_sync_client: redis.Redis | None = None
_async_client: aioredis.Redis | None = None


def get_redis() -> redis.Redis:
    global _sync_client
    if _sync_client is None:
        _sync_client = redis.Redis.from_url(settings.redis_url, decode_responses=False)
    return _sync_client


def get_async_redis() -> aioredis.Redis:
    global _async_client
    if _async_client is None:
        _async_client = aioredis.from_url(settings.redis_url, decode_responses=False)
    return _async_client

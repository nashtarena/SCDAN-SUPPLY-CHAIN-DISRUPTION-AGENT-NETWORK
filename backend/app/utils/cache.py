import json
from typing import Any

import redis.asyncio as redis

from app.core.config import settings
from app.core.logging import logger

_redis_client: redis.Redis | None = None


def get_redis() -> redis.Redis:
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
    return _redis_client


async def cache_get_json(key: str) -> Any | None:
    """Returns the cached value (already parsed from JSON), or None on miss/error."""
    try:
        client = get_redis()
        raw = await client.get(key)
        if raw is None:
            return None
        return json.loads(raw)
    except Exception as exc:
        # Cache must never break the pipeline. Treat any Redis error as a miss.
        logger.warning(f"Cache GET failed for key={key}: {exc}")
        return None


async def cache_set_json(key: str, value: Any, ttl_seconds: int | None = None) -> None:
    ttl = ttl_seconds or settings.CACHE_TTL_SECONDS
    try:
        client = get_redis()
        await client.set(key, json.dumps(value, default=str), ex=ttl)
    except Exception as exc:
        logger.warning(f"Cache SET failed for key={key}: {exc}")
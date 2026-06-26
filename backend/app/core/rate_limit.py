"""Redis connection and rate limiting placeholder."""

import redis.asyncio as redis

from app.config import get_settings

settings = get_settings()

redis_client: redis.Redis | None = None


async def init_redis() -> None:
    global redis_client
    try:
        redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
        await redis_client.ping()
    except Exception:
        redis_client = None


async def close_redis() -> None:
    global redis_client
    if redis_client:
        await redis_client.close()
        redis_client = None


async def check_rate_limit(key: str) -> bool:
    """Returns True if within limit, False if exceeded."""
    if redis_client is None:
        return True  # Degrade gracefully when Redis unavailable
    count = await redis_client.incr(key)
    if count == 1:
        await redis_client.expire(key, 60)
    return count <= settings.RATE_LIMIT_PER_MINUTE

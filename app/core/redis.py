from redis.asyncio import Redis

from app.core.config import Settings


def create_redis(settings: Settings) -> Redis:
    # decode_responses=True -> str instead of bytes. Connection is lazy.
    return Redis.from_url(str(settings.redis_url), decode_responses=True)

"""Health checks. Business logic only: no HTTP concerns here.

(No repository.py/models.py: this module owns no tables. Modules only get the
layers they need; the "avoid over-engineering" rule from the brief.)
"""

import asyncio
import logging
import time
from collections.abc import Awaitable, Callable

from redis.asyncio import Redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.health.schemas import ComponentStatus, ReadinessResponse

logger = logging.getLogger(__name__)

CHECK_TIMEOUT_SECONDS = 2.0


async def _timed(check: Callable[[], Awaitable[object]]) -> ComponentStatus:
    start = time.perf_counter()
    try:
        await asyncio.wait_for(check(), timeout=CHECK_TIMEOUT_SECONDS)
    except Exception as exc:  # any failure means "down"; never let it escape
        logger.warning("Health check failed: %s", type(exc).__name__)
        # Only the exception TYPE is exposed: messages may contain hostnames/credentials.
        return ComponentStatus(status="down", error=type(exc).__name__)
    return ComponentStatus(status="up", latency_ms=round((time.perf_counter() - start) * 1000, 2))


async def check_database(session: AsyncSession) -> ComponentStatus:
    return await _timed(lambda: session.execute(text("SELECT 1")))


async def check_redis(redis: Redis) -> ComponentStatus:
    return await _timed(lambda: redis.ping())


async def readiness(session: AsyncSession, redis: Redis) -> ReadinessResponse:
    # Independent checks run concurrently: total time = slowest, not the sum.
    database, cache = await asyncio.gather(check_database(session), check_redis(redis))
    components = {"database": database, "redis": cache}
    all_up = all(c.status == "up" for c in components.values())
    return ReadinessResponse(status="ready" if all_up else "degraded", components=components)

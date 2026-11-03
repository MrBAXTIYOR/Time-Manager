"""FastAPI dependencies shared by all modules.

Resources live on `app.state` (created in the lifespan). Dependencies hand them
to endpoints, so tests can swap any of them with `app.dependency_overrides`.
"""

from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends, Request
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings


def get_app_settings(request: Request) -> Settings:
    settings: Settings = request.app.state.settings
    return settings


async def get_db_session(request: Request) -> AsyncIterator[AsyncSession]:
    """One session per request.

    Transaction policy: the SERVICE layer calls `await session.commit()`.
    We deliberately do NOT auto-commit here: code after `yield` runs after the
    response is sent (FastAPI >= 0.118), so a failing commit could no longer be
    reported to the client. Leaving the `async with` block closes the session
    and rolls back anything uncommitted, which is the safe default.
    """
    async with request.app.state.session_factory() as session:
        yield session


def get_redis(request: Request) -> Redis:
    redis: Redis = request.app.state.redis
    return redis


SettingsDep = Annotated[Settings, Depends(get_app_settings)]
DbSession = Annotated[AsyncSession, Depends(get_db_session)]
RedisDep = Annotated[Redis, Depends(get_redis)]

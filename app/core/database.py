"""Async engine / session factory.

No module-level globals: the engine is created in the application lifespan and
stored on `app.state`. That makes tests able to build an app against a
different database, and makes startup/shutdown explicit.
"""

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import Settings


def create_engine(settings: Settings) -> AsyncEngine:
    return create_async_engine(
        settings.database_url,
        echo=settings.db_echo,
        pool_size=settings.db_pool_size,
        max_overflow=settings.db_max_overflow,
        pool_recycle=settings.db_pool_recycle_seconds,
        pool_pre_ping=True,  # transparently replace connections MySQL has dropped
    )


def create_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(
        engine,
        expire_on_commit=False,  # async: lazy-loading expired attributes would fail
        autoflush=False,  # explicit flushes -> predictable SQL in async code
    )

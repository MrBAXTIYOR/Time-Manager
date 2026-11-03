from collections.abc import AsyncIterator

import pytest
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.core.base import Base
from app.core.config import Settings
from app.core.database import create_engine, create_session_factory
from app.core.redis import create_redis
from tests.models import Widget

pytestmark = pytest.mark.integration


def pytest_collection_modifyitems(items):
    for item in items:
        if "tests/integration" in str(item.fspath).replace("\\", "/"):
            item.add_marker(pytest.mark.integration)


@pytest.fixture(scope="session")
async def engine(integration_settings: Settings) -> AsyncIterator[AsyncEngine]:
    eng = create_engine(integration_settings)
    async with eng.begin() as conn:
        await conn.run_sync(Widget.__table__.drop, checkfirst=True)
        await conn.run_sync(Widget.__table__.create)
    yield eng
    async with eng.begin() as conn:
        await conn.run_sync(Widget.__table__.drop, checkfirst=True)
    await eng.dispose()


@pytest.fixture
async def session(engine: AsyncEngine) -> AsyncIterator[AsyncSession]:
    factory: async_sessionmaker[AsyncSession] = create_session_factory(engine)
    async with factory() as s:
        yield s
        await s.rollback()
    async with engine.begin() as conn:  # keep tests independent
        await conn.execute(Widget.__table__.delete())


@pytest.fixture(scope="session")
async def redis(integration_settings: Settings) -> AsyncIterator[Redis]:
    r = create_redis(integration_settings)
    yield r
    await r.aclose()


assert Base  # imported so metadata is populated

import os
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.core.config import Settings
from app.main import create_app


def make_settings(**overrides: object) -> Settings:
    """Settings that ignore any local .env file: unit tests must be hermetic."""
    values: dict[str, object] = {
        "mysql_user": "test_user",
        "mysql_password": "test_password",
        "mysql_database": "test_db",
        "app_env": "testing",
        "log_level": "WARNING",
    }
    values.update(overrides)
    return Settings(_env_file=None, **values)  # type: ignore[arg-type]


@pytest.fixture
def settings() -> Settings:
    return make_settings()


@asynccontextmanager
async def run_app(app: FastAPI, *, raise_app_exceptions: bool = True) -> AsyncIterator[AsyncClient]:
    """httpx does not run ASGI lifespan events, so we run them ourselves."""
    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app, raise_app_exceptions=raise_app_exceptions)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            yield client


@pytest.fixture
def app_runner() -> Callable[..., object]:
    return run_app


@pytest.fixture
async def client(settings: Settings) -> AsyncIterator[AsyncClient]:
    async with run_app(create_app(settings)) as c:
        yield c


# ---------- integration fixtures (real MySQL + Redis) ----------


@pytest.fixture(scope="session")
def integration_settings() -> Settings:
    """Reads the real environment/.env but ALWAYS targets the test database,
    so a test run can never touch development data."""
    return Settings(mysql_database=os.getenv("TEST_MYSQL_DATABASE", "tms_test"))  # type: ignore[call-arg]

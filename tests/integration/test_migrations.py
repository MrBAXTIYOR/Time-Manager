"""Runs the real Alembic CLI against the test database."""

import os
import subprocess
import sys

import pytest
from sqlalchemy import text

from tests.models import Widget


def _alembic(*args: str, settings) -> subprocess.CompletedProcess[str]:
    env = {**os.environ, "MYSQL_DATABASE": settings.mysql_database}
    return subprocess.run(
        [sys.executable, "-m", "alembic", *args],
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )


@pytest.fixture
async def migration_db(engine):
    """Empty database for the migration tests: remove the test-only table (it is
    not part of the app metadata) and any alembic bookkeeping, then restore."""
    async with engine.begin() as conn:
        await conn.run_sync(Widget.__table__.drop, checkfirst=True)
        await conn.execute(text("DROP TABLE IF EXISTS alembic_version"))
    yield
    async with engine.begin() as conn:
        await conn.execute(text("DROP TABLE IF EXISTS alembic_version"))
        await conn.run_sync(Widget.__table__.create, checkfirst=True)


async def test_upgrade_and_downgrade_cycle(integration_settings, engine, migration_db):
    up = _alembic("upgrade", "head", settings=integration_settings)
    assert up.returncode == 0, up.stderr
    async with engine.connect() as conn:
        version = (await conn.execute(text("SELECT version_num FROM alembic_version"))).scalar_one()
    assert version

    down = _alembic("downgrade", "base", settings=integration_settings)
    assert down.returncode == 0, down.stderr


async def test_models_and_migrations_are_in_sync(integration_settings, migration_db):
    """`alembic check` exits non-zero when models differ from migrations,
    i.e. someone changed a model and forgot to generate a migration."""
    assert _alembic("upgrade", "head", settings=integration_settings).returncode == 0
    check = _alembic("check", settings=integration_settings)
    assert check.returncode == 0, check.stdout + check.stderr

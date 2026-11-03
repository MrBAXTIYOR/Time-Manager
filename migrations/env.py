"""Alembic environment (async).

Alembic itself is synchronous, so for an async driver we open an async
connection and hand Alembic a sync view of it with `run_sync`.
"""

import asyncio

from alembic import context
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config import get_settings
from app.core.registry import metadata  # also imports every model

target_metadata = metadata
settings = get_settings()


def run_migrations_offline() -> None:
    """Emit SQL to stdout without connecting (`alembic upgrade head --sql`)."""
    context.configure(
        url=settings.database_url.render_as_string(hide_password=False),
        target_metadata=target_metadata,
        literal_binds=True,
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def _do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,  # detect column type changes
        compare_server_default=True,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    engine = create_async_engine(settings.database_url)
    async with engine.connect() as connection:
        await connection.run_sync(_do_run_migrations)
    await engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())

import uuid
from datetime import UTC, datetime, timedelta, timezone

import pytest
from sqlalchemy import select, text

from tests.models import Widget


async def test_connects_and_session_timezone_is_utc(session):
    assert (await session.execute(text("SELECT 1"))).scalar_one() == 1
    # Our columns store UTC explicitly, but a UTC server session avoids surprises
    # from functions such as NOW().
    tz = (await session.execute(text("SELECT @@session.time_zone"))).scalar_one()
    assert tz in ("+00:00", "UTC", "SYSTEM")


async def test_insert_roundtrip_with_uuid7_and_timestamps(session):
    w = Widget(name="first")
    session.add(w)
    await session.commit()

    assert isinstance(w.id, uuid.UUID) and w.id.version == 7
    loaded = (await session.execute(select(Widget).where(Widget.id == w.id))).scalar_one()
    assert loaded.name == "first"
    assert loaded.created_at.tzinfo is UTC
    assert abs(loaded.created_at - datetime.now(UTC)) < timedelta(seconds=5)
    assert loaded.deleted_at is None


async def test_id_is_stored_as_16_raw_bytes(session):
    w = Widget(name="raw")
    session.add(w)
    await session.commit()
    length, hexval = (
        await session.execute(text("SELECT LENGTH(id), HEX(id) FROM _test_widgets"))
    ).one()
    assert length == 16
    assert hexval.lower() == w.id.hex


async def test_column_is_binary16_and_datetime6(session):
    rows = (
        await session.execute(
            text(
                "SELECT COLUMN_NAME, COLUMN_TYPE FROM information_schema.COLUMNS "
                "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = '_test_widgets'"
            )
        )
    ).all()
    types = {name.lower(): ctype.lower() for name, ctype in rows}
    assert types["id"] == "binary(16)"
    assert types["created_at"] == "datetime(6)"


async def test_primary_key_order_equals_creation_order(session):
    widgets = [Widget(name=f"w{i}") for i in range(50)]
    session.add_all(widgets)
    await session.commit()
    ordered = (await session.execute(select(Widget.name).order_by(Widget.id))).scalars().all()
    assert ordered == [f"w{i}" for i in range(50)]


async def test_timezone_aware_input_is_normalised_to_utc(session):
    tashkent = timezone(timedelta(hours=5))
    w = Widget(name="tz")
    w.deleted_at = datetime(2026, 6, 1, 12, 0, 0, 123456, tzinfo=tashkent)
    session.add(w)
    await session.commit()
    session.expire_all()
    got = (await session.execute(select(Widget.deleted_at))).scalar_one()
    assert got == datetime(2026, 6, 1, 7, 0, 0, 123456, tzinfo=UTC)  # microseconds kept


async def test_naive_datetime_is_rejected_at_the_database_boundary(session):
    w = Widget(name="naive")
    w.deleted_at = datetime(2026, 1, 1, 12, 0)
    session.add(w)
    with pytest.raises(Exception, match="Naive"):
        await session.commit()


async def test_updated_at_changes_on_update(session):
    w = Widget(name="a")
    session.add(w)
    await session.commit()
    first = w.updated_at
    w.name = "b"
    await session.commit()
    assert w.updated_at > first and w.created_at < w.updated_at


async def test_uncommitted_work_is_rolled_back_when_session_closes(engine):
    from app.core.database import create_session_factory

    factory = create_session_factory(engine)
    async with factory() as s:
        s.add(Widget(name="ghost"))
        await s.flush()  # sent to DB but never committed
    async with factory() as s2:
        assert (await s2.execute(select(Widget).where(Widget.name == "ghost"))).first() is None

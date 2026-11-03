import uuid
from datetime import UTC, datetime, timedelta, timezone

import pytest
from sqlalchemy.dialects import mysql

from app.core.types import UTCDateTime, UUIDBinary

D = mysql.dialect()


def test_uuid_binary_round_trip():
    t, u = UUIDBinary(), uuid.uuid4()
    raw = t.process_bind_param(u, D)
    assert isinstance(raw, bytes) and len(raw) == 16
    assert t.process_result_value(raw, D) == u


def test_uuid_binary_accepts_string_and_none():
    t, u = UUIDBinary(), uuid.uuid4()
    assert t.process_bind_param(str(u), D) == u.bytes
    assert t.process_bind_param(None, D) is None
    assert t.process_result_value(None, D) is None


def test_uuid_binary_rejects_other_types():
    with pytest.raises(TypeError):
        UUIDBinary().process_bind_param(12345, D)


def test_utc_datetime_rejects_naive():
    with pytest.raises(ValueError, match="Naive"):
        UTCDateTime().process_bind_param(datetime(2026, 1, 1, 12, 0), D)


def test_utc_datetime_converts_offsets_to_utc():
    tashkent = timezone(timedelta(hours=5))
    stored = UTCDateTime().process_bind_param(datetime(2026, 1, 1, 12, 0, tzinfo=tashkent), D)
    assert stored == datetime(2026, 1, 1, 7, 0)  # naive, but in UTC
    assert stored.tzinfo is None


def test_utc_datetime_returns_aware_utc():
    loaded = UTCDateTime().process_result_value(datetime(2026, 1, 1, 7, 0), D)
    assert loaded.tzinfo is UTC


def test_utc_datetime_uses_microsecond_precision_on_mysql():
    impl = UTCDateTime().load_dialect_impl(D)
    assert impl.fsp == 6

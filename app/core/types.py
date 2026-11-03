"""Custom SQLAlchemy column types shared by every module."""

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import BINARY, DateTime
from sqlalchemy.dialects import mysql
from sqlalchemy.engine import Dialect
from sqlalchemy.types import TypeDecorator, TypeEngine


class UUIDBinary(TypeDecorator[uuid.UUID]):
    """Python uuid.UUID <-> MySQL BINARY(16).

    16 bytes instead of CHAR(36): ~55% smaller keys and indexes, and faster
    comparisons. The trade-off is that raw rows are unreadable in the mysql
    CLI; use HEX(id) or BIN_TO_UUID(id) when debugging.
    """

    impl = BINARY(16)
    cache_ok = True

    def process_bind_param(self, value: Any, dialect: Dialect) -> bytes | None:
        if value is None:
            return None
        if isinstance(value, str):
            value = uuid.UUID(value)
        if not isinstance(value, uuid.UUID):
            raise TypeError(f"UUIDBinary expects uuid.UUID, got {type(value).__name__}")
        return value.bytes

    def process_result_value(self, value: Any, dialect: Dialect) -> uuid.UUID | None:
        return None if value is None else uuid.UUID(bytes=bytes(value))


class UTCDateTime(TypeDecorator[datetime]):
    """Timezone-aware UTC datetimes on top of MySQL DATETIME(6).

    MySQL DATETIME has no timezone, so a naive value is ambiguous. This type
    enforces the project rule "store UTC, always":
      * on write: naive datetimes are REJECTED (a bug in the caller, not
        something to guess about); aware ones are converted to UTC.
      * on read: values come back as aware datetimes with tzinfo=UTC.
    DATETIME(6) keeps microseconds.
    """

    impl = DateTime
    cache_ok = True

    def load_dialect_impl(self, dialect: Dialect) -> TypeEngine[Any]:
        if dialect.name == "mysql":
            return dialect.type_descriptor(mysql.DATETIME(fsp=6))
        return dialect.type_descriptor(DateTime())

    def process_bind_param(self, value: Any, dialect: Dialect) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            raise ValueError("Naive datetime rejected: use timezone-aware datetimes (UTC).")
        naive_utc: datetime = value.astimezone(UTC).replace(tzinfo=None)
        return naive_utc

    def process_result_value(self, value: Any, dialect: Dialect) -> datetime | None:
        if value is None:
            return None
        result: datetime = value.replace(tzinfo=UTC)
        return result

"""Declarative base and reusable column mixins.

Every business module's models.py inherits from these, so primary keys,
timestamps and soft delete behave identically everywhere.
"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.core.types import UTCDateTime, UUIDBinary
from app.core.uuid7 import uuid7

# Explicit constraint naming. Without it MySQL/SQLAlchemy generate unstable
# names and Alembic cannot reliably drop or alter constraints later.
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


def utcnow() -> datetime:
    return datetime.now(UTC)


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)


class UUIDPrimaryKeyMixin:
    # The id is generated in Python (not by the DB) so the object has its
    # identity before flush: handy for building related rows and events.
    id: Mapped[uuid.UUID] = mapped_column(UUIDBinary, primary_key=True, default=uuid7)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        UTCDateTime, default=utcnow, onupdate=utcnow, nullable=False
    )


class SoftDeleteMixin:
    """Rows are flagged, not removed (see roadmap: recovery + activity logs).

    Repositories must filter `deleted_at IS NULL` by default; that logic lives
    in the shared repository helpers added with the first real module.
    """

    deleted_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True, default=None)

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None

    def soft_delete(self) -> None:
        self.deleted_at = utcnow()

    def restore(self) -> None:
        self.deleted_at = None


class BaseModel(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Abstract parent for most entities: UUIDv7 id + created_at/updated_at.
    Add SoftDeleteMixin explicitly where deletion must be recoverable."""

    __abstract__ = True

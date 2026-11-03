import uuid
from datetime import UTC

from app.core.base import NAMING_CONVENTION, Base
from tests.models import Widget


def test_metadata_uses_naming_convention():
    assert Base.metadata.naming_convention == NAMING_CONVENTION


def test_soft_delete_and_restore():
    w = Widget(name="x")
    assert not w.is_deleted
    w.soft_delete()
    assert w.is_deleted and w.deleted_at.tzinfo is UTC
    w.restore()
    assert not w.is_deleted


def test_columns_defined_by_mixins():
    cols = Widget.__table__.c
    assert {"id", "created_at", "updated_at", "deleted_at", "name"} <= set(cols.keys())
    assert cols.id.primary_key
    assert cols.deleted_at.nullable and not cols.created_at.nullable


def test_id_default_generates_uuid7():
    default = Widget.__table__.c.id.default
    value = default.arg(None)  # SQLAlchemy wraps callables to take a context arg
    assert isinstance(value, uuid.UUID) and value.version == 7

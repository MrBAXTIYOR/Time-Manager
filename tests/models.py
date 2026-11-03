"""Throwaway model used only by tests to exercise BaseModel + mixins."""

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base import BaseModel, SoftDeleteMixin


class Widget(SoftDeleteMixin, BaseModel):
    __tablename__ = "_test_widgets"
    name: Mapped[str] = mapped_column(String(50))

"""baseline (empty schema)

Revision ID: a693d4f0971e
Revises:
Create Date: 2026-11-03 11:08:17.412478
"""

from collections.abc import Sequence

revision: str = "a693d4f0971e"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass

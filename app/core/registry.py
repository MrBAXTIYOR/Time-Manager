"""Imports every module's models so they register on Base.metadata.

Alembic autogenerate only sees tables whose model classes have been imported.
Each new module adds ONE import line here (no models exist yet in Step 1).
"""

from app.core.base import Base

# from app.modules.users import models as _users  # noqa: F401   <- added in Step 2

metadata = Base.metadata

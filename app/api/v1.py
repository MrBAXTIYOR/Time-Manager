"""Version 1 API router. Each step mounts its module router here, e.g.

    api_router.include_router(auth_router, prefix="/auth", tags=["auth"])

Infrastructure endpoints (/health) live outside the version prefix on purpose:
probes must keep working when the API version changes.
"""

from fastapi import APIRouter

api_router = APIRouter()

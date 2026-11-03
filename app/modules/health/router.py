from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.core.dependencies import DbSession, RedisDep, SettingsDep
from app.modules.health import service
from app.modules.health.schemas import LivenessResponse, ReadinessResponse

router = APIRouter(tags=["health"])


@router.get(
    "/health",
    response_model=LivenessResponse,
    summary="Liveness probe",
    description="Is the process running? Touches no dependencies, so it is always fast. "
    "Orchestrators use it to decide whether to RESTART the container.",
)
async def liveness(settings: SettingsDep) -> LivenessResponse:
    return LivenessResponse(
        app=settings.app_name, version=settings.app_version, environment=settings.app_env
    )


@router.get(
    "/health/ready",
    response_model=ReadinessResponse,
    responses={503: {"model": ReadinessResponse, "description": "A dependency is down."}},
    summary="Readiness probe",
    description="Can the app serve traffic? Verifies MySQL and Redis. Load balancers use it "
    "to decide whether to ROUTE traffic to this instance.",
)
async def readiness(session: DbSession, redis: RedisDep) -> JSONResponse:
    result = await service.readiness(session, redis)
    return JSONResponse(
        status_code=200 if result.status == "ready" else 503,
        content=result.model_dump(mode="json"),
    )

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.v1 import api_router
from app.core.config import Settings, get_settings
from app.core.database import create_engine, create_session_factory
from app.core.exceptions import register_exception_handlers
from app.core.logging import configure_logging
from app.core.middleware import RequestContextMiddleware
from app.core.redis import create_redis
from app.modules.health.router import router as health_router

logger = logging.getLogger(__name__)


def create_app(settings: Settings | None = None) -> FastAPI:
    """Application factory: tests can build an app with different settings."""
    settings = settings or get_settings()
    configure_logging(settings.log_level, json_logs=settings.is_production)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        # Engine and Redis clients connect lazily, so startup does not fail
        # when a dependency is briefly down; /health/ready reports it instead.
        engine = create_engine(settings)
        redis = create_redis(settings)
        app.state.settings = settings
        app.state.engine = engine
        app.state.session_factory = create_session_factory(engine)
        app.state.redis = redis
        logger.info("Application started", extra={"environment": settings.app_env})
        try:
            yield
        finally:
            await redis.aclose()
            await engine.dispose()
            logger.info("Application stopped")

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="Google Calendar-inspired time management API.",
        lifespan=lifespan,
        # Do not publish the API schema in production by default.
        docs_url=None if settings.is_production else "/docs",
        redoc_url=None if settings.is_production else "/redoc",
        openapi_url=None if settings.is_production else "/openapi.json",
    )
    app.add_middleware(RequestContextMiddleware)
    register_exception_handlers(app)
    app.include_router(health_router)
    app.include_router(api_router, prefix=settings.api_v1_prefix)
    return app

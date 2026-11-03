"""Domain exceptions + one place that turns every error into the same JSON shape:

    {"error": {"code": "...", "message": "...", "details": ..., "request_id": "..."}}

Services raise AppError subclasses (they know nothing about HTTP responses);
the handlers registered below translate them. Clients can rely on `code`
(stable, machine-readable) instead of parsing `message`.
"""

import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)


class AppError(Exception):
    status_code: int = 500
    code: str = "internal_error"
    message: str = "Internal server error."

    def __init__(self, message: str | None = None, *, details: Any = None) -> None:
        self.message = message or self.message
        self.details = details
        super().__init__(self.message)


class NotFoundError(AppError):
    status_code, code, message = 404, "not_found", "Resource not found."


class ConflictError(AppError):
    status_code, code, message = 409, "conflict", "Resource conflict."


class UnauthorizedError(AppError):
    status_code, code, message = 401, "unauthorized", "Authentication required."


class ForbiddenError(AppError):
    status_code, code, message = 403, "forbidden", "You do not have permission."


class BusinessRuleError(AppError):
    status_code, code, message = 422, "business_rule_violation", "Business rule violated."


class ServiceUnavailableError(AppError):
    status_code, code, message = 503, "service_unavailable", "Service unavailable."


def _body(request: Request, code: str, message: str, details: Any = None) -> dict[str, Any]:
    return {
        "error": {
            "code": code,
            "message": message,
            "details": details,
            # Read from request.state (set by the middleware), not a contextvar:
            # the 500 handler runs outside our middleware, after contextvars reset.
            "request_id": getattr(request.state, "request_id", None),
        }
    }


async def _app_error_handler(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, AppError)
    return JSONResponse(
        status_code=exc.status_code,
        content=jsonable_encoder(_body(request, exc.code, exc.message, exc.details)),
    )


async def _validation_error_handler(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, RequestValidationError)
    details = [
        {"field": ".".join(str(p) for p in err["loc"]), "message": err["msg"], "type": err["type"]}
        for err in exc.errors()
    ]
    return JSONResponse(
        status_code=422,
        content=jsonable_encoder(
            _body(request, "validation_error", "Request validation failed.", details)
        ),
    )


async def _http_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, StarletteHTTPException)
    code = {404: "not_found", 405: "method_not_allowed"}.get(exc.status_code, "http_error")
    return JSONResponse(
        status_code=exc.status_code,
        content=_body(request, code, str(exc.detail)),
        headers=getattr(exc, "headers", None),
    )


async def _unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
    # Full traceback goes to the logs; the client gets nothing internal.
    logger.exception("Unhandled exception on %s %s", request.method, request.url.path)
    request_id = getattr(request.state, "request_id", None)
    # This response is built by Starlette's outermost ServerErrorMiddleware, i.e.
    # OUTSIDE our request-context middleware, so the header must be set here.
    return JSONResponse(
        status_code=500,
        content=_body(request, "internal_error", "Internal server error."),
        headers={"X-Request-ID": request_id} if request_id else None,
    )


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AppError, _app_error_handler)
    app.add_exception_handler(RequestValidationError, _validation_error_handler)
    app.add_exception_handler(StarletteHTTPException, _http_exception_handler)
    app.add_exception_handler(Exception, _unhandled_error_handler)

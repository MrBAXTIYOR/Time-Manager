"""Exception envelope + request-id middleware + health endpoints, with NO infrastructure."""

from pydantic import BaseModel

from app.core.dependencies import get_db_session, get_redis
from app.core.exceptions import ConflictError, NotFoundError
from app.main import create_app
from tests.conftest import make_settings, run_app


class Payload(BaseModel):
    count: int


def _app_with_test_routes():
    app = create_app(make_settings())

    @app.get("/_t/not-found")
    async def _nf():
        raise NotFoundError("Calendar not found.", details={"id": "42"})

    @app.get("/_t/conflict")
    async def _cf():
        raise ConflictError()

    @app.get("/_t/boom")
    async def _boom():
        raise RuntimeError("secret internal detail")

    @app.post("/_t/validate")
    async def _val(p: Payload):
        return p

    return app


async def test_app_error_uses_standard_envelope():
    async with run_app(_app_with_test_routes()) as c:
        r = await c.get("/_t/not-found", headers={"X-Request-ID": "req-abcdef12"})
    assert r.status_code == 404
    assert r.json() == {
        "error": {
            "code": "not_found",
            "message": "Calendar not found.",
            "details": {"id": "42"},
            "request_id": "req-abcdef12",
        }
    }


async def test_default_message_and_status():
    async with run_app(_app_with_test_routes()) as c:
        r = await c.get("/_t/conflict")
    assert r.status_code == 409 and r.json()["error"]["code"] == "conflict"


async def test_validation_errors_are_flattened():
    async with run_app(_app_with_test_routes()) as c:
        r = await c.post("/_t/validate", json={"count": "not-a-number"})
    body = r.json()["error"]
    assert r.status_code == 422 and body["code"] == "validation_error"
    assert body["details"][0]["field"] == "body.count"


async def test_unhandled_error_hides_internals_but_keeps_request_id():
    async with run_app(_app_with_test_routes(), raise_app_exceptions=False) as c:
        r = await c.get("/_t/boom")
    body = r.json()["error"]
    assert r.status_code == 500
    assert "secret" not in r.text
    assert body["code"] == "internal_error" and body["request_id"] == r.headers["X-Request-ID"]


async def test_unknown_route_uses_envelope():
    async with run_app(create_app(make_settings())) as c:
        r = await c.get("/nope")
    assert r.status_code == 404 and r.json()["error"]["code"] == "not_found"


async def test_request_id_generated_when_absent():
    async with run_app(create_app(make_settings())) as c:
        r1, r2 = await c.get("/health"), await c.get("/health")
    assert len(r1.headers["X-Request-ID"]) == 32
    assert r1.headers["X-Request-ID"] != r2.headers["X-Request-ID"]


async def test_valid_client_request_id_is_propagated():
    async with run_app(create_app(make_settings())) as c:
        r = await c.get("/health", headers={"X-Request-ID": "client-id-12345"})
    assert r.headers["X-Request-ID"] == "client-id-12345"


async def test_malicious_request_id_is_replaced():
    async with run_app(create_app(make_settings())) as c:
        r = await c.get("/health", headers={"X-Request-ID": "bad id\twith spaces"})
    assert r.headers["X-Request-ID"] != "bad id\twith spaces"
    assert len(r.headers["X-Request-ID"]) == 32


async def test_liveness():
    async with run_app(create_app(make_settings())) as c:
        r = await c.get("/health")
    assert r.status_code == 200
    assert r.json() == {
        "status": "ok",
        "app": "Time Management System",
        "version": "0.1.0",
        "environment": "testing",
    }


class _OkSession:
    async def execute(self, *_a, **_k):
        return None


class _BadSession:
    async def execute(self, *_a, **_k):
        raise ConnectionError("mysql password=hunter2 unreachable")


class _OkRedis:
    async def ping(self):
        return True


class _BadRedis:
    async def ping(self):
        raise ConnectionError("redis down")


async def _ready(session, redis):
    app = create_app(make_settings())
    app.dependency_overrides[get_db_session] = lambda: session
    app.dependency_overrides[get_redis] = lambda: redis
    async with run_app(app) as c:
        return await c.get("/health/ready")


async def test_ready_when_all_dependencies_up():
    r = await _ready(_OkSession(), _OkRedis())
    assert r.status_code == 200 and r.json()["status"] == "ready"
    assert r.json()["components"]["database"]["status"] == "up"


async def test_degraded_when_database_down_and_error_not_leaked():
    r = await _ready(_BadSession(), _OkRedis())
    body = r.json()
    assert r.status_code == 503 and body["status"] == "degraded"
    assert body["components"]["database"] == {
        "status": "down",
        "latency_ms": None,
        "error": "ConnectionError",
    }
    assert body["components"]["redis"]["status"] == "up"
    assert "hunter2" not in r.text


async def test_degraded_when_redis_down():
    r = await _ready(_OkSession(), _BadRedis())
    assert r.status_code == 503 and r.json()["components"]["redis"]["status"] == "down"


async def test_docs_enabled_in_development_disabled_in_production():
    async with run_app(create_app(make_settings(app_env="development"))) as c:
        assert (await c.get("/docs")).status_code == 200
        assert "/health" in (await c.get("/openapi.json")).json()["paths"]
    async with run_app(create_app(make_settings(app_env="production"))) as c:
        assert (await c.get("/docs")).status_code == 404
        assert (await c.get("/openapi.json")).status_code == 404


async def test_middleware_passes_non_http_scopes_through():
    from app.core.middleware import RequestContextMiddleware

    seen = []

    async def inner(scope, receive, send):
        seen.append(scope["type"])

    await RequestContextMiddleware(inner)({"type": "lifespan"}, None, None)
    assert seen == ["lifespan"]

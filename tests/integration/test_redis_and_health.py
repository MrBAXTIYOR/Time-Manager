from app.core.config import Settings
from app.main import create_app
from tests.conftest import run_app


async def test_redis_roundtrip(redis):
    assert await redis.ping() is True
    await redis.set("tms:test:key", "value", ex=10)
    assert await redis.get("tms:test:key") == "value"  # decode_responses=True -> str
    await redis.delete("tms:test:key")


async def test_readiness_with_real_dependencies(integration_settings: Settings):
    async with run_app(create_app(integration_settings)) as c:
        r = await c.get("/health/ready")
    body = r.json()
    assert r.status_code == 200, body
    assert body["status"] == "ready"
    assert body["components"]["database"]["latency_ms"] is not None
    assert body["components"]["redis"]["status"] == "up"


async def test_readiness_reports_real_outage_without_crashing(integration_settings: Settings):
    broken = integration_settings.model_copy(update={"redis_url": "redis://localhost:1/0"})
    async with run_app(create_app(broken)) as c:
        r = await c.get("/health/ready")
    body = r.json()
    assert r.status_code == 503
    assert body["components"]["redis"]["status"] == "down"
    assert body["components"]["database"]["status"] == "up"  # failures are isolated

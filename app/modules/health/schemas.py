from typing import Literal

from pydantic import BaseModel, Field


class LivenessResponse(BaseModel):
    status: Literal["ok"] = "ok"
    app: str
    version: str
    environment: str


class ComponentStatus(BaseModel):
    status: Literal["up", "down"]
    latency_ms: float | None = None
    error: str | None = Field(default=None, description="Short reason when status is 'down'.")


class ReadinessResponse(BaseModel):
    status: Literal["ready", "degraded"]
    components: dict[str, ComponentStatus]

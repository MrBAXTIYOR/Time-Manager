"""Structured logging.

Production: one JSON object per line (what log aggregators such as Loki, ELK or
CloudWatch expect). Development: readable single-line text. In both cases every
record carries the current request_id, so all lines of one request correlate.
"""

import json
import logging
import sys
from contextvars import ContextVar
from datetime import UTC, datetime
from typing import Any

request_id_ctx: ContextVar[str | None] = ContextVar("request_id", default=None)

# Attributes that exist on every LogRecord; anything else came from `extra=`.
_STANDARD_ATTRS = set(vars(logging.LogRecord("", 0, "", 0, "", (), None))) | {
    "message",
    "asctime",
    "request_id",
}


class RequestIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_ctx.get()
        return True


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": getattr(record, "request_id", None),
        }
        payload.update({k: v for k, v in record.__dict__.items() if k not in _STANDARD_ATTRS})
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


def configure_logging(level: str, *, json_logs: bool) -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.addFilter(RequestIdFilter())
    handler.setFormatter(
        JsonFormatter()
        if json_logs
        else logging.Formatter("%(asctime)s %(levelname)-8s [%(request_id)s] %(name)s: %(message)s")
    )
    root = logging.getLogger()
    root.handlers[:] = [handler]  # replace, so calling twice never duplicates output
    root.setLevel(level)
    # uvicorn's own access log is replaced by our middleware's richer line.
    logging.getLogger("uvicorn.access").disabled = True

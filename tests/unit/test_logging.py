import json
import logging

from app.core.logging import JsonFormatter, RequestIdFilter, request_id_ctx


def _record(**extra) -> logging.LogRecord:
    r = logging.LogRecord("t", logging.INFO, __file__, 1, "hello %s", ("world",), None)
    r.__dict__.update(extra)
    return r


def test_json_formatter_outputs_valid_json_with_extras():
    r = _record(status=200)
    RequestIdFilter().filter(r)
    data = json.loads(JsonFormatter().format(r))
    assert data["message"] == "hello world"
    assert data["level"] == "INFO"
    assert data["status"] == 200
    assert "timestamp" in data


def test_request_id_is_attached_from_context():
    token = request_id_ctx.set("abc12345")
    try:
        r = _record()
        RequestIdFilter().filter(r)
        assert json.loads(JsonFormatter().format(r))["request_id"] == "abc12345"
    finally:
        request_id_ctx.reset(token)


def test_exceptions_are_serialised():
    try:
        raise RuntimeError("boom")
    except RuntimeError:
        import sys

        r = _record()
        r.exc_info = sys.exc_info()
    assert "RuntimeError: boom" in json.loads(JsonFormatter().format(r))["exception"]

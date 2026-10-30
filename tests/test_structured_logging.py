
import json
import logging

from backend.structured_logger import JSONFormatter


def test_formatter_produces_valid_json():
    formatter = JSONFormatter()

    record = logging.LogRecord(
        name="faultforge",
        level=logging.INFO,
        pathname=__file__,
        lineno=10,
        msg="Request completed",
        args=(),
        exc_info=None,
    )

    result = json.loads(formatter.format(record))

    assert result["message"] == "Request completed"
    assert result["level"] == "INFO"
    assert result["logger"] == "faultforge"
    assert "timestamp" in result


def test_formatter_includes_request_metadata():
    formatter = JSONFormatter()

    record = logging.LogRecord(
        name="faultforge",
        level=logging.INFO,
        pathname=__file__,
        lineno=20,
        msg="Request completed",
        args=(),
        exc_info=None,
    )

    record.request_id = "test-request-123"
    record.method = "GET"
    record.path = "/api/services"
    record.status_code = 200
    record.duration_ms = 14.52

    result = json.loads(formatter.format(record))

    assert result["request_id"] == "test-request-123"
    assert result["method"] == "GET"
    assert result["path"] == "/api/services"
    assert result["status_code"] == 200
    assert result["duration_ms"] == 14.52


def test_formatter_handles_missing_metadata():
    formatter = JSONFormatter()

    record = logging.LogRecord(
        name="faultforge",
        level=logging.WARNING,
        pathname=__file__,
        lineno=30,
        msg="Cache unavailable",
        args=(),
        exc_info=None,
    )

    result = json.loads(formatter.format(record))

    assert result["level"] == "WARNING"
    assert result["message"] == "Cache unavailable"
    assert "request_id" not in result
    assert "duration_ms" not in result


def test_formatter_includes_exception():
    formatter = JSONFormatter()

    try:
        raise ValueError("Test failure")
    except ValueError:
        import sys
        exception_info = sys.exc_info()

    record = logging.LogRecord(
        name="faultforge",
        level=logging.ERROR,
        pathname=__file__,
        lineno=40,
        msg="Operation failed",
        args=(),
        exc_info=exception_info,
    )

    result = json.loads(formatter.format(record))

    assert result["level"] == "ERROR"
    assert "exception" in result
    assert "ValueError: Test failure" in result["exception"]

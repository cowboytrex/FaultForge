
import sys
import json
import logging
from pathlib import Path

sys.path.insert(
    0,
    str(Path(__file__).resolve().parents[1] / "backend")
)

from structured_logger import JSONFormatter


def test_json_log_format():
    """Logs should be valid JSON."""
    formatter = JSONFormatter()

    record = logging.LogRecord(
        name="faultforge",
        level=logging.WARNING,
        pathname=__file__,
        lineno=1,
        msg="Database connection failed",
        args=(),
        exc_info=None
    )

    output = formatter.format(record)
    data = json.loads(output)

    assert data["level"] == "WARNING"
    assert data["logger"] == "faultforge"
    assert data["message"] == "Database connection failed"
    assert "timestamp" in data


def test_event_type_in_log():
    """Incident logs should include an event type."""
    formatter = JSONFormatter()

    record = logging.LogRecord(
        name="faultforge",
        level=logging.CRITICAL,
        pathname=__file__,
        lineno=1,
        msg="Circuit breaker opened",
        args=(),
        exc_info=None
    )

    record.event_type = "circuit_opened"

    data = json.loads(formatter.format(record))

    assert data["event_type"] == "circuit_opened"
    assert data["level"] == "CRITICAL"


def test_regular_log_without_event_type():
    """Regular logs should not require an event type."""
    formatter = JSONFormatter()

    record = logging.LogRecord(
        name="faultforge",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="Application started",
        args=(),
        exc_info=None
    )

    data = json.loads(formatter.format(record))

    assert data["message"] == "Application started"
    assert "event_type" not in data

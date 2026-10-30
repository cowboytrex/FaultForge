import sys
from pathlib import Path

import pytest

sys.path.insert(
    0,
    str(Path(__file__).resolve().parents[1] / "backend")
)

from event_logger import events, events_lock, log_event, get_events
from circuit_breaker import CircuitBreaker

@pytest.fixture(autouse=True)
def clear_events():
    """Reset event history before and after each test."""
    with events_lock:
        events.clear()
    yield
    with events_lock:
        events.clear()

def test_event_recording():
    log_event("database_failure", "Database unavaliable", "warning")

    recorded = get_events()

    assert len(recorded) == 1
    assert recorded[0]["type"] == "database_failure"
    assert recorded[0]["severity"] == "warning"
    assert "timestamp" in recorded[0]

def test_event_order():
    log_event("first", "First event")
    log_event("second", "Second event")

    recorded = get_events()

    assert len(recorded) == 2
    assert recorded[0]["type"] == "second"
    assert recorded[1]["type"] == "first"


def test_circuit_opens_and_logs_event():
    breaker = CircuitBreaker(failure_threshold=3)

    def failing_database():
        raise ConnectionError("Database unavailable")

    # Simulate three consecutive database failures.
    for _ in range(3):
        with pytest.raises(ConnectionError):
            breaker.call(failing_database)

    # The circuit should now be OPEN.
    assert breaker.state == "OPEN"
    assert breaker.failure_count == 3

    # Check that the expected events were recorded.
    event_types = [event["type"] for event in get_events()]

    assert event_types.count("database_failure") == 3
    assert event_types.count("circuit_opened") == 1



def test_successful_recovery(monkeypatch):
    current_time = [100.0]

    monkeypatch.setattr(
        "circuit_breaker.time.monotonic",
        lambda: current_time[0]
    )

    breaker = CircuitBreaker(
        failure_threshold=1,
        recovery_timeout=10
    )

    def failing_operation():
        raise ConnectionError("Database unavailable")

    with pytest.raises(ConnectionError):
        breaker.call(failing_operation)

    assert breaker.state == "OPEN"

    # Advance simulated time without waiting.
    current_time[0] = 111.0

    result = breaker.call(lambda: "Database restored")

    assert result == "Database restored"
    assert breaker.state == "CLOSED"
    assert breaker.failure_count == 0

    event_types = [event["type"] for event in get_events()]

    assert "recovery_attempt" in event_types
    assert "database_recovered" in event_types

import sys
from pathlib import Path

import pytest
import psycopg

sys.path.insert(
    0,
    str(Path(__file__).resolve().parents[1] / "backend")
)

from circuit_breaker import CircuitBreaker, CircuitOpenError


# Test 1: Circuit breaker starts in CLOSED state
def test_circuit_starts_closed():
    breaker = CircuitBreaker()

    assert breaker.state == "CLOSED"
    assert breaker.failure_count == 0


# Test 2: Circuit opens after three consecutive failures
def test_circuit_opens_after_three_failures():
    breaker = CircuitBreaker(failure_threshold=3)

    def failing_database():
        raise psycopg.OperationalError("Database unavailable")

    for _ in range(3):
        with pytest.raises(psycopg.OperationalError):
            breaker.call(failing_database)

    assert breaker.state == "OPEN"
    assert breaker.failure_count == 3

    # The fourth request should be blocked
    with pytest.raises(CircuitOpenError):
        breaker.call(failing_database)


# Test 3: Successful request resets the failure counter
def test_success_resets_failure_count():
    breaker = CircuitBreaker(failure_threshold=3)

    def failing_database():
        raise ConnectionError("Database unavailable")

    with pytest.raises(ConnectionError):
        breaker.call(failing_database)

    assert breaker.failure_count == 1

    result = breaker.call(lambda: "Database recovered")

    assert result == "Database recovered"
    assert breaker.state == "CLOSED"
    assert breaker.failure_count == 0


# Test 4: Circuit recovers after the timeout
def test_circuit_recovers_after_timeout(monkeypatch):
    breaker = CircuitBreaker(
        failure_threshold=3,
        recovery_timeout=10
    )

    # Simulate time without waiting 10 real seconds
    current_time = [100.0]

    monkeypatch.setattr(
        "circuit_breaker.time.monotonic",
        lambda: current_time[0]
    )

    def failing_database():
        raise psycopg.OperationalError("Database unavailable")

    # Three failures should open the circuit
    for _ in range(3):
        with pytest.raises(psycopg.OperationalError):
            breaker.call(failing_database)

    assert breaker.state == "OPEN"

    # Simulate 11 seconds passing
    current_time[0] += 11

    # The next request tests whether the database recovered
    def recovered_database():
        assert breaker.state == "HALF_OPEN"
        return "Database is back online"

    result = breaker.call(recovered_database)

    assert result == "Database is back online"
    assert breaker.state == "CLOSED"
    assert breaker.failure_count == 0

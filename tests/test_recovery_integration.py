
import sys
from pathlib import Path

sys.path.insert(
    0,
    str(Path(__file__).resolve().parents[1] / "backend")
)

import app as flask_module
import circuit_breaker


def test_complete_failure_recovery_lifecycle(monkeypatch):
    """Test normal operation, outage, fallback, and recovery."""

    breaker = flask_module.db_breaker

    original_state = breaker.state
    original_failure_count = breaker.failure_count
    original_last_failure_time = breaker.last_failure_time

    services = [
        {"id": 1, "name": "Authentication", "status": "active"}
    ]

    cache = {"data": None}
    database = {"available": True}
    clock = {"now": 100.0}

    def fake_database():
        if not database["available"]:
            raise ConnectionError("Simulated PostgreSQL outage")
        return services

    def fake_save_to_cache(data):
        cache["data"] = data

    def fake_get_cached_services():
        return cache["data"]

    monkeypatch.setattr(
        flask_module,
        "get_services_from_db",
        fake_database,
    )
    monkeypatch.setattr(
        flask_module,
        "save_to_cache",
        fake_save_to_cache,
    )
    monkeypatch.setattr(
        flask_module,
        "get_cached_services",
        fake_get_cached_services,
    )
    monkeypatch.setattr(
        circuit_breaker.time,
        "monotonic",
        lambda: clock["now"],
    )

    try:
        breaker.state = "CLOSED"
        breaker.failure_count = 0
        breaker.last_failure_time = None

        with flask_module.app.test_client() as client:

            # 1. Healthy database
            response = client.get("/api/services")

            assert response.status_code == 200
            assert response.get_json()["source"] == "primary"
            assert breaker.state == "CLOSED"

            # 2. Database outage
            database["available"] = False

            for _ in range(breaker.failure_threshold):
                response = client.get("/api/services")

                assert response.status_code == 200
                assert response.get_json()["source"] == "cache"
                assert response.get_json()["stale"] is True

            assert breaker.state == "OPEN"
            assert breaker.failure_count == breaker.failure_threshold

            # 3. Requests are blocked while OPEN
            response = client.get("/api/services")

            assert response.status_code == 200
            assert response.get_json()["source"] == "cache"
            assert breaker.state == "OPEN"
            assert breaker.failure_count == breaker.failure_threshold

            # 4. Advance clock beyond recovery timeout
            clock["now"] += breaker.recovery_timeout + 1

            database["available"] = True

            # 5. Trial request succeeds
            response = client.get("/api/services")

            assert response.status_code == 200
            assert response.get_json()["source"] == "primary"
            assert response.get_json()["system_status"] == "healthy"

            # 6. Circuit returns to CLOSED
            assert breaker.state == "CLOSED"
            assert breaker.failure_count == 0
            assert breaker.last_failure_time is None

    finally:
        # Restore shared circuit-breaker state.
        breaker.state = original_state
        breaker.failure_count = original_failure_count
        breaker.last_failure_time = original_last_failure_time


def test_recovery_generates_incident_events(monkeypatch):
    """Verify that the recovery lifecycle generates expected events."""

    breaker = flask_module.db_breaker

    original_state = breaker.state
    original_failure_count = breaker.failure_count
    original_last_failure_time = breaker.last_failure_time

    recorded_events = []
    clock = {"now": 100.0}

    def fake_log_event(event_type, message, severity):
        recorded_events.append(event_type)

    monkeypatch.setattr(
        circuit_breaker,
        "log_event",
        fake_log_event,
    )

    monkeypatch.setattr(
        circuit_breaker.time,
        "monotonic",
        lambda: clock["now"],
    )

    try:
        breaker.state = "CLOSED"
        breaker.failure_count = 0
        breaker.last_failure_time = None

        def failing_operation():
            raise ConnectionError("Database unavailable")

        def successful_operation():
            return [{"id": 1, "name": "Authentication"}]

        # Trigger enough failures to open the circuit.
        for _ in range(breaker.failure_threshold):
            try:
                breaker.call(failing_operation)
            except ConnectionError:
                pass

        assert breaker.state == "OPEN"

        # Advance time to permit a recovery attempt.
        clock["now"] += breaker.recovery_timeout + 1

        result = breaker.call(successful_operation)

        assert result == [{"id": 1, "name": "Authentication"}]
        assert breaker.state == "CLOSED"

        assert recorded_events.count("database_failure") == (
            breaker.failure_threshold
        )
        assert recorded_events.count("circuit_opened") == 1
        assert recorded_events.count("recovery_attempt") == 1
        assert recorded_events.count("database_recovered") == 1

        assert recorded_events == (
            ["database_failure"] * breaker.failure_threshold
            + [
                "circuit_opened",
                "recovery_attempt",
                "database_recovered",
            ]
        )

    finally:
        breaker.state = original_state
        breaker.failure_count = original_failure_count
        breaker.last_failure_time = original_last_failure_time


import pytest

from backend.app import app, chaos_engine, db_breaker


@pytest.fixture
def chaos_client(monkeypatch):
    """Create an isolated Flask test client."""

    original_enabled = chaos_engine.enabled
    original_latency = chaos_engine.latency_ms
    original_rate = chaos_engine.failure_rate

    original_state = db_breaker.state
    original_count = db_breaker.failure_count
    original_time = db_breaker.last_failure_time

    original_fault_setting = app.config["ENABLE_FAULT_INJECTION"]

    monkeypatch.setattr(
        "backend.app.get_services_from_db",
        lambda: [{"id": 1, "name": "Test Service", "status": "active"}],
    )
    monkeypatch.setattr(
        "backend.app.save_to_cache",
        lambda data: None,
    )
    monkeypatch.setattr(
        "backend.app.get_cached_services",
        lambda: [{"id": 1, "name": "Test Service", "status": "active"}],
    )

    db_breaker.state = "CLOSED"
    db_breaker.failure_count = 0
    db_breaker.last_failure_time = None

    try:
        yield app.test_client()
    finally:
        chaos_engine.configure(
            enabled=original_enabled,
            latency_ms=original_latency,
            failure_rate=original_rate,
        )

        db_breaker.state = original_state
        db_breaker.failure_count = original_count
        db_breaker.last_failure_time = original_time

        app.config["ENABLE_FAULT_INJECTION"] = original_fault_setting


def test_chaos_disabled_in_production_mode(chaos_client):
    """Disabled fault injection must bypass chaos."""

    app.config["ENABLE_FAULT_INJECTION"] = False
    chaos_engine.configure(enabled=True, failure_rate=1.0)

    response = chaos_client.get("/api/services")

    assert response.status_code == 200
    assert response.get_json()["source"] == "primary"
    assert db_breaker.state == "CLOSED"


def test_chaos_forced_failure_uses_cache(chaos_client):
    """Chaos failure should trigger Redis fallback."""

    app.config["ENABLE_FAULT_INJECTION"] = True
    chaos_engine.configure(enabled=True, failure_rate=1.0)

    response = chaos_client.get("/api/services")

    assert response.status_code == 200
    assert response.get_json()["source"] == "cache"
    assert response.get_json()["stale"] is True
    assert db_breaker.failure_count == 1


def test_chaos_opens_circuit_after_three_failures(chaos_client):
    """Three chaos failures should open the circuit breaker."""

    app.config["ENABLE_FAULT_INJECTION"] = True
    chaos_engine.configure(enabled=True, failure_rate=1.0)

    for _ in range(3):
        response = chaos_client.get("/api/services")
        assert response.get_json()["source"] == "cache"

    assert db_breaker.state == "OPEN"
    assert db_breaker.failure_count == 3

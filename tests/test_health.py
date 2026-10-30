
import sys
import pytest
from pathlib import Path

sys.path.insert(
    0,
    str(Path(__file__).resolve().parents[1] / "backend")
)

import app as flask_module


@pytest.mark.parametrize(
    "database_available, cache_available, expected_http, expected_status",
    [
        (True, False, 200, "healthy"),
        (False, True, 200, "degraded"),
        (False, False, 503, "unavailable"),
    ],
)
def test_readiness_status(
    monkeypatch,
    database_available,
    cache_available,
    expected_http,
    expected_status,
):
    """Test readiness under different dependency conditions."""

    def fake_database_check():
        if not database_available:
            raise ConnectionError("Database unavailable")
        return []

    def fake_cache_check():
        if cache_available:
            return [{"id": 1, "name": "Test"}]
        return None

    monkeypatch.setattr(
        flask_module,
        "get_services_from_db",
        fake_database_check,
    )

    monkeypatch.setattr(
        flask_module,
        "get_cached_services",
        fake_cache_check,
    )

    with flask_module.app.test_client() as client:
        response = client.get("/health/ready")

    assert response.status_code == expected_http
    assert (
        response.get_json()["system_status"]
        == expected_status
    )


def test_liveness_endpoint():
    with flask_module.app.test_client() as client:
        response = client.get("/health/live")

    assert response.status_code == 200
    assert response.get_json()["status"] == "alive"
    assert response.get_json()["service"] == "faultforge"


def test_liveness_has_request_id():
    with flask_module.app.test_client() as client:
        response = client.get("/health/live")

    assert response.status_code == 200
    assert "X-Request-ID" in response.headers


def test_readiness_does_not_change_circuit_breaker(monkeypatch):
    """Readiness checks must not modify circuit-breaker state."""

    def failing_database():
        raise ConnectionError("Database unavailable")

    def empty_cache():
        return None

    monkeypatch.setattr(
        flask_module,
        "get_services_from_db",
        failing_database,
    )

    monkeypatch.setattr(
        flask_module,
        "get_cached_services",
        empty_cache,
    )

    # Capture the circuit breaker's current state.
    breaker = flask_module.db_breaker

    original_state = breaker.state
    original_failure_count = breaker.failure_count

    with flask_module.app.test_client() as client:
        response = client.get("/health/ready")

    assert response.status_code == 503

    # A readiness probe must not trigger the circuit breaker.
    assert breaker.state == original_state
    assert breaker.failure_count == original_failure_count

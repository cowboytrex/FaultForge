
import pytest

from backend.app import app, chaos_engine


@pytest.fixture
def client():
    """Create a test client and restore configuration afterward."""

    original_testing = app.config["TESTING"]
    original_fault = app.config["ENABLE_FAULT_INJECTION"]
    original_chaos_api = app.config.get("CHAOS_API_ENABLED", False)

    original_chaos = (
        chaos_engine.enabled,
        chaos_engine.latency_ms,
        chaos_engine.failure_rate,
    )

    app.config["TESTING"] = True
    app.config["ENABLE_FAULT_INJECTION"] = True
    app.config["CHAOS_API_ENABLED"] = True

    chaos_engine.configure(enabled=False)

    try:
        yield app.test_client()
    finally:
        chaos_engine.configure(
            enabled=original_chaos[0],
            latency_ms=original_chaos[1],
            failure_rate=original_chaos[2],
        )
        app.config["TESTING"] = original_testing
        app.config["ENABLE_FAULT_INJECTION"] = original_fault
        app.config["CHAOS_API_ENABLED"] = original_chaos_api


def test_chaos_api_disabled(client):
    app.config["CHAOS_API_ENABLED"] = False

    response = client.post(
        "/api/chaos/configure",
        json={"enabled": True},
    )

    assert response.status_code == 403


def test_fault_injection_disabled(client):
    app.config["ENABLE_FAULT_INJECTION"] = False

    response = client.post(
        "/api/chaos/configure",
        json={"enabled": True},
    )

    assert response.status_code == 403


def test_configure_chaos_success(client):
    response = client.post(
        "/api/chaos/configure",
        json={
            "enabled": True,
            "latency_ms": 200,
            "failure_rate": 0.3,
        },
    )

    assert response.status_code == 200
    assert chaos_engine.enabled is True
    assert chaos_engine.latency_ms == 200
    assert chaos_engine.failure_rate == 0.3


def test_reject_invalid_failure_rate(client):
    response = client.post(
        "/api/chaos/configure",
        json={
            "enabled": True,
            "failure_rate": 1.5,
        },
    )

    assert response.status_code == 400


def test_reject_invalid_latency(client):
    response = client.post(
        "/api/chaos/configure",
        json={
            "enabled": True,
            "latency_ms": -100,
        },
    )

    assert response.status_code == 400


def test_reject_invalid_json(client):
    response = client.post(
        "/api/chaos/configure",
        data="not-json",
        content_type="application/json",
    )

    assert response.status_code == 400


def test_reject_remote_client(client):
    response = client.post(
        "/api/chaos/configure",
        json={"enabled": True},
        environ_overrides={"REMOTE_ADDR": "203.0.113.10"},
    )

    assert response.status_code == 403


def test_reset_chaos(client):
    chaos_engine.configure(
        enabled=True,
        latency_ms=1000,
        failure_rate=0.5,
    )

    response = client.post("/api/chaos/reset")

    assert response.status_code == 200
    assert chaos_engine.enabled is False
    assert chaos_engine.latency_ms == 0
    assert chaos_engine.failure_rate == 0.0


def test_reset_denied_when_api_disabled(client):
    app.config["CHAOS_API_ENABLED"] = False

    response = client.post("/api/chaos/reset")

    assert response.status_code == 403

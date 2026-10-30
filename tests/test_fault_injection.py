
import sys
from pathlib import Path

import pytest

sys.path.insert(
    0,
    str(Path(__file__).resolve().parents[1] / "backend")
)

import app as flask_module


@pytest.fixture
def client():
    flask_module.app.config["TESTING"] = True

    with flask_module.app.test_client() as test_client:
        yield test_client


def test_fault_injection_disabled(client, monkeypatch):
    """Fault injection must be blocked by default."""
    monkeypatch.delenv("ENABLE_FAULT_INJECTION", raising=False)

    response = client.post("/api/simulate-failure")

    assert response.status_code == 403
    assert response.get_json()["error"] == (
        "Fault injection is disabled"
    )


def test_fault_injection_explicitly_disabled(client, monkeypatch):
    """Explicitly disabling fault injection must return 403."""
    monkeypatch.setenv("ENABLE_FAULT_INJECTION", "false")

    response = client.post("/api/simulate-failure")

    assert response.status_code == 403


def test_fault_injection_enabled(client, monkeypatch):
    """Fault injection should work when explicitly enabled."""
    monkeypatch.setenv("ENABLE_FAULT_INJECTION", "true")

    # Mock the internal service request so this test
    # doesn't need a real PostgreSQL connection.
    class FakeResponse:
        status_code = 200

        def get_json(self):
            return {"system_status": "degraded"}

    class FakeClient:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_value, traceback):
            return False

        def get(self, path):
            assert path == "/api/services?fail=true"
            return FakeResponse()

    monkeypatch.setattr(
        flask_module.app,
        "test_client",
        lambda: FakeClient()
    )


def test_direct_fault_injection_blocked(client, monkeypatch):
    """Direct API requests cannot bypass fault-injection protection."""

    monkeypatch.setenv("ENABLE_FAULT_INJECTION", "false")

    response = client.get("/api/services?fail=true")

    assert response.status_code == 403
    assert response.get_json()["error"] == (
        "Fault injection is disabled"
    )


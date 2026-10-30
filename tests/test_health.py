
import sys
import pytest
from pathlib import Path

sys.path.insert(
    0,
    str(Path(__file__).resolve().parents[1] / "backend")
)

import app as flask_module

@pytest.mark.parametrize(
    "system_status, expected_http, expected_status",
    [
        ("healthy", 200, "ready"),
        ("degraded", 200, "ready"),
        ("unavailable", 503, "not_ready"),
    ],
)
def test_readiness_status(
    monkeypatch,
    system_status,
    expected_http,
    expected_status,
):
    flask_module.app.config["TESTING"] = True

    class FakeResponse:
        status_code = 200

        def get_json(self):
            return {"system_status": system_status}

    class FakeClient:
        def get(self, path):
            assert path == "/api/services"
            return FakeResponse()

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    monkeypatch.setattr(
        flask_module.app,
        "test_client",
        lambda: FakeClient(),
    )

    with flask_module.app.test_request_context(
        "/health/ready"
    ):
        response, status_code = flask_module.health_ready()

    assert status_code == expected_http
    assert response.get_json()["status"] == expected_status


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


import pytest

import importlib

import pytest

from backend.alert_repository import AlertRepository

app_module = importlib.import_module("backend.app")
app = app_module.app


@pytest.fixture
def client(tmp_path, monkeypatch):
    """Use an isolated SQLite database for API tests."""
    repository = AlertRepository(tmp_path / "api_alerts.db")

    monkeypatch.setattr(
        app_module,
        "AlertRepository",
        lambda: repository,
    )

    repository.save({
        "timestamp": "2026-10-30T12:00:00+00:00",
        "status": "healthy",
        "previous_status": None,
        "p95_latency_ms": 100.0,
    })

    repository.save({
        "timestamp": "2026-10-30T12:01:00+00:00",
        "status": "warning",
        "previous_status": "healthy",
        "p95_latency_ms": 250.0,
    })

    repository.save({
        "timestamp": "2026-10-30T12:02:00+00:00",
        "status": "critical",
        "previous_status": "warning",
        "p95_latency_ms": 600.0,
    })

    app.config["TESTING"] = True

    with app.test_client() as test_client:
        yield test_client


def test_history_returns_all_events(client):
    response = client.get("/api/metrics/latency/alerts/history")

    assert response.status_code == 200
    assert response.get_json()["total"] == 3


def test_filter_critical_events(client):
    response = client.get(
        "/api/metrics/latency/alerts/history?status=critical"
    )

    data = response.get_json()

    assert response.status_code == 200
    assert data["total"] == 1
    assert data["history"][0]["status"] == "critical"


def test_history_limit(client):
    response = client.get(
        "/api/metrics/latency/alerts/history?limit=2"
    )

    data = response.get_json()

    assert response.status_code == 200
    assert data["total"] == 2
    assert [event["status"] for event in data["history"]] == [
        "warning",
        "critical",
    ]


def test_invalid_status_returns_400(client):
    response = client.get(
        "/api/metrics/latency/alerts/history?status=unknown"
    )

    assert response.status_code == 400


def test_invalid_limit_returns_400(client):
    response = client.get(
        "/api/metrics/latency/alerts/history?limit=0"
    )

    assert response.status_code == 400

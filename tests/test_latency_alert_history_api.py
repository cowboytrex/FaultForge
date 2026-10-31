
from unittest.mock import patch

from backend.app import app


def test_alert_history_api_empty():
    """The endpoint should handle an empty alert history."""

    with patch("backend.app.AlertRepository") as mock_repository:
        mock_repository.return_value.history.return_value = []

        with app.test_client() as client:
            response = client.get(
                "/api/metrics/latency/alerts/history"
            )

    assert response.status_code == 200
    assert response.get_json() == {
        "total": 0,
        "history": [],
    }


def test_alert_history_api_returns_events():
    """The endpoint should return recorded transitions."""

    events = [
        {
            "timestamp": "2026-10-30T23:44:29+00:00",
            "status": "healthy",
            "previous_status": None,
            "p95_latency_ms": 25,
        },
        {
            "timestamp": "2026-10-30T23:45:00+00:00",
            "status": "warning",
            "previous_status": "healthy",
            "p95_latency_ms": 350,
        },
    ]

    with patch("backend.app.AlertRepository") as mock_repository:
        mock_repository.return_value.history.return_value = events

        with app.test_client() as client:
            response = client.get(
                "/api/metrics/latency/alerts/history"
            )

    assert response.status_code == 200

    data = response.get_json()

    assert data["total"] == 2
    assert data["history"] == events
    assert data["history"][1]["previous_status"] == "healthy"


def test_alert_history_api_returns_json():
    """The response should have a JSON content type."""

    with patch("backend.app.AlertRepository") as mock_repository:
        mock_repository.return_value.history.return_value = []

        with app.test_client() as client:
            response = client.get(
                "/api/metrics/latency/alerts/history"
            )

    assert response.is_json


def test_latency_alert_api_survives_database_failure(monkeypatch):
    """The latency API should work even if alert storage fails."""
    import importlib

    app_module = importlib.import_module("backend.app")
    client = app_module.app.test_client()

    # Simulate a database failure when recording an alert.
    def failing_record(*args, **kwargs):
        raise OSError("Simulated SQLite failure")

    monkeypatch.setattr(
        app_module.alert_history,
        "record",
        failing_record,
    )

    response = client.get("/api/metrics/latency/alert")

    assert response.status_code == 200

    data = response.get_json()

    assert data["status"] in {
        "healthy",
        "warning",
        "critical",
        "no_data",
    }

    assert "p95_latency_ms" in data


def test_latency_alert_database_failure_is_logged(monkeypatch, caplog):
    """Database failures should be logged without breaking the API."""
    import importlib
    import logging

    app_module = importlib.import_module("backend.app")
    client = app_module.app.test_client()

    def failing_record(*args, **kwargs):
        raise OSError("Simulated SQLite failure")

    monkeypatch.setattr(
        app_module.alert_history,
        "record",
        failing_record,
    )

    with caplog.at_level(logging.ERROR):
        response = client.get("/api/metrics/latency/alert")

    # The API should remain available.
    assert response.status_code == 200

    # The database failure should be logged.
    assert "Failed to persist latency alert transition" in caplog.text
    assert "Simulated SQLite failure" in caplog.text


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

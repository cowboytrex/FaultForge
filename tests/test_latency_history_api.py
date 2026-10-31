
from unittest.mock import patch

from backend.app import app


def test_latency_history_api_returns_empty_history():
    app.config["TESTING"] = True

    with patch("backend.app.latency_collector") as mock_collector:
        mock_collector.history.return_value = []

        with app.test_client() as client:
            response = client.get("/api/metrics/latency/history")

    assert response.status_code == 200
    assert response.get_json() == {
        "total": 0,
        "history": [],
    }


def test_latency_history_api_returns_samples():
    app.config["TESTING"] = True

    samples = [
        {
            "timestamp": "2026-10-30T12:00:00+00:00",
            "duration_ms": 12.5,
        },
        {
            "timestamp": "2026-10-30T12:00:01+00:00",
            "duration_ms": 25.0,
        },
    ]

    with patch("backend.app.latency_collector") as mock_collector:
        mock_collector.history.return_value = samples

        with app.test_client() as client:
            response = client.get("/api/metrics/latency/history")

    assert response.status_code == 200
    assert response.get_json() == {
        "total": 2,
        "history": samples,
    }


def test_latency_history_api_returns_json():
    app.config["TESTING"] = True

    with patch("backend.app.latency_collector") as mock_collector:
        mock_collector.history.return_value = []

        with app.test_client() as client:
            response = client.get("/api/metrics/latency/history")

    assert response.is_json

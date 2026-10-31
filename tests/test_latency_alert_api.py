
from unittest.mock import patch

from backend.app import app


def test_alert_api_no_data():
    with patch("backend.app.latency_collector") as mock_collector:
        mock_collector.metrics.return_value = {
            "total_requests": 0,
            "p95_latency_ms": 0,
        }

        with app.test_client() as client:
            response = client.get("/api/metrics/latency/alert")

    assert response.status_code == 200
    assert response.get_json()["status"] == "no_data"


def test_alert_api_healthy():
    with patch("backend.app.latency_collector") as mock_collector:
        mock_collector.metrics.return_value = {
            "total_requests": 10,
            "p95_latency_ms": 100,
        }

        with app.test_client() as client:
            response = client.get("/api/metrics/latency/alert")

    assert response.status_code == 200
    assert response.get_json()["status"] == "healthy"


def test_alert_api_warning():
    with patch("backend.app.latency_collector") as mock_collector:
        mock_collector.metrics.return_value = {
            "total_requests": 10,
            "p95_latency_ms": 350,
        }

        with app.test_client() as client:
            response = client.get("/api/metrics/latency/alert")

    assert response.status_code == 200
    assert response.get_json()["status"] == "warning"


def test_alert_api_critical():
    with patch("backend.app.latency_collector") as mock_collector:
        mock_collector.metrics.return_value = {
            "total_requests": 10,
            "p95_latency_ms": 750,
        }

        with app.test_client() as client:
            response = client.get("/api/metrics/latency/alert")

    assert response.status_code == 200
    assert response.get_json()["status"] == "critical"

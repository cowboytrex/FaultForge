
from unittest.mock import patch

from backend.app import app
from backend.alert_history import AlertHistory


def test_alert_transitions():
    history = AlertHistory()

    scenarios = [
        (50, "healthy"),
        (350, "warning"),
        (750, "critical"),
        (40, "healthy"),
    ]

    with patch("backend.app.alert_history", history):
        with patch("backend.app.latency_collector") as collector:
            with app.test_client() as client:

                for latency, expected_status in scenarios:
                    collector.metrics.return_value = {
                        "total_requests": 10,
                        "p95_latency_ms": latency,
                    }

                    response = client.get(
                        "/api/metrics/latency/alert"
                    )

                    assert response.status_code == 200
                    assert response.get_json()["status"] == expected_status

                response = client.get(
                    "/api/metrics/latency/alerts/history"
                )

    assert response.status_code == 200

    events = response.get_json()["history"]

    assert [event["status"] for event in events] == [
        "healthy",
        "warning",
        "critical",
        "healthy",
    ]

    assert events[1]["previous_status"] == "healthy"
    assert events[2]["previous_status"] == "warning"
    assert events[3]["previous_status"] == "critical"


import sys
from pathlib import Path

sys.path.insert(
    0,
    str(Path(__file__).resolve().parents[1] / "backend")
)

from backend.app import app
from latency_collector import latency_collector


def test_latency_metrics_api():
    """The latency API returns metrics from the collector."""

    # Replace the shared collector's history with a known sample.
    # Restore it afterward to avoid affecting other tests.
    with latency_collector._lock:
        original_durations = list(latency_collector._durations)
        latency_collector._durations.clear()

    try:
        for duration in [10, 20, 30, 40, 100]:
            latency_collector.record(duration)

        with app.test_client() as client:
            response = client.get("/api/metrics/latency")

        assert response.status_code == 200

        data = response.get_json()

        assert data["total_requests"] == 5
        assert data["average_latency_ms"] == 40.0
        assert data["p95_latency_ms"] == 100
        assert data["max_latency_ms"] == 100
        assert data["slow_requests"] == 0

    finally:
        with latency_collector._lock:
            latency_collector._durations.clear()
            latency_collector._durations.extend(original_durations)

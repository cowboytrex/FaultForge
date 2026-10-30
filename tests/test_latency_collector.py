
import pytest

from backend.latency_collector import LatencyCollector


def test_collector_starts_empty():
    collector = LatencyCollector()

    assert collector.snapshot() == []
    assert collector.metrics()["total_requests"] == 0


def test_collector_records_durations():
    collector = LatencyCollector()

    collector.record(10)
    collector.record(20)
    collector.record(30)

    assert collector.snapshot() == [10, 20, 30]


def test_collector_removes_oldest_samples():
    collector = LatencyCollector(max_samples=3)

    for duration in [10, 20, 30, 40]:
        collector.record(duration)

    assert collector.snapshot() == [20, 30, 40]


def test_collector_calculates_metrics():
    collector = LatencyCollector()

    for duration in [10, 20, 30, 40, 100]:
        collector.record(duration)

    result = collector.metrics()

    assert result["total_requests"] == 5
    assert result["average_latency_ms"] == 40.0
    assert result["p95_latency_ms"] == 100
    assert result["max_latency_ms"] == 100


def test_collector_detects_slow_requests():
    collector = LatencyCollector()

    for duration in [100, 200, 600, 800]:
        collector.record(duration)

    result = collector.metrics(slow_threshold_ms=500)

    assert result["slow_requests"] == 2


def test_collector_rejects_invalid_durations():
    collector = LatencyCollector()

    for duration in [-10, float("nan"), float("inf")]:
        with pytest.raises(ValueError):
            collector.record(duration)


def test_collector_rejects_invalid_capacity():
    for capacity in [0, -1, 1.5, True]:
        with pytest.raises(ValueError):
            LatencyCollector(max_samples=capacity)


def test_snapshot_is_independent_copy():
    collector = LatencyCollector()

    collector.record(10)

    snapshot = collector.snapshot()
    snapshot.append(999)

    assert collector.snapshot() == [10]

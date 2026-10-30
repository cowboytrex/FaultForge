
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(
    0,
    str(Path(__file__).resolve().parents[1] / "backend")
)

from latency_collector import LatencyCollector


def test_history_records_timestamps():
    collector = LatencyCollector()

    collector.record(12.5)
    collector.record(25.0)

    history = collector.history()

    assert len(history) == 2
    assert history[0]["duration_ms"] == 12.5
    assert history[1]["duration_ms"] == 25.0

    for sample in history:
        timestamp = datetime.fromisoformat(sample["timestamp"])
        assert timestamp.tzinfo is not None


def test_history_respects_max_samples():
    collector = LatencyCollector(max_samples=2)

    collector.record(10)
    collector.record(20)
    collector.record(30)

    history = collector.history()

    assert len(history) == 2
    assert [sample["duration_ms"] for sample in history] == [20, 30]


def test_history_returns_independent_copies():
    collector = LatencyCollector()
    collector.record(15)

    history = collector.history()
    history[0]["duration_ms"] = 999

    assert collector.history()[0]["duration_ms"] == 15


def test_history_preserves_existing_metrics():
    collector = LatencyCollector()

    collector.record(10)
    collector.record(20)
    collector.record(30)

    assert collector.snapshot() == [10, 20, 30]
    assert collector.metrics()["average_latency_ms"] == 20.0

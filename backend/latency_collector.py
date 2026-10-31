
from collections import deque
from threading import Lock
from datetime import datetime, timezone

from latency_metrics import calculate_latency_metrics


class LatencyCollector:
    """Keep a bounded history of recent request durations."""

    def __init__(self, max_samples=1000):
        if not isinstance(max_samples, int) or isinstance(max_samples, bool) or max_samples < 1:
            raise ValueError("max_samples must be a positive integer")

        self._durations = deque(maxlen=max_samples)
        self._lock = Lock()
        self._history = deque(maxlen=max_samples)

    def record(self, duration_ms):
        """Store one request duration in milliseconds."""
        import math

        if not isinstance(duration_ms, (int, float)) or not math.isfinite(duration_ms) or duration_ms < 0:
            raise ValueError("duration_ms must be finite and nonnegative")

        timestamp = datetime.now(timezone.utc).isoformat()

        with self._lock:
            self._durations.append(duration_ms)
            self._history.append({
                "timestamp": timestamp,
                "duration_ms": duration_ms,
            })

    def snapshot(self):
        """Return a copy of the current duration history."""
        with self._lock:
            return list(self._durations)

    def metrics(self, slow_threshold_ms=500):
        """Calculate statistics for recent requests."""
        return calculate_latency_metrics(
            self.snapshot(),
            slow_threshold_ms=slow_threshold_ms,
        )

    def history(self):
        """Return timestamped request samples."""
        with self._lock:
            return [sample.copy() for sample in self._history]
latency_collector = LatencyCollector()

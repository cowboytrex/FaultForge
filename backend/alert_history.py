
from collections import deque
from datetime import datetime, timezone
from threading import Lock


class AlertHistory:
    """Track changes in performance alert status."""

    VALID_STATUSES = {
        "healthy",
        "warning",
        "critical",
        "no_data",
    }

    def __init__(self, max_events=100):
        if (
            not isinstance(max_events, int)
            or isinstance(max_events, bool)
            or max_events < 1
        ):
            raise ValueError("max_events must be a positive integer")

        self._events = deque(maxlen=max_events)
        self._current_status = None
        self._lock = Lock()

    def record(self, status, p95_latency_ms=None):
        """Record an event only when the status changes."""
        if status not in self.VALID_STATUSES:
            raise ValueError("Invalid alert status")

        with self._lock:
            if status == self._current_status:
                return False

            self._events.append({
                "timestamp": datetime.now(
                    timezone.utc
                ).isoformat(),
                "status": status,
                "previous_status": self._current_status,
                "p95_latency_ms": p95_latency_ms,
            })

            self._current_status = status
            return True

    def history(self):
        """Return a copy of recorded alert transitions."""
        with self._lock:
            return [event.copy() for event in self._events]


alert_history = AlertHistory()

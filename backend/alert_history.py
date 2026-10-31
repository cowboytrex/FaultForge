
from collections import deque
from datetime import datetime, timezone
from threading import Lock

from backend.alert_repository import AlertRepository


class AlertHistory:
    """Track changes in performance alert status."""

    VALID_STATUSES = {
        "healthy",
        "warning",
        "critical",
        "no_data",
    }

    def __init__(self, max_events=100, repository=None):
        if (
            not isinstance(max_events, int)
            or isinstance(max_events, bool)
            or max_events < 1
        ):
            raise ValueError("max_events must be a positive integer")

        self._events = deque(maxlen=max_events)
        self._current_status = None
        self._lock = Lock()
        self._repository = repository

                # Restore previous alert transitions from SQLite.
        if self._repository is not None:
            saved_events = self._repository.history(limit=max_events)
            self._events.extend(saved_events)

            if saved_events:
                self._current_status = saved_events[-1]["status"]


    def record(self, status, p95_latency_ms=None):
        """Record an event only when the status changes."""
        if status not in self.VALID_STATUSES:
            raise ValueError("Invalid alert status")

        with self._lock:
            if status == self._current_status:
                return False

            event = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "status": status,
                "previous_status": self._current_status,
                "p95_latency_ms": p95_latency_ms,
            }

            # Persist the event and enforce the retention limit.
            if self._repository is not None:
                self._repository.save(event)

            self._events.append(event)
            self._current_status = status

            return True


    def history(self):
        """Return a copy of recorded alert transitions."""
        with self._lock:
            return [event.copy() for event in self._events]


alert_history = AlertHistory(repository=AlertRepository())

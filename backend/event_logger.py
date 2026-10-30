from collections import deque
from datetime import datetime, timezone
from threading import Lock

# Keep the 100 most recent reliability events.
events = deque(maxlen=100)
events_lock = Lock()


def log_event(event_type, message, severity="info"):
    """Record a reliability event."""
    event = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "type": event_type,
        "message": message,
        "severity": severity
    }

    with events_lock:
        events.appendleft(event)

    return event


def get_events():
    """Return a snapshot of the latest events."""
    with events_lock:
        return list(events)

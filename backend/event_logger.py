
from datetime import datetime, timezone
from threading import Lock

from event_store import save_event, load_events

events_lock = Lock()


def log_event(event_type, message, severity="info"):
    """Record an incident in persistent storage."""
    event = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "type": event_type,
        "message": message,
        "severity": severity
    }

    with events_lock:
        save_event(event)

    return event


def get_events():
    """Retrieve the 100 most recent incidents."""
    with events_lock:
        return load_events(limit=100)

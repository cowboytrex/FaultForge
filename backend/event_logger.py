from structured_logger import logger
from datetime import datetime, timezone
from threading import Lock
from flask import g, has_request_context
from event_store import save_event, load_events

events_lock = Lock()



def log_event(event_type, message, severity="info"):
    """Record an incident in persistent storage."""
    request_id = None

    if has_request_context():
        request_id = getattr(g, "request_id", None)

    event = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "type": event_type,
        "message": message,
        "severity": severity,
        "request_id": request_id,
    }

    with events_lock:
        save_event(event)

    level = {
        "info": "info",
        "warning": "warning",
        "critical": "critical"
    }.get(severity, "info")

    getattr(logger, level)(
        message,
        extra={
            "event_type": event_type,
            "request_id": request_id,
        }
    )

    return event


def get_events():
    """Retrieve the 100 most recent incidents."""
    with events_lock:
        return load_events(limit=100)

from event_store import load_events
from collections import defaultdict
from datetime import datetime, timedelta, timezone

def calculate_metrics():
    """Calculate reliability metrics from incident history."""

    # Load all recorded events for accurate lifetime totals.
    events = load_events(limit=-1)

    total_failures = 0
    circuit_trips = 0
    successful_recoveries = 0

    for event in events:
        event_type = event["type"]

        if event_type == "database_failure":
            total_failures += 1

        elif event_type == "circuit_opened":
            circuit_trips += 1

        elif event_type == "database_recovered":
            successful_recoveries += 1

    recovery_rate = (
        round(successful_recoveries / circuit_trips * 100, 1)
        if circuit_trips > 0
        else 0.0
    )

    return {
        "total_failures": total_failures,
        "circuit_trips": circuit_trips,
        "successful_recoveries": successful_recoveries,
        "recovery_rate": recovery_rate
    }


def calculate_daily_trends(days=7):
    """Count reliability events for each UTC day."""
    if days < 1:
        raise ValueError("days must be positive")

    today = datetime.now(timezone.utc).date()
    start_date = today - timedelta(days=days - 1)

    trends = {
        (start_date + timedelta(days=i)).isoformat(): {
            "date": (start_date + timedelta(days=i)).isoformat(),
            "failures": 0,
            "circuit_trips": 0
        }
        for i in range(days)
    }

    for event in load_events(limit=-1):
        event_date = datetime.fromisoformat(
            event["timestamp"]
        ).astimezone(timezone.utc).date().isoformat()

        if event_date not in trends:
            continue

        if event["type"] == "database_failure":
            trends[event_date]["failures"] += 1

        elif event["type"] == "circuit_opened":
            trends[event_date]["circuit_trips"] += 1

    return list(trends.values())

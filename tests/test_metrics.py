
import sys
from pathlib import Path

import pytest

# Tell Python where the backend modules are located.
sys.path.insert(
    0,
    str(Path(__file__).resolve().parents[1] / "backend")
)

import event_store
from event_logger import log_event
from metrics import calculate_metrics, calculate_daily_trends



@pytest.fixture(autouse=True)
def isolated_database(tmp_path, monkeypatch):
    """Use a temporary database for every test."""
    test_db = tmp_path / "metrics_test.db"
    monkeypatch.setattr(event_store, "DB_PATH", test_db)


def test_empty_metrics():
    """An empty incident history should produce zero metrics."""
    result = calculate_metrics()

    assert result["total_failures"] == 0
    assert result["circuit_trips"] == 0
    assert result["successful_recoveries"] == 0
    assert result["recovery_rate"] == 0.0


def test_failure_count():
    """Count database failures correctly."""
    log_event("database_failure", "Connection lost")
    log_event("database_failure", "Connection lost")

    result = calculate_metrics()

    assert result["total_failures"] == 2


def test_recovery_rate():
    """Calculate recovery rate from circuit events."""
    for _ in range(3):
        log_event("circuit_opened", "Circuit opened")

    for _ in range(2):
        log_event("database_recovered", "Database restored")

    result = calculate_metrics()

    assert result["circuit_trips"] == 3
    assert result["successful_recoveries"] == 2
    assert result["recovery_rate"] == 66.7


def test_unrelated_events_ignored():
    """Other incident types must not affect metrics."""
    log_event("recovery_attempt", "Testing recovery")

    result = calculate_metrics()

    assert result["total_failures"] == 0
    assert result["circuit_trips"] == 0
    assert result["successful_recoveries"] == 0


def test_daily_trends_seven_days():
    """The trends API should return seven daily records."""
    trends = calculate_daily_trends()

    assert len(trends) == 7

    for day in trends:
        assert "date" in day
        assert "failures" in day
        assert "circuit_trips" in day


def test_daily_trends_count_events():
    """Today's failures and circuit trips should be counted."""
    from datetime import datetime, timezone

    log_event("database_failure", "Database unavailable")
    log_event("database_failure", "Database unavailable")
    log_event("circuit_opened", "Circuit breaker opened")

    trends = calculate_daily_trends()

    today = datetime.now(timezone.utc).date().isoformat()
    today_data = next(
        day for day in trends if day["date"] == today
    )

    assert today_data["failures"] == 2
    assert today_data["circuit_trips"] == 1


def test_daily_trends_empty_history():
    """Days without incidents should have zero counts."""
    trends = calculate_daily_trends()

    assert all(day["failures"] == 0 for day in trends)
    assert all(day["circuit_trips"] == 0 for day in trends)


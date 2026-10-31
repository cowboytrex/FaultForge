
from backend.alert_history import AlertHistory
from backend.alert_repository import AlertRepository


def test_alert_history_survives_restart(tmp_path):
    db_path = tmp_path / "alerts.db"

    # First application instance
    repository = AlertRepository(db_path)
    history = AlertHistory(repository=repository)

    history.record("healthy", 100.0)
    history.record("warning", 250.0)
    history.record("critical", 600.0)

    # Simulate an application restart
    restarted_repository = AlertRepository(db_path)
    restarted_history = AlertHistory(
        repository=restarted_repository
    )

    events = restarted_history.history()

    assert len(events) == 3
    assert [event["status"] for event in events] == [
        "healthy",
        "warning",
        "critical",
    ]


def test_restored_status_prevents_duplicate_alert(tmp_path):
    db_path = tmp_path / "alerts.db"

    repository = AlertRepository(db_path)
    history = AlertHistory(repository=repository)

    history.record("warning", 250.0)

    # Simulate restarting the application
    restarted_history = AlertHistory(
        repository=AlertRepository(db_path)
    )

    # Same status should not create another event
    recorded = restarted_history.record("warning", 300.0)

    assert recorded is False
    assert len(restarted_history.history()) == 1


def test_new_transition_after_restart_is_persisted(tmp_path):
    db_path = tmp_path / "alerts.db"

    history = AlertHistory(
        repository=AlertRepository(db_path)
    )
    history.record("warning", 250.0)

    # Restart and record a new transition
    restarted_history = AlertHistory(
        repository=AlertRepository(db_path)
    )
    restarted_history.record("healthy", 100.0)

    # Verify the database contains both events
    final_repository = AlertRepository(db_path)
    events = final_repository.history()

    assert len(events) == 2
    assert events[0]["status"] == "warning"
    assert events[1]["status"] == "healthy"
    assert events[1]["previous_status"] == "warning"

def test_automatic_retention_after_record(tmp_path):
    """Recording an alert should trigger database retention."""
    db_path = tmp_path / "retention.db"
    repository = AlertRepository(db_path)

    # Populate the database with 1,000 existing events.
    for i in range(1000):
        repository.save({
            "timestamp": f"2026-10-30T12:00:{i:04d}+00:00",
            "status": "healthy",
            "previous_status": None,
            "p95_latency_ms": 100.0,
        })

    # Create an AlertHistory instance using the populated database.
    history = AlertHistory(repository=repository)

    # Trigger a new status transition.
    recorded = history.record("critical", 600.0)

    # The database should still contain exactly 1,000 events.
    events = repository.history(limit=2000)

    assert recorded is True
    assert len(events) == 1000

    # The oldest event should have been removed.
    assert events[0]["timestamp"] == "2026-10-30T12:00:0001+00:00"

    # The newest event should be the critical transition.
    assert events[-1]["status"] == "critical"
    assert events[-1]["previous_status"] == "healthy"
    assert events[-1]["p95_latency_ms"] == 600.0



def test_failed_database_save_does_not_update_memory(tmp_path, monkeypatch):
    """A failed SQLite save must not update in-memory alert history."""
    repository = AlertRepository(tmp_path / "failure.db")
    history = AlertHistory(repository=repository)

    history.record("healthy", 100.0)

    def failing_save(event):
        raise OSError("Simulated database write failure")

    monkeypatch.setattr(repository, "save", failing_save)

    import pytest

    with pytest.raises(OSError, match="Simulated database write failure"):
        history.record("critical", 600.0)

    # The failed transition should not appear in memory.
    events = history.history()

    assert len(events) == 1
    assert events[0]["status"] == "healthy"

    # The failed transition should not appear in SQLite.
    saved_events = AlertRepository(tmp_path / "failure.db").history()
    assert len(saved_events) == 1
    assert saved_events[0]["status"] == "healthy"


def test_alert_history_recovers_after_database_failure(tmp_path, monkeypatch):
    """Alert history should recover after a temporary database failure."""
    repository = AlertRepository(tmp_path / "recovery.db")
    history = AlertHistory(repository=repository)

    # 1. Normal operation
    assert history.record("healthy", 100.0) is True

    original_save = repository.save

    # 2. Simulate a temporary database failure
    def failing_save(event):
        raise OSError("Database temporarily unavailable")

    monkeypatch.setattr(repository, "save", failing_save)

    import pytest

    with pytest.raises(OSError, match="Database temporarily unavailable"):
        history.record("critical", 600.0)

    # Failed transition should not update memory or SQLite.
    assert len(history.history()) == 1
    assert len(repository.history()) == 1

    # 3. Restore normal database operation
    monkeypatch.setattr(repository, "save", original_save)

    # Retry the critical transition
    assert history.record("critical", 600.0) is True

    events = repository.history()

    assert len(events) == 2
    assert events[0]["status"] == "healthy"
    assert events[1]["status"] == "critical"
    assert events[1]["previous_status"] == "healthy"

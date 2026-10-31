
import pytest

from backend.alert_repository import AlertRepository


@pytest.fixture
def repository(tmp_path):
    """Create an isolated SQLite database for each test."""
    return AlertRepository(tmp_path / "test_alerts.db")


def make_event(status, previous_status=None, p95=100.0):
    """Build a sample performance alert event."""
    return {
        "timestamp": "2026-10-30T12:00:00+00:00",
        "status": status,
        "previous_status": previous_status,
        "p95_latency_ms": p95,
    }


def test_database_starts_empty(repository):
    assert repository.history() == []


def test_save_alert(repository):
    event = make_event("healthy")

    repository.save(event)

    assert repository.history() == [event]


def test_save_multiple_alerts(repository):
    repository.save(make_event("healthy"))
    repository.save(make_event("warning", "healthy", 250.0))
    repository.save(make_event("critical", "warning", 600.0))

    events = repository.history()

    assert len(events) == 3
    assert [event["status"] for event in events] == [
        "healthy",
        "warning",
        "critical",
    ]


def test_history_limit(repository):
    for i in range(5):
        repository.save(make_event("warning", p95=float(i)))

    events = repository.history(limit=2)

    assert len(events) == 2
    assert [event["p95_latency_ms"] for event in events] == [3.0, 4.0]


def test_alerts_survive_repository_restart(tmp_path):
    db_path = tmp_path / "persistent_alerts.db"

    first_repository = AlertRepository(db_path)
    first_repository.save(make_event("critical", "warning", 650.0))

    # Recreate the repository using the same database file.
    restarted_repository = AlertRepository(db_path)

    events = restarted_repository.history()

    assert len(events) == 1
    assert events[0]["status"] == "critical"
    assert events[0]["p95_latency_ms"] == 650.0


def test_filter_critical_alerts(repository):
    repository.save(make_event("healthy", p95=100.0))
    repository.save(make_event("warning", "healthy", 250.0))
    repository.save(make_event("critical", "warning", 600.0))
    repository.save(make_event("critical", "warning", 700.0))

    events = repository.history(status="critical")

    assert len(events) == 2
    assert all(event["status"] == "critical" for event in events)
    assert [event["p95_latency_ms"] for event in events] == [
        600.0,
        700.0,
    ]


def test_filter_warning_alerts(repository):
    repository.save(make_event("healthy"))
    repository.save(make_event("warning", "healthy", 250.0))
    repository.save(make_event("critical", "warning", 600.0))

    events = repository.history(status="warning")

    assert len(events) == 1
    assert events[0]["status"] == "warning"


def test_filter_respects_limit(repository):
    for i in range(5):
        repository.save(make_event("critical", p95=600.0 + i))

    events = repository.history(limit=2, status="critical")

    assert len(events) == 2
    assert [event["p95_latency_ms"] for event in events] == [
        603.0,
        604.0,
    ]


def test_invalid_filter_rejected(repository):
    with pytest.raises(ValueError, match="Invalid alert status"):
        repository.history(status="unknown")

    with pytest.raises(ValueError, match="positive integer"):
        repository.history(limit=0)


def test_retention_deletes_oldest_events(repository):
    """Keep only the three newest alerts."""
    for i in range(5):
        repository.save(
            make_event("warning", p95=float(i))
        )

    deleted = repository.delete_old_events(keep_latest=3)

    events = repository.history()

    assert deleted == 2
    assert len(events) == 3
    assert [event["p95_latency_ms"] for event in events] == [
        2.0, 3.0, 4.0
    ]


def test_retention_preserves_small_history(repository):
    """Do not delete events when below the retention limit."""
    repository.save(make_event("healthy"))
    repository.save(make_event("warning"))

    deleted = repository.delete_old_events(keep_latest=10)

    assert deleted == 0
    assert len(repository.history()) == 2


def test_retention_handles_empty_database(repository):
    """Cleanup should work even when no alerts exist."""
    deleted = repository.delete_old_events(keep_latest=5)

    assert deleted == 0
    assert repository.history() == []


def test_retention_rejects_invalid_limits(repository):
    """Reject invalid retention settings."""
    for invalid_limit in [0, -1, True, 1.5, "100"]:
        with pytest.raises(ValueError, match="positive integer"):
            repository.delete_old_events(
                keep_latest=invalid_limit
            )


def test_save_rolls_back_when_retention_fails(tmp_path):
    """A retention failure should roll back the entire transaction."""
    import sqlite3

    repository = AlertRepository(tmp_path / "rollback.db")

    repository.save(make_event("healthy"))

    # Prevent DELETE operations on the alert table.
    with sqlite3.connect(repository.db_path) as connection:
        connection.execute(
            """
            CREATE TRIGGER block_alert_deletion
            BEFORE DELETE ON alert_events
            BEGIN
                SELECT RAISE(ABORT, 'Deletion blocked');
            END;
            """
        )

    # Insert enough records that the next save requires cleanup.
    with sqlite3.connect(repository.db_path) as connection:
        for i in range(1000):
            connection.execute(
                """
                INSERT INTO alert_events (
                    timestamp, status, previous_status, p95_latency_ms
                ) VALUES (?, ?, ?, ?)
                """,
                (
                    f"2026-10-30T12:00:{i:04d}+00:00",
                    "warning",
                    "healthy",
                    float(i),
                ),
            )

    # There are now 1,001 records.
    assert len(repository.history(limit=2000)) == 1001

    # Saving another event triggers retention, which must fail.
    with pytest.raises(sqlite3.DatabaseError, match="Deletion blocked"):
        repository.save(make_event("critical"))

    # The failed transaction must not add another record.
    events = repository.history(limit=2000)

    assert len(events) == 1001
    assert events[-1]["p95_latency_ms"] == 999.0


def test_repository_health_check(tmp_path):
    """A working SQLite database should pass its health check."""
    repository = AlertRepository(tmp_path / "health.db")

    assert repository.health_check() is True


def test_repository_health_check_missing_table(tmp_path):
    """Health check should fail when the alert table is missing."""
    import sqlite3

    repository = AlertRepository(tmp_path / "missing_table.db")

    # Simulate a damaged or incomplete database schema.
    with sqlite3.connect(repository.db_path) as connection:
        connection.execute("DROP TABLE alert_events")

    assert repository.health_check() is False



def test_repository_health_check_read_only_database(
    tmp_path, monkeypatch
):
    """Health check should fail if SQLite rejects writes."""
    import sqlite3

    repository = AlertRepository(tmp_path / "readonly.db")

    def read_only_connection():
        return sqlite3.connect(
            f"file:{repository.db_path}?mode=ro",
            uri=True,
        )

    monkeypatch.setattr(
        repository,
        "_connect",
        read_only_connection,
    )

    assert repository.health_check() is False


def test_health_check_does_not_modify_alert_history(tmp_path):
    """Health checks must not add or remove real alert events."""
    repository = AlertRepository(tmp_path / "health_integrity.db")

    # Create two real alert transitions.
    repository.save(make_event("healthy"))
    repository.save(make_event("warning"))

    # Capture the database contents before the health check.
    events_before = repository.history()

    # Run the health check multiple times.
    for _ in range(5):
        assert repository.health_check() is True

    # The alert history must remain unchanged.
    events_after = repository.history()

    assert events_after == events_before
    assert len(events_after) == 2


import sys
import sqlite3
from pathlib import Path

sys.path.insert(
    0,
    str(Path(__file__).resolve().parents[1] / "backend")
)

import event_store


def test_save_and_load_request_id(tmp_path, monkeypatch):
    """Request IDs should persist in SQLite."""
    test_db = tmp_path / "incidents.db"

    monkeypatch.setattr(event_store, "DB_PATH", test_db)

    event = {
        "timestamp": "2026-10-30T12:00:00+00:00",
        "type": "database_failure",
        "message": "Database connection failed",
        "severity": "warning",
        "request_id": "test-request-123",
    }

    event_store.save_event(event)
    events = event_store.load_events()

    assert len(events) == 1
    assert events[0]["request_id"] == "test-request-123"


def test_old_database_migration(tmp_path, monkeypatch):
    """Existing incident records should survive migration."""
    test_db = tmp_path / "old_incidents.db"

    monkeypatch.setattr(event_store, "DB_PATH", test_db)

    with sqlite3.connect(test_db) as connection:
        connection.execute("""
            CREATE TABLE incidents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                type TEXT NOT NULL,
                message TEXT NOT NULL,
                severity TEXT NOT NULL
            )
        """)

        connection.execute(
            """
            INSERT INTO incidents
                (timestamp, type, message, severity)
            VALUES (?, ?, ?, ?)
            """,
            (
                "2026-10-29T12:00:00+00:00",
                "database_failure",
                "Previous failure",
                "warning",
            ),
        )

    event_store.initialize_event_store()
    events = event_store.load_events()

    assert len(events) == 1
    assert events[0]["message"] == "Previous failure"
    assert events[0]["request_id"] is None


def test_event_without_request_id(tmp_path, monkeypatch):
    """Background events should work without a Request ID."""
    test_db = tmp_path / "incidents.db"

    monkeypatch.setattr(event_store, "DB_PATH", test_db)

    event = {
        "timestamp": "2026-10-30T12:00:00+00:00",
        "type": "database_recovered",
        "message": "Database recovered",
        "severity": "info",
    }

    event_store.save_event(event)
    events = event_store.load_events()

    assert events[0]["request_id"] is None

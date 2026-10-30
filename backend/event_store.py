
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parents[1] / "data" / "incidents.db"


def initialize_event_store():
    """Create or migrate the incident table."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(DB_PATH) as connection:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS incidents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                type TEXT NOT NULL,
                message TEXT NOT NULL,
                severity TEXT NOT NULL,
                request_id TEXT
            )
        """)

        # Migrate databases created before request tracking.
        columns = {
            row[1]
            for row in connection.execute(
                "PRAGMA table_info(incidents)"
            ).fetchall()
        }

        if "request_id" not in columns:
            connection.execute(
                "ALTER TABLE incidents "
                "ADD COLUMN request_id TEXT"
            )


def save_event(event):
    """Save a reliability event to SQLite."""
    initialize_event_store()

    with sqlite3.connect(DB_PATH) as connection:
        connection.execute(
            """
            INSERT INTO incidents
                (timestamp, type, message, severity, request_id)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                event["timestamp"],
                event["type"],
                event["message"],
                event["severity"],
                event.get("request_id")
            )
        )


def load_events(limit=100):
    """Load the newest reliability events."""
    initialize_event_store()

    with sqlite3.connect(DB_PATH) as connection:
        connection.row_factory = sqlite3.Row

        rows = connection.execute(
            """
            SELECT timestamp, type, message,
                   severity, request_id
            FROM incidents
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,)
        ).fetchall()

    return [dict(row) for row in rows]

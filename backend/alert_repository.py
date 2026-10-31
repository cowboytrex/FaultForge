
import sqlite3
from pathlib import Path


class AlertRepository:
    """Store and retrieve performance alert transitions in SQLite."""

    def __init__(self, db_path="data/alerts.db"):
        self.db_path = Path(db_path)

        # Create the database directory if it doesn't exist.
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self._initialize_database()

    def _connect(self):
        """Open a connection to the SQLite database."""
        return sqlite3.connect(self.db_path, timeout=10)

    def _initialize_database(self):
        """Create the alerts table if it doesn't exist."""
        with self._connect() as connection:
            connection.execute("""
                CREATE TABLE IF NOT EXISTS alert_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    status TEXT NOT NULL,
                    previous_status TEXT,
                    p95_latency_ms REAL
                )
            """)


    def save(self, event):
        """Save an alert and enforce retention in one transaction."""
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO alert_events (
                    timestamp, status, previous_status, p95_latency_ms
                ) VALUES (?, ?, ?, ?)
                """,
                (
                    event["timestamp"],
                    event["status"],
                    event["previous_status"],
                    event["p95_latency_ms"],
                ),
            )

            # Keep only the newest 1,000 alerts.
            connection.execute(
                """
                DELETE FROM alert_events
                WHERE id NOT IN (
                    SELECT id
                    FROM alert_events
                    ORDER BY id DESC
                    LIMIT ?
                )
                """,
                (1000,),
            )


    def delete_old_events(self, keep_latest=1000):
        """Delete older alerts while keeping the newest events."""
        if (
            not isinstance(keep_latest, int)
            or isinstance(keep_latest, bool)
            or keep_latest < 1
        ):
            raise ValueError("keep_latest must be a positive integer")

        with self._connect() as connection:
            cursor = connection.execute(
                """
                DELETE FROM alert_events
                WHERE id NOT IN (
                    SELECT id
                    FROM alert_events
                    ORDER BY id DESC
                    LIMIT ?
                )
                """,
                (keep_latest,),
            )

            return cursor.rowcount

    
    def history(self, limit=100, status=None):
        """Retrieve recent alerts, optionally filtered by status."""
        if not isinstance(limit, int) or isinstance(limit, bool) or limit < 1:
            raise ValueError("limit must be a positive integer")

        valid_statuses = {"healthy", "warning", "critical", "no_data"}

        if status is not None and status not in valid_statuses:
            raise ValueError("Invalid alert status")

        query = """
            SELECT timestamp, status, previous_status, p95_latency_ms
            FROM alert_events
        """
        parameters = []

        if status is not None:
            query += " WHERE status = ?"
            parameters.append(status)

        query += " ORDER BY id DESC LIMIT ?"
        parameters.append(limit)

        with self._connect() as connection:
            rows = connection.execute(query, parameters).fetchall()

        # Return events in chronological order.
        rows.reverse()

        return [
            {
                "timestamp": row[0],
                "status": row[1],
                "previous_status": row[2],
                "p95_latency_ms": row[3],
            }
            for row in rows
        ]

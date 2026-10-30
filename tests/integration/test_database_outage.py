
import subprocess
import time
from datetime import datetime, timezone

import pytest

from backend.app import app, db_breaker


def docker_compose(*args):
    """Execute a Docker Compose command."""
    subprocess.run(
        ["docker", "compose", *args],
        check=True,
        timeout=60,
    )


def wait_for_postgres(timeout=60):
    """Wait until PostgreSQL accepts connections."""
    deadline = time.monotonic() + timeout

    while time.monotonic() < deadline:
        result = subprocess.run(
            [
                "docker", "compose", "exec", "-T",
                "postgres", "pg_isready",
                "-U", "faultforge",
                "-d", "faultforge",
            ],
            capture_output=True,
            timeout=10,
        )

        if result.returncode == 0:
            return

        time.sleep(1)

    raise TimeoutError("PostgreSQL did not recover in time")


@pytest.mark.integration
def test_real_database_outage_and_recovery():
    """Verify real database failure, Redis fallback, and recovery."""

    original_state = db_breaker.state
    original_count = db_breaker.failure_count
    original_time = db_breaker.last_failure_time

    database_stopped = False
    test_started_at = datetime.now(timezone.utc)

    try:
        # Reset the circuit breaker for this test.
        db_breaker.state = "CLOSED"
        db_breaker.failure_count = 0
        db_breaker.last_failure_time = None

        with app.test_client() as client:

            # 1. Confirm healthy database access and populate Redis.
            healthy = client.get("/api/services")

            assert healthy.status_code == 200
            assert healthy.get_json()["source"] == "primary"
            assert healthy.get_json()["cache_status"] == "available"

            # 2. Stop the real PostgreSQL container.
            # Mark it first so cleanup runs even if stop raises.
            database_stopped = True
            docker_compose("stop", "postgres")

            # 3. Trigger three database failures.
            for _ in range(3):
                response = client.get("/api/services")

                assert response.status_code == 200
                assert response.get_json()["source"] == "cache"
                assert response.get_json()["stale"] is True

            # 4. Confirm the circuit breaker opened.
            assert db_breaker.state == "OPEN"
            assert db_breaker.failure_count == 3

            # 5. Restart PostgreSQL.
            docker_compose("start", "postgres")
            wait_for_postgres()
            database_stopped = False

            # 6. Wait for the recovery timeout.
            time.sleep(db_breaker.recovery_timeout + 1)

            # 7. Verify successful recovery.
            recovered = client.get("/api/services")

            assert recovered.status_code == 200
            assert recovered.get_json()["source"] == "primary"
            assert recovered.get_json()["stale"] is False

            assert db_breaker.state == "CLOSED"
            assert db_breaker.failure_count == 0

            # 8. Verify incident events generated during this test.
            events_response = client.get("/api/events")

            assert events_response.status_code == 200

            events = events_response.get_json()["events"]

            recent_events = [
                event
                for event in events
                if datetime.fromisoformat(event["timestamp"])
                >= test_started_at
            ]

            # Sort events from oldest to newest.
            recent_events.sort(key=lambda event: event["timestamp"])

            event_types = [
                event["type"] for event in recent_events
            ]

            expected_events = [
                "database_failure",
                "circuit_opened",
                "recovery_attempt",
                "database_recovered",
            ]

            # Verify the sequence, allowing additional events.
            position = 0

            for event_type in event_types:
                if (
                    position < len(expected_events)
                    and event_type == expected_events[position]
                ):
                    position += 1

            assert position == len(expected_events), (
                f"Expected sequence: {expected_events}. "
                f"Actual events: {event_types}"
            )

    finally:
        try:
            # Always attempt to restore PostgreSQL.
            if database_stopped:
                docker_compose("start", "postgres")
                wait_for_postgres()
        finally:
            # Restore the original circuit-breaker state.
            db_breaker.state = original_state
            db_breaker.failure_count = original_count
            db_breaker.last_failure_time = original_time

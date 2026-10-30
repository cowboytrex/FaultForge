import pytest

from backend.app import app, db_breaker


@pytest.mark.integration
def test_real_postgres_returns_primary_data():
    """Verify the API retrieves records from real PostgreSQL."""

    original_state = db_breaker.state
    original_failures = db_breaker.failure_count
    original_failure_time = db_breaker.last_failure_time

    try:
        db_breaker.state = "CLOSED"
        db_breaker.failure_count = 0
        db_breaker.last_failure_time = None

        with app.test_client() as client:
            response = client.get("/api/services")

        assert response.status_code == 200

        data = response.get_json()

        assert data["source"] == "primary"
        assert data["stale"] is False
        assert data["system_status"] == "healthy"

        assert isinstance(data["data"], list)
        assert len(data["data"]) > 0

        service_names = [service["name"] for service in data["data"]]

        assert "Authentication" in service_names
        assert "Notifications" in service_names
        assert "Reporting" in service_names

    finally:
        db_breaker.state = original_state
        db_breaker.failure_count = original_failures
        db_breaker.last_failure_time = original_failure_time
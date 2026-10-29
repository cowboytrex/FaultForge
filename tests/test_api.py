
import sys
from pathlib import Path
from unittest.mock import patch

import fakeredis
import psycopg
import pytest
from redis.exceptions import RedisError


# Allow tests to import modules from the backend folder
sys.path.insert(
    0,
    str(Path(__file__).resolve().parents[1] / "backend")
)

from app import app, db_breaker
import fallback


# --------------------------------------------------
# TEST FIXTURES
# --------------------------------------------------

@pytest.fixture(autouse=True)
def mock_redis():
    """Give every test an isolated fake Redis server."""

    fake_client = fakeredis.FakeRedis(decode_responses=True)

    with patch("fallback.get_redis_client", return_value=fake_client):
        yield fake_client


@pytest.fixture(autouse=True)
def reset_circuit_breaker():
    """Reset circuit breaker state before and after every test."""

    def reset():
        db_breaker.state = "CLOSED"
        db_breaker.failure_count = 0
        db_breaker.last_failure_time = None

    reset()
    yield
    reset()


@pytest.fixture
def client():
    """Create a Flask test client."""

    app.config["TESTING"] = True
    return app.test_client()


# --------------------------------------------------
# TEST 1: NORMAL DATABASE REQUEST
# --------------------------------------------------

def test_normal_request(client):
    sample_data = [
        {"id": 1, "name": "Authentication", "status": "active"},
        {"id": 2, "name": "Notifications", "status": "active"},
        {"id": 3, "name": "Reporting", "status": "maintenance"}
    ]

    with patch(
        "app.get_services_from_db",
        return_value=sample_data
    ):
        response = client.get("/api/services")

    assert response.status_code == 200
    assert response.json["source"] == "primary"
    assert response.json["stale"] is False
    assert response.json["system_status"] == "healthy"
    assert response.json["data"] == sample_data


# --------------------------------------------------
# TEST 2: DATABASE FAILURE WITH REDIS CACHE
# --------------------------------------------------

def test_database_failure_with_cache(client):
    sample_data = [
        {"id": 1, "name": "Authentication", "status": "active"}
    ]

    # First request succeeds and populates Redis.
    with patch(
        "app.get_services_from_db",
        return_value=sample_data
    ):
        response = client.get("/api/services")
        assert response.status_code == 200

    # PostgreSQL becomes unavailable.
    with patch(
        "app.get_services_from_db",
        side_effect=psycopg.OperationalError(
            "Database unavailable"
        )
    ):
        response = client.get("/api/services")

    # Redis should serve the cached data.
    assert response.status_code == 200
    assert response.json["source"] == "cache"
    assert response.json["stale"] is True
    assert response.json["system_status"] == "degraded"
    assert response.json["data"] == sample_data


# --------------------------------------------------
# TEST 3: DATABASE FAILURE WITHOUT CACHE
# --------------------------------------------------

def test_database_failure_without_cache(client):

    with patch(
        "app.get_services_from_db",
        side_effect=psycopg.OperationalError(
            "Database unavailable"
        )
    ):
        response = client.get("/api/services")

    assert response.status_code == 503
    assert response.json["system_status"] == "unavailable"
    assert response.json["cache_status"] == "unavailable_or_empty"


# --------------------------------------------------
# TEST 4: REDIS FAILURE, DATABASE HEALTHY
# --------------------------------------------------

def test_redis_failure_with_healthy_database(client):
    sample_data = [
        {"id": 1, "name": "Authentication", "status": "active"}
    ]

    with patch(
        "app.get_services_from_db",
        return_value=sample_data
    ):
        with patch(
            "app.save_to_cache",
            side_effect=RedisError("Redis unavailable")
        ):
            response = client.get("/api/services")

    assert response.status_code == 200
    assert response.json["source"] == "primary"
    assert response.json["system_status"] == "healthy"
    assert response.json["cache_status"] == "unavailable"
    assert response.json["data"] == sample_data


# --------------------------------------------------
# TEST 5: BOTH POSTGRESQL AND REDIS FAIL
# --------------------------------------------------

def test_postgres_and_redis_failure(client):

    with patch(
        "app.get_services_from_db",
        side_effect=psycopg.OperationalError(
            "PostgreSQL unavailable"
        )
    ):
        with patch(
            "app.get_cached_services",
            side_effect=RedisError("Redis unavailable")
        ):
            response = client.get("/api/services")

    assert response.status_code == 503
    assert response.json["system_status"] == "unavailable"
    assert response.json["cache_status"] == "unavailable_or_empty"


# --------------------------------------------------
# TEST 6: CIRCUIT BREAKER OPENS
# --------------------------------------------------

def test_api_circuit_breaker_open(client):

    with patch(
        "app.get_services_from_db",
        side_effect=psycopg.OperationalError(
            "Database down"
        )
    ) as mock_db:

        # Three consecutive failures.
        for _ in range(3):
            response = client.get("/api/services")

            assert response.status_code == 503
            assert response.json["system_status"] == "unavailable"

        # The circuit should now be OPEN.
        assert db_breaker.state == "OPEN"
        assert mock_db.call_count == 3

        # Fourth request should skip PostgreSQL.
        response = client.get("/api/services")

        assert response.status_code == 503
        assert mock_db.call_count == 3


# --------------------------------------------------
# TEST 7: CIRCUIT BREAKER RECOVERS
# --------------------------------------------------

def test_api_circuit_breaker_recovery(client):

    sample_data = [
        {"id": 1, "name": "Authentication", "status": "active"}
    ]

    with patch("app.get_services_from_db") as mock_db:

        # Simulate PostgreSQL being unavailable.
        mock_db.side_effect = psycopg.OperationalError(
            "Database unavailable"
        )

        # Three failures open the circuit.
        for _ in range(3):
            response = client.get("/api/services")

            assert response.status_code == 503
            assert response.json["system_status"] == "unavailable"

        assert db_breaker.state == "OPEN"
        assert mock_db.call_count == 3

        # Simulate 11 seconds passing.
        db_breaker.last_failure_time -= 11

        # PostgreSQL becomes healthy again.
        mock_db.side_effect = None
        mock_db.return_value = sample_data

        # Circuit breaker attempts recovery.
        response = client.get("/api/services")

        assert response.status_code == 200
        assert response.json["source"] == "primary"
        assert response.json["stale"] is False
        assert response.json["data"] == sample_data

        # Circuit should return to CLOSED.
        assert db_breaker.state == "CLOSED"
        assert db_breaker.failure_count == 0
        assert mock_db.call_count == 4

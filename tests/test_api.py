import sys
import fakeredis
from pathlib import Path
from redis.exceptions import RedisError
from unittest.mock import patch

import pytest
import psycopg

sys.path.insert(
    0,
    str(Path(__file__).resolve().parents[1] / "backend")
)

import fallback
from app import app

@pytest.fixture(autouse=True)
def mock_redis():
    """Give each test an isolated fake Redis server."""
    fake_client = fakeredis.FakeRedis(decode_responses=True)

    with patch("fallback.get_redis_client", return_value=fake_client):
        yield


@pytest.fixture
def client():
    """Create a Flask test clients."""
    app.config["TESTING"] = True
    return app.test_client()


def test_normal_request(client):
    sample_data = [
        {"id": 1, "name": "Authentication", "status": "active"},
        {"id": 2, "name": "Notifications", "status": "active"},
        {"id": 3, "name": "Reporting", "status": "maintenance"}
    ]

    with patch("app.get_services_from_db", return_value=sample_data):
        response = client.get("/api/services")

    assert response.status_code == 200
    assert response.json["source"] == "primary"
    assert response.json["stale"] is False
    assert response.json["system_status"] == "healthy"
    assert response.json["data"] == sample_data


def test_database_failure_with_cache(client):
    sample_data = [
        {"id": 1, "name": "Authentication", "status": "active"}
    ]

    # First, populate the cache with a successful request.
    with patch("app.get_services_from_db", return_value=sample_data):
        client.get("/api/services")

    # Then simulate a real PostgreSQL connection error.
    with patch(
        "app.get_services_from_db",
        side_effect=psycopg.OperationalError("Database unavailable")
    ):
        response = client.get("/api/services")

    assert response.status_code == 200
    assert response.json["source"] == "cache"
    assert response.json["stale"] is True
    assert response.json["system_status"] == "degraded"
    assert response.json["data"] == sample_data


def test_database_failure_without_cache(client):
    with patch(
        "app.get_services_from_db",
        side_effect=psycopg.OperationalError("Database unavailable")
    ):
        response = client.get("/api/services")


def test_redis_failure_with_healthy_database(client):
    """The API should work even when Redis is unavailable."""
    sample_data = [
        {"id": 1, "name": "Authentication", "status": "active"}
    ]

    with patch("app.get_services_from_db", return_value=sample_data):
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


def test_postgres_and_redis_failure(client):
    """The API should return 503 when both services are unavailable."""

    with patch(
        "app.get_services_from_db",
        side_effect=psycopg.OperationalError("PostgreSQL unavailable")
    ):
        with patch(
            "app.get_cached_services",
            side_effect=RedisError("Redis unavailable")
        ):
            response = client.get("/api/services")

    assert response.status_code == 503
    assert response.json["system_status"] == "unavailable"
    assert response.json["cache_status"] == "unavailable_or_empty"


    assert response.status_code == 503
    assert response.json["system_status"] == "unavailable"

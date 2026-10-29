import sys
from pathlib import Path

sys.path.insert(
    0,
    str(Path(__file__).resolve().parents[1] / "backend")
)

import pytest
import fallback
from app import app

@pytest.fixture(autouse=True)
def reset_cache():
    """Ensure each test starts with an empty cache."""
    fallback.clear_cache()
    yield
    fallback.clear_cache()


@pytest.fixture
def client():
    """Create a Flask test clients."""
    app.config["TESTING"] = True
    return app.test_client()

def test_normal_request(client):
    response = client.get("/api/services")

    assert response.status_code == 500
    assert response.json["source"] == "primary"
    assert response.json["stale"] is False
    assert response.json["system_status"] == "healthy"

def test_database_failure_with_cache(client):
    # First, make a successful request to populate the cache
    client.get("/api/services")

    # Now simulate a database failure
    response = client.get("/api/services?fail=true")

    assert response.status_code == 200
    assert response.json["source"] == "cache"
    assert response.json["stale"] is True
    assert response.json["system_status"] == "degraded"
    assert len(response.json["data"]) == 3

def test_database_failure_without_cache(client):
    response = client.get("/api/services?fail=true")

    assert response.status_code == 503
    assert response.json["system_status"] == "unavailable"

import sys
import json
from pathlib import Path
from unittest.mock import MagicMock

sys.path.insert(
    0,
    str(Path(__file__).resolve().parents[1] / "backend")
)

import fallback


def test_save_to_cache(monkeypatch):
    """Saving services should serialize them as JSON."""

    mock_redis = MagicMock()

    monkeypatch.setattr(
        fallback,
        "get_redis_client",
        lambda: mock_redis,
    )

    services = [
        {"id": 1, "name": "Authentication", "status": "healthy"}
    ]

    fallback.save_to_cache(services)

    mock_redis.set.assert_called_once_with(
        fallback.CACHE_KEY,
        json.dumps(services),
    )


def test_get_cached_services_success(monkeypatch):
    """Cached JSON should be converted back into Python data."""

    mock_redis = MagicMock()

    services = [
        {"id": 1, "name": "Authentication", "status": "healthy"}
    ]

    mock_redis.get.return_value = json.dumps(services)

    monkeypatch.setattr(
        fallback,
        "get_redis_client",
        lambda: mock_redis,
    )

    result = fallback.get_cached_services()

    assert result == services
    mock_redis.get.assert_called_once_with(fallback.CACHE_KEY)


def test_get_cached_services_empty(monkeypatch):
    """An empty cache should return None."""

    mock_redis = MagicMock()
    mock_redis.get.return_value = None

    monkeypatch.setattr(
        fallback,
        "get_redis_client",
        lambda: mock_redis,
    )

    result = fallback.get_cached_services()

    assert result is None


def test_clear_cache(monkeypatch):
    """Clearing the cache should delete the Redis key."""

    mock_redis = MagicMock()

    monkeypatch.setattr(
        fallback,
        "get_redis_client",
        lambda: mock_redis,
    )

    fallback.clear_cache()

    mock_redis.delete.assert_called_once_with(
        fallback.CACHE_KEY
    )


import pytest


def test_redis_client_configuration(monkeypatch):
    """Redis client should use environment configuration."""

    from unittest.mock import MagicMock

    mock_redis_constructor = MagicMock()

    monkeypatch.setenv("REDIS_HOST", "test-redis")
    monkeypatch.setenv("REDIS_PORT", "6380")

    monkeypatch.setattr(
        fallback.redis,
        "Redis",
        mock_redis_constructor,
    )

    fallback.get_redis_client()

    mock_redis_constructor.assert_called_once_with(
        host="test-redis",
        port=6380,
        decode_responses=True,
        socket_connect_timeout=2,
        socket_timeout=2,
    )


def test_redis_error_propagates(monkeypatch):
    """Redis connection errors should reach the caller."""

    from redis.exceptions import RedisError

    def failing_client():
        raise RedisError("Redis unavailable")

    monkeypatch.setattr(
        fallback,
        "get_redis_client",
        failing_client,
    )

    with pytest.raises(RedisError, match="Redis unavailable"):
        fallback.get_cached_services()

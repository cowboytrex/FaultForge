
import json
import os

import redis

CACHE_KEY = "faultforge:services"


def get_redis_client():
    """Create a Redis client."""
    return redis.Redis(
        host=os.getenv("REDIS_HOST", "localhost"),
        port=int(os.getenv("REDIS_PORT", "6379")),
        decode_responses=True,
        socket_connect_timeout=2,
        socket_timeout=2,
    )


def save_to_cache(data):
    """Save the latest successful database response to Redis."""
    client = get_redis_client()
    client.set(CACHE_KEY, json.dumps(data))


def get_cached_services():
    """Retrieve the latest cached response from Redis."""
    client = get_redis_client()
    cached_data = client.get(CACHE_KEY)

    if cached_data is None:
        return None

    return json.loads(cached_data)


def clear_cache():
    """Remove cached data."""
    client = get_redis_client()
    client.delete(CACHE_KEY)

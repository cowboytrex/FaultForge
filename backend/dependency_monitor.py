
def check_dependencies(database_check, cache_check):
    """
    Check whether FaultForge can serve requests.

    These checks must not call the circuit breaker
    or modify its state.
    """

    database_available = False
    cache_available = False

    try:
        database_available = bool(database_check())
    except Exception:
        database_available = False

    # Only check Redis when PostgreSQL is unavailable.
    if not database_available:
        try:
            cache_available = bool(cache_check())
        except Exception:
            cache_available = False

    if database_available:
        return {
            "status": "ready",
            "system_status": "healthy",
        }, 200

    if cache_available:
        return {
            "status": "ready",
            "system_status": "degraded",
        }, 200

    return {
        "status": "not_ready",
        "system_status": "unavailable",
    }, 503

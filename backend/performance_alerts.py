
def evaluate_latency_alert(
    p95_latency_ms,
    warning_threshold_ms=200,
    critical_threshold_ms=500,
):
    """Evaluate API performance based on P95 latency."""

    if warning_threshold_ms < 0:
        raise ValueError("Warning threshold cannot be negative")

    if critical_threshold_ms <= warning_threshold_ms:
        raise ValueError(
            "Critical threshold must exceed warning threshold"
        )

    if p95_latency_ms < 0:
        raise ValueError("P95 latency cannot be negative")

    if p95_latency_ms > critical_threshold_ms:
        status = "critical"
        message = "Critical API latency detected"

    elif p95_latency_ms > warning_threshold_ms:
        status = "warning"
        message = "API latency exceeds warning threshold"

    else:
        status = "healthy"
        message = "API latency is within normal limits"

    return {
        "status": status,
        "message": message,
        "p95_latency_ms": p95_latency_ms,
        "warning_threshold_ms": warning_threshold_ms,
        "critical_threshold_ms": critical_threshold_ms,
    }

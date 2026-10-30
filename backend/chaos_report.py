
import math
from statistics import mean


def generate_chaos_report(results):
    """Summarize responses collected during a chaos experiment."""

    total = len(results)

    if total == 0:
        return {
            "total_requests": 0,
            "primary_successes": 0,
            "cache_fallbacks": 0,
            "unavailable_responses": 0,
            "availability_rate": 0.0,
            "average_latency_ms": 0.0,
            "p95_latency_ms": 0.0,
        }

    primary = sum(
        1 for result in results
        if result["source"] == "primary"
    )

    cache = sum(
        1 for result in results
        if result["source"] == "cache"
    )

    unavailable = sum(
        1 for result in results
        if result["status_code"] >= 500
    )

    available = sum(
        1 for result in results
        if 200 <= result["status_code"] < 300
    )

    latencies = sorted(
        result["latency_ms"] for result in results
    )

    p95_index = math.ceil(0.95 * total) - 1

    return {
        "total_requests": total,
        "primary_successes": primary,
        "cache_fallbacks": cache,
        "unavailable_responses": unavailable,
        "availability_rate": round(
            available / total * 100, 2
        ),
        "average_latency_ms": round(
            mean(latencies), 2
        ),
        "p95_latency_ms": round(
            latencies[p95_index], 2
        ),
    }

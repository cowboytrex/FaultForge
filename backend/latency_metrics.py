
import math


def calculate_latency_metrics(durations, slow_threshold_ms=500):
    """
    Calculate performance statistics from HTTP request durations.

    durations: list of response times in milliseconds
    slow_threshold_ms: duration considered a slow request
    """

    if slow_threshold_ms < 0:
        raise ValueError("slow_threshold_ms cannot be negative")

    if any(
        not math.isfinite(duration) or duration < 0
        for duration in durations
    ):
        raise ValueError("durations must be finite and nonnegative")

    if not durations:
        return {
            "total_requests": 0,
            "average_latency_ms": 0.0,
            "p95_latency_ms": 0.0,
            "max_latency_ms": 0.0,
            "slow_requests": 0,
        }

    sorted_durations = sorted(durations)
    total_requests = len(sorted_durations)

    average_latency = sum(sorted_durations) / total_requests

    # Nearest-rank percentile:
    # Find the value at the 95th percentile.
    p95_index = math.ceil(0.95 * total_requests) - 1
    p95_latency = sorted_durations[p95_index]

    slow_requests = sum(
        duration > slow_threshold_ms
        for duration in sorted_durations
    )

    return {
        "total_requests": total_requests,
        "average_latency_ms": round(average_latency, 2),
        "p95_latency_ms": round(p95_latency, 2),
        "max_latency_ms": round(sorted_durations[-1], 2),
        "slow_requests": slow_requests,
    }

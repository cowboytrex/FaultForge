
import time
import uuid

import requests

from backend.chaos_report import generate_chaos_report


def run_chaos_experiment(
    base_url="http://127.0.0.1:5001",
    total_requests=20,
):
    """Run an experiment and summarize its HTTP responses."""

    if not isinstance(total_requests, int) or isinstance(total_requests, bool):
        raise ValueError("total_requests must be an integer")

    if not 1 <= total_requests <= 1000:
        raise ValueError("total_requests must be between 1 and 1000")

    experiment_id = str(uuid.uuid4())
    results = []

    for _ in range(total_requests):
        start = time.perf_counter()

        try:
            response = requests.get(
                f"{base_url}/api/services",
                timeout=10,
            )

            latency_ms = (time.perf_counter() - start) * 1000

            try:
                payload = response.json()
            except ValueError:
                payload = {}

            results.append({
                "source": payload.get("source"),
                "status_code": response.status_code,
                "latency_ms": round(latency_ms, 2),
            })

        except requests.RequestException:
            latency_ms = (time.perf_counter() - start) * 1000

            results.append({
                "source": None,
                "status_code": 503,
                "latency_ms": round(latency_ms, 2),
            })

    return {
        "experiment_id": experiment_id,
        "configuration": {
            "base_url": base_url,
            "total_requests": total_requests,
        },
        "report": generate_chaos_report(results),
        "results": results,
    }

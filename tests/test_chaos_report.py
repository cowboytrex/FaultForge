
from backend.chaos_report import generate_chaos_report


def test_empty_experiment():
    report = generate_chaos_report([])

    assert report["total_requests"] == 0
    assert report["availability_rate"] == 0.0


def test_all_primary_successes():
    results = [
        {
            "source": "primary",
            "status_code": 200,
            "latency_ms": 100,
        },
        {
            "source": "primary",
            "status_code": 200,
            "latency_ms": 200,
        },
    ]

    report = generate_chaos_report(results)

    assert report["total_requests"] == 2
    assert report["primary_successes"] == 2
    assert report["cache_fallbacks"] == 0
    assert report["availability_rate"] == 100.0
    assert report["average_latency_ms"] == 150.0


def test_cache_fallbacks():
    results = [
        {
            "source": "primary",
            "status_code": 200,
            "latency_ms": 100,
        },
        {
            "source": "cache",
            "status_code": 200,
            "latency_ms": 20,
        },
    ]

    report = generate_chaos_report(results)

    assert report["primary_successes"] == 1
    assert report["cache_fallbacks"] == 1
    assert report["availability_rate"] == 100.0


def test_unavailable_response():
    results = [
        {
            "source": "primary",
            "status_code": 200,
            "latency_ms": 100,
        },
        {
            "source": None,
            "status_code": 503,
            "latency_ms": 50,
        },
    ]

    report = generate_chaos_report(results)

    assert report["unavailable_responses"] == 1
    assert report["availability_rate"] == 50.0


def test_p95_latency():
    results = [
        {
            "source": "primary",
            "status_code": 200,
            "latency_ms": i * 10,
        }
        for i in range(1, 21)
    ]

    report = generate_chaos_report(results)

    assert report["p95_latency_ms"] == 190


import pytest

from backend.latency_metrics import calculate_latency_metrics


def test_empty_latency_data():
    result = calculate_latency_metrics([])

    assert result["total_requests"] == 0
    assert result["average_latency_ms"] == 0.0
    assert result["p95_latency_ms"] == 0.0
    assert result["max_latency_ms"] == 0.0
    assert result["slow_requests"] == 0


def test_average_latency():
    result = calculate_latency_metrics([10, 20, 30, 40, 100])

    assert result["total_requests"] == 5
    assert result["average_latency_ms"] == 40.0


def test_p95_latency():
    durations = list(range(1, 101))

    result = calculate_latency_metrics(durations)

    assert result["p95_latency_ms"] == 95


def test_max_latency():
    result = calculate_latency_metrics([12, 85, 24])

    assert result["max_latency_ms"] == 85


def test_slow_requests():
    result = calculate_latency_metrics(
        [100, 200, 600, 800],
        slow_threshold_ms=500,
    )

    assert result["slow_requests"] == 2


def test_negative_duration_rejected():
    with pytest.raises(ValueError):
        calculate_latency_metrics([10, -5, 20])


def test_invalid_threshold_rejected():
    with pytest.raises(ValueError):
        calculate_latency_metrics(
            [10, 20],
            slow_threshold_ms=-1,
        )


def test_nonfinite_duration_rejected():
    with pytest.raises(ValueError):
        calculate_latency_metrics([10, float("nan")])

    with pytest.raises(ValueError):
        calculate_latency_metrics([10, float("inf")])

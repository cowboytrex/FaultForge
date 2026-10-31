
import pytest
from backend.performance_alerts import evaluate_latency_alert


def test_healthy_latency():
    result = evaluate_latency_alert(100)

    assert result["status"] == "healthy"
    assert result["p95_latency_ms"] == 100


def test_warning_latency():
    result = evaluate_latency_alert(350)

    assert result["status"] == "warning"
    assert result["p95_latency_ms"] == 350


def test_critical_latency():
    result = evaluate_latency_alert(750)

    assert result["status"] == "critical"
    assert result["p95_latency_ms"] == 750


def test_warning_boundary():
    result = evaluate_latency_alert(200)

    assert result["status"] == "healthy"


def test_critical_boundary():
    result = evaluate_latency_alert(500)

    assert result["status"] == "warning"


def test_custom_thresholds():
    result = evaluate_latency_alert(
        150,
        warning_threshold_ms=100,
        critical_threshold_ms=200,
    )

    assert result["status"] == "warning"


def test_negative_latency():
    with pytest.raises(ValueError):
        evaluate_latency_alert(-10)


def test_invalid_warning_threshold():
    with pytest.raises(ValueError):
        evaluate_latency_alert(
            100,
            warning_threshold_ms=-1,
        )


def test_invalid_critical_threshold():
    with pytest.raises(ValueError):
        evaluate_latency_alert(
            100,
            warning_threshold_ms=500,
            critical_threshold_ms=200,
        )


import pytest

from backend.chaos_engine import ChaosEngine


def test_chaos_disabled():
    engine = ChaosEngine()
    assert engine.execute(lambda: "success") == "success"


def test_latency_injection(monkeypatch):
    engine = ChaosEngine()
    engine.configure(enabled=True, latency_ms=2000)

    delays = []
    monkeypatch.setattr("backend.chaos_engine.time.sleep", delays.append)

    assert engine.execute(lambda: "success") == "success"
    assert delays == [2.0]


def test_forced_failure():
    engine = ChaosEngine()
    engine.configure(enabled=True, failure_rate=1.0)

    with pytest.raises(ConnectionError):
        engine.execute(lambda: "success")


def test_zero_failure_rate():
    engine = ChaosEngine()
    engine.configure(enabled=True, failure_rate=0.0)

    assert engine.execute(lambda: "success") == "success"


def test_invalid_latency():
    engine = ChaosEngine()

    with pytest.raises(ValueError):
        engine.configure(enabled=True, latency_ms=-100)


def test_invalid_failure_rate():
    engine = ChaosEngine()

    with pytest.raises(ValueError):
        engine.configure(enabled=True, failure_rate=1.5)

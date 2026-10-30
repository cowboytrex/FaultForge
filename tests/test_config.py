
import sys
from pathlib import Path

sys.path.insert(
    0,
    str(Path(__file__).resolve().parents[1] / "backend")
)

from config import Config


def test_fault_injection_disabled_by_default(monkeypatch):
    """Fault injection should be disabled by default."""
    monkeypatch.delenv(
        "ENABLE_FAULT_INJECTION",
        raising=False
    )

    config = Config.from_environment()

    assert config["ENABLE_FAULT_INJECTION"] is False


def test_fault_injection_enabled(monkeypatch):
    """Fault injection can be enabled explicitly."""
    monkeypatch.setenv(
        "ENABLE_FAULT_INJECTION",
        "true"
    )

    config = Config.from_environment()

    assert config["ENABLE_FAULT_INJECTION"] is True


def test_fault_injection_disabled_explicitly(monkeypatch):
    """Setting false must disable fault injection."""
    monkeypatch.setenv(
        "ENABLE_FAULT_INJECTION",
        "false"
    )

    config = Config.from_environment()

    assert config["ENABLE_FAULT_INJECTION"] is False


def test_debug_disabled_by_default(monkeypatch):
    """Debug mode should be disabled by default."""
    monkeypatch.delenv(
        "FLASK_DEBUG",
        raising=False
    )

    config = Config.from_environment()

    assert config["DEBUG"] is False

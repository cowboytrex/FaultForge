
import pytest

from backend.alert_history import AlertHistory


def test_records_first_alert():
    history = AlertHistory()

    result = history.record("healthy", 25)

    assert result is True
    assert len(history.history()) == 1
    assert history.history()[0]["status"] == "healthy"


def test_records_status_transition():
    history = AlertHistory()

    history.record("healthy", 25)
    history.record("warning", 350)

    events = history.history()

    assert len(events) == 2
    assert events[1]["previous_status"] == "healthy"
    assert events[1]["status"] == "warning"


def test_prevents_duplicate_alerts():
    history = AlertHistory()

    history.record("warning", 350)
    result = history.record("warning", 400)

    assert result is False
    assert len(history.history()) == 1


def test_records_recovery():
    history = AlertHistory()

    history.record("critical", 750)
    history.record("healthy", 50)

    events = history.history()

    assert events[1]["previous_status"] == "critical"
    assert events[1]["status"] == "healthy"


def test_history_respects_max_events():
    history = AlertHistory(max_events=2)

    history.record("healthy", 25)
    history.record("warning", 350)
    history.record("critical", 750)

    events = history.history()

    assert len(events) == 2
    assert [event["status"] for event in events] == [
        "warning",
        "critical",
    ]


def test_invalid_status():
    history = AlertHistory()

    with pytest.raises(ValueError):
        history.record("unknown", 100)


def test_invalid_max_events():
    with pytest.raises(ValueError):
        AlertHistory(max_events=0)


def test_history_returns_independent_copies():
    history = AlertHistory()
    history.record("healthy", 25)

    events = history.history()
    events[0]["status"] = "critical"

    assert history.history()[0]["status"] == "healthy"


from unittest.mock import Mock, patch

import pytest
import requests

from backend.chaos_runner import run_chaos_experiment


@patch("backend.chaos_runner.requests.get")
def test_successful_requests(mock_get):
    response = Mock()
    response.status_code = 200
    response.json.return_value = {
        "source": "primary",
        "system_status": "healthy",
    }
    mock_get.return_value = response

    experiment = run_chaos_experiment(total_requests=3)

    assert experiment["experiment_id"]
    assert experiment["report"]["total_requests"] == 3
    assert experiment["report"]["primary_successes"] == 3
    assert experiment["report"]["availability_rate"] == 100.0
    assert len(experiment["results"]) == 3
    assert mock_get.call_count == 3


@patch("backend.chaos_runner.requests.get")
def test_cache_fallback(mock_get):
    response = Mock()
    response.status_code = 200
    response.json.return_value = {
        "source": "cache",
        "system_status": "degraded",
    }
    mock_get.return_value = response

    experiment = run_chaos_experiment(total_requests=2)

    assert experiment["report"]["cache_fallbacks"] == 2
    assert experiment["report"]["availability_rate"] == 100.0


@patch("backend.chaos_runner.requests.get")
def test_database_unavailable(mock_get):
    response = Mock()
    response.status_code = 503
    response.json.return_value = {
        "error": "Database unavailable",
    }
    mock_get.return_value = response

    experiment = run_chaos_experiment(total_requests=2)

    assert experiment["report"]["unavailable_responses"] == 2
    assert experiment["report"]["availability_rate"] == 0.0


@patch("backend.chaos_runner.requests.get")
def test_connection_error(mock_get):
    mock_get.side_effect = requests.ConnectionError(
        "Connection refused"
    )

    experiment = run_chaos_experiment(total_requests=2)

    assert experiment["report"]["total_requests"] == 2
    assert experiment["report"]["unavailable_responses"] == 2
    assert experiment["report"]["availability_rate"] == 0.0


@pytest.mark.parametrize("count", [0, -1, 1001, 1.5, True])
def test_invalid_request_count(count):
    with pytest.raises(ValueError):
        run_chaos_experiment(total_requests=count)

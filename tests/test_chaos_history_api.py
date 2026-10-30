
from unittest.mock import patch

import pytest

from backend.app import app


@pytest.fixture
def client():
    app.config["TESTING"] = True

    with app.test_client() as test_client:
        yield test_client


@patch("backend.app.load_experiments")
def test_get_empty_experiment_history(mock_load, client):
    mock_load.return_value = []

    response = client.get("/api/chaos/experiments")

    assert response.status_code == 200
    assert response.get_json() == {
        "total": 0,
        "experiments": [],
    }


@patch("backend.app.load_experiments")
def test_get_saved_experiments(mock_load, client):
    experiments = [
        {
            "experiment_id": "experiment-001",
            "report": {"availability_rate": 100.0},
        },
        {
            "experiment_id": "experiment-002",
            "report": {"availability_rate": 95.0},
        },
    ]

    mock_load.return_value = experiments

    response = client.get("/api/chaos/experiments")

    assert response.status_code == 200
    assert response.get_json() == {
        "total": 2,
        "experiments": experiments,
    }


@patch("backend.app.load_experiments")
def test_experiment_history_file_error(mock_load, client):
    mock_load.side_effect = OSError("File unavailable")

    response = client.get("/api/chaos/experiments")

    assert response.status_code == 500
    assert response.get_json() == {
        "error": "Unable to load experiment history",
    }


@patch("backend.app.load_experiments")
def test_experiment_history_invalid_data(mock_load, client):
    mock_load.side_effect = ValueError("Invalid history")

    response = client.get("/api/chaos/experiments")

    assert response.status_code == 500
    assert response.get_json() == {
        "error": "Unable to load experiment history",
    }

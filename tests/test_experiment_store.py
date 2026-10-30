
import json

import pytest

from backend.experiment_store import (
    save_experiment,
    load_experiments,
)


def test_load_empty_history(tmp_path):
    history_file = tmp_path / "experiments.json"

    experiments = load_experiments(history_file)

    assert experiments == []


def test_save_single_experiment(tmp_path):
    history_file = tmp_path / "experiments.json"

    experiment = {
        "experiment_id": "experiment-001",
        "report": {
            "total_requests": 20,
            "availability_rate": 100.0,
        },
    }

    save_experiment(experiment, history_file)

    saved = load_experiments(history_file)

    assert len(saved) == 1
    assert saved[0] == experiment


def test_save_multiple_experiments(tmp_path):
    history_file = tmp_path / "experiments.json"

    first = {"experiment_id": "experiment-001"}
    second = {"experiment_id": "experiment-002"}

    save_experiment(first, history_file)
    save_experiment(second, history_file)

    saved = load_experiments(history_file)

    assert len(saved) == 2
    assert saved[0] == first
    assert saved[1] == second


def test_invalid_history_format(tmp_path):
    history_file = tmp_path / "experiments.json"

    history_file.write_text(
        json.dumps({"invalid": "format"}),
        encoding="utf-8",
    )

    with pytest.raises(ValueError):
        load_experiments(history_file)


def test_history_persists_between_reads(tmp_path):
    history_file = tmp_path / "experiments.json"

    save_experiment(
        {"experiment_id": "experiment-003"},
        history_file,
    )

    first_read = load_experiments(history_file)
    second_read = load_experiments(history_file)

    assert first_read == second_read
    assert len(second_read) == 1

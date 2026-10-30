
import json
from pathlib import Path

DEFAULT_HISTORY_PATH = Path("data/chaos_experiments.json")


def save_experiment(experiment, path=DEFAULT_HISTORY_PATH):
    """Save an experiment without overwriting previous runs."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    experiments = load_experiments(path)
    experiments.append(experiment)

    with path.open("w", encoding="utf-8") as file:
        json.dump(experiments, file, indent=2)

    return experiment


def load_experiments(path=DEFAULT_HISTORY_PATH):
    """Load previously saved experiments."""
    path = Path(path)

    if not path.exists():
        return []

    with path.open("r", encoding="utf-8") as file:
        experiments = json.load(file)

    if not isinstance(experiments, list):
        raise ValueError("Experiment history must be a JSON list")

    return experiments

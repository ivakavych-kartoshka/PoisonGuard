from poisonguard.experiments.run_calibration import run_calibration
from poisonguard.experiments.run_evaluation import run_evaluation
from poisonguard.utils.io import load_config


def test_synthetic_calibration_and_evaluation_are_labeled() -> None:
    config = load_config("configs/synthetic_demo.yaml")
    calibration = run_calibration(config)
    evaluation = run_evaluation(config)
    assert "not a paper result" in str(calibration["label"])
    assert evaluation["real_experiment"] is False
    assert {row["method"] for row in evaluation["methods"]} >= {"no_defense", "poisonguard"}

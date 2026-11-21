from poisonguard.experiments.run_evaluation import run_evaluation
from poisonguard.utils.io import load_config


def test_fixed_seed_reproduces_numerical_results() -> None:
    config = load_config("configs/synthetic_demo.yaml")
    assert run_evaluation(config) == run_evaluation(config)

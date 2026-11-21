from __future__ import annotations

from typing import Any
import numpy as np

from poisonguard.data.synthetic import generate_synthetic_events
from poisonguard.models.adapters import DeterministicAdapterTrainer


def run_calibration(config: dict[str, Any]) -> dict[str, float | str]:
    """Empirical benign audit calibration; no conformal guarantee is claimed."""
    events, _ = generate_synthetic_events(int(config.get("seed", 7)),
                                          int(config["synthetic"]["benign_count"]), 0)
    trainer = DeterministicAdapterTrainer(int(config["model"]["dimension"]),
                                          float(config["model"]["clip_norm"]))
    norms = [float(np.linalg.norm(trainer.train(np.zeros(trainer.dimension), [event],
                                                float(config["training"]["step_size"]))))
             for event in events]
    quantile = float(config.get("calibration", {}).get("quantile", 0.95))
    return {"label": "synthetic smoke-test output, not a paper result",
            "calibration_kind": "empirical_benign_quantile_no_formal_coverage_claim",
            "max_update_norm": float(np.quantile(norms, quantile)), "quantile": quantile,
            "sample_count": len(norms)}

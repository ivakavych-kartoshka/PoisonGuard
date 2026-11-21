from __future__ import annotations

from typing import Any
from .common import LABEL
from .run_evaluation import run_evaluation


def run_ablation(config: dict[str, Any]) -> dict[str, Any]:
    result = run_evaluation(config)
    return {"label": LABEL, "ablations": result["methods"],
            "note": "Policy-level synthetic ablations; hardware and detector ablations require real assets."}

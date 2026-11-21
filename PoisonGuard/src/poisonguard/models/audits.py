from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence
import numpy as np


@dataclass(frozen=True)
class AuditThresholds:
    max_behavior_score: float = 1.0
    max_update_norm: float = 1.0


def audit_signals(active: Sequence[float], candidate: Sequence[float], probes: np.ndarray) -> tuple[float, float]:
    active_arr, candidate_arr = np.asarray(active), np.asarray(candidate)
    behavior = float(np.max(np.abs(probes @ (candidate_arr - active_arr)))) if len(probes) else 0.0
    return behavior, float(np.linalg.norm(candidate_arr - active_arr))

"""Small numerical references; not a pretrained SLM implementation."""

from __future__ import annotations

import hashlib
from typing import Sequence
import numpy as np

from poisonguard.data.schemas import Event


def apply_lora(weight: np.ndarray, a: np.ndarray, b: np.ndarray, alpha: float) -> np.ndarray:
    """Paper Eq. (2): return W + alpha * B A / r with dimension checks."""
    if weight.ndim != 2 or a.ndim != 2 or b.ndim != 2:
        raise ValueError("W, A, and B must be matrices")
    rank = a.shape[0]
    if rank <= 0 or b.shape[1] != rank or weight.shape != (b.shape[0], a.shape[1]):
        raise ValueError("incompatible LoRA dimensions")
    return weight + float(alpha) * (b @ a) / rank


class DeterministicAdapterTrainer:
    """Deterministic vector-state trainer for state-machine tests and smoke demos."""

    def __init__(self, dimension: int = 8, clip_norm: float = 1.0) -> None:
        if dimension <= 0 or clip_norm <= 0:
            raise ValueError("dimension and clip_norm must be positive")
        self.dimension, self.clip_norm = dimension, clip_norm

    def feature(self, event: Event) -> np.ndarray:
        digest = hashlib.sha256(event.payload.encode("utf-8")).digest()
        values = np.frombuffer(digest[: self.dimension], dtype=np.uint8).astype(float)
        values = (values - 127.5) / 127.5
        norm = np.linalg.norm(values)
        return values * min(1.0, self.clip_norm / max(norm, 1e-12))

    def train(self, parameters: Sequence[float], events: Sequence[Event], step_size: float = 0.1) -> np.ndarray:
        if step_size < 0:
            raise ValueError("step_size must be nonnegative")
        current = np.asarray(parameters, dtype=float).copy()
        if current.shape != (self.dimension,):
            raise ValueError(f"parameters must have shape ({self.dimension},)")
        if events:
            current += step_size * np.mean([self.feature(event) for event in events], axis=0)
        return current

    def behavior_score(self, parameters: Sequence[float], probes: np.ndarray) -> float:
        params = np.asarray(parameters, dtype=float)
        if probes.ndim != 2 or probes.shape[1] != self.dimension:
            raise ValueError("probe matrix has wrong shape")
        return float(np.max(np.abs(probes @ params))) if len(probes) else 0.0

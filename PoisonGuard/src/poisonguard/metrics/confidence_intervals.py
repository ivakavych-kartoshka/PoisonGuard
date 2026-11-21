from __future__ import annotations

from collections.abc import Callable, Sequence
import math
import numpy as np


def bootstrap_interval(values: Sequence[float], statistic: Callable[[np.ndarray], float] = np.mean,
                       confidence: float = 0.95, resamples: int = 2000,
                       seed: int = 0) -> tuple[float, float]:
    """Percentile bootstrap CI for user/seed-level observations."""
    if not values:
        return math.nan, math.nan
    if not 0 < confidence < 1 or resamples <= 0:
        raise ValueError("invalid bootstrap settings")
    array = np.asarray(values, dtype=float)
    rng = np.random.default_rng(seed)
    estimates = [statistic(rng.choice(array, size=len(array), replace=True)) for _ in range(resamples)]
    tail = (1 - confidence) / 2
    return float(np.quantile(estimates, tail)), float(np.quantile(estimates, 1 - tail))

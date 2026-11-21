"""Small aggregation helpers for real experiment runs."""

from __future__ import annotations

import statistics
from typing import Iterable, Sequence


def median_iqr_count(values: Sequence[float]) -> dict[str, float | int | None]:
    data = [float(value) for value in values]
    if not data:
        return {"count": 0, "median": None, "iqr": None, "min": None, "max": None}
    if len(data) == 1:
        iqr = 0.0
    else:
        try:
            q1, _, q3 = statistics.quantiles(data, n=4, method="inclusive")
            iqr = q3 - q1
        except statistics.StatisticsError:
            iqr = max(data) - min(data)
    return {
        "count": len(data),
        "median": statistics.median(data),
        "iqr": iqr,
        "min": min(data),
        "max": max(data),
    }


def bootstrap_mean_ci(values: Sequence[float], samples: int = 1000, seed: int = 0) -> dict[str, float | int]:
    """A tiny deterministic bootstrap interval for pilot planning only."""
    import random

    data = [float(value) for value in values]
    if not data:
        return {"count": 0, "mean": 0.0, "ci_low": 0.0, "ci_high": 0.0}
    rng = random.Random(seed)
    means = []
    for _ in range(samples):
        draw = [rng.choice(data) for _ in data]
        means.append(sum(draw) / len(draw))
    means.sort()
    low = means[int(0.025 * (samples - 1))]
    high = means[int(0.975 * (samples - 1))]
    return {"count": len(data), "mean": sum(data) / len(data),
            "ci_low": low, "ci_high": high}
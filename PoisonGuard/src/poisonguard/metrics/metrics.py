"""Paper security, policy, utility, recovery, and systems metrics."""

from __future__ import annotations

from collections.abc import Sequence
import math
import numpy as np

from poisonguard.data.schemas import Decision


def _mean(values: Sequence[float | bool]) -> float:
    return float(np.mean(values)) if len(values) else math.nan


def attack_success_rate(successes: Sequence[bool]) -> float:
    """Paper Eq. (10): trigger-conditioned attack success rate."""
    return _mean(successes)


def clean_trigger_false_activation(activations: Sequence[bool]) -> float:
    """False target activation on clean-trigger collision probes."""
    return _mean(activations)


def laundering_persistence(post_deletion_asr: float, clean_asr: float) -> float:
    """Paper Eq. (10): LP = ASR(post-deletion) - ASR(clean)."""
    return float(post_deletion_asr - clean_asr)


def false_quarantine_rate(benign_decisions: Sequence[Decision]) -> float:
    """Paper Eq. (11), counting quarantine and deny as benign rejection."""
    return _mean([item is not Decision.ALLOW for item in benign_decisions])


def false_admission_rate(malicious_decisions: Sequence[Decision]) -> float:
    return _mean([item is Decision.ALLOW for item in malicious_decisions])


def admission_rate(decisions: Sequence[Decision]) -> float:
    return _mean([item is Decision.ALLOW for item in decisions])


def retrieval_rate(retrieved: Sequence[bool]) -> float:
    return _mean(retrieved)


def user_confirmation_burden(confirmations: int, eligible_events: int) -> float:
    if confirmations < 0 or eligible_events < 0:
        raise ValueError("counts must be nonnegative")
    return confirmations / eligible_events if eligible_events else math.nan


def accuracy(y_true: Sequence[object], y_pred: Sequence[object]) -> float:
    if len(y_true) != len(y_pred):
        raise ValueError("labels and predictions must have equal length")
    return _mean([a == b for a, b in zip(y_true, y_pred)])


def binary_f1(y_true: Sequence[bool], y_pred: Sequence[bool]) -> float:
    if len(y_true) != len(y_pred):
        raise ValueError("labels and predictions must have equal length")
    tp = sum(a and b for a, b in zip(y_true, y_pred))
    fp = sum((not a) and b for a, b in zip(y_true, y_pred))
    fn = sum(a and (not b) for a, b in zip(y_true, y_pred))
    denominator = 2 * tp + fp + fn
    return 2 * tp / denominator if denominator else math.nan


def mean_reciprocal_rank(relevant_ranks: Sequence[int | None]) -> float:
    """Mean reciprocal rank, with `None` representing no retrieved relevant item."""
    if any(rank is not None and rank <= 0 for rank in relevant_ranks):
        raise ValueError("ranks must be positive")
    return _mean([0.0 if rank is None else 1.0 / rank for rank in relevant_ranks])


def parameter_distance(left: Sequence[float], right: Sequence[float]) -> float:
    return float(np.linalg.norm(np.asarray(left, dtype=float) - np.asarray(right, dtype=float)))


def checkpoint_hash_equal(left: str, right: str) -> bool:
    return bool(left) and left == right


def output_distribution_distance(left: Sequence[float], right: Sequence[float]) -> float:
    a, b = np.asarray(left, dtype=float), np.asarray(right, dtype=float)
    if a.shape != b.shape or a.size == 0:
        raise ValueError("distributions must be non-empty and shape-matched")
    if np.any(a < 0) or np.any(b < 0) or not np.isclose(a.sum(), 1) or not np.isclose(b.sum(), 1):
        raise ValueError("inputs must be probability distributions")
    midpoint = 0.5 * (a + b)
    def kl(x: np.ndarray, y: np.ndarray) -> float:
        mask = x > 0
        return float(np.sum(x[mask] * np.log(x[mask] / y[mask])))
    return 0.5 * kl(a, midpoint) + 0.5 * kl(b, midpoint)


def contaminated_displacement_bound(fraction: float, gradient_bound: float,
                                     step_sizes: Sequence[float]) -> float:
    """Paper Eq. (13): 2 alpha G sum(eta_h); this is not an ASR bound."""
    if not 0 <= fraction <= 1 or gradient_bound < 0 or any(x < 0 for x in step_sizes):
        raise ValueError("invalid bound arguments")
    return float(2 * fraction * gradient_bound * sum(step_sizes))


def storage_upper_bound(n: int, degree: int, vertex_bytes: int, edge_bytes: int,
                        checkpoints: int, lora_scalars: int, scalar_bytes: int,
                        index_bytes: int = 0, replay_bytes: int = 0) -> int:
    """Paper Eq. (14): structural/checkpoint storage upper bound in bytes."""
    values = (n, degree, vertex_bytes, edge_bytes, checkpoints, lora_scalars,
              scalar_bytes, index_bytes, replay_bytes)
    if any(value < 0 for value in values):
        raise ValueError("storage terms must be nonnegative")
    return n * vertex_bytes + n * degree * edge_bytes + checkpoints * lora_scalars * scalar_bytes + index_bytes + replay_bytes


def deployment_objective(attack_risk: float, utility_delta: float, fqr: float,
                         lambda_utility: float, lambda_quarantine: float) -> float:
    """Paper Eq. (12) objective value; resource constraints are checked separately."""
    return float(attack_risk + lambda_utility * utility_delta + lambda_quarantine * fqr)


def summarize_trials(values: Sequence[float]) -> dict[str, float | int]:
    if not values:
        return {"median": math.nan, "q1": math.nan, "q3": math.nan, "count": 0}
    array = np.asarray(values, dtype=float)
    return {"median": float(np.median(array)), "q1": float(np.quantile(array, 0.25)),
            "q3": float(np.quantile(array, 0.75)), "count": len(values)}

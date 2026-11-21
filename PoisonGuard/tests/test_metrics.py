import math
import pytest
from poisonguard.data.schemas import Decision
from poisonguard.metrics.metrics import *  # noqa: F403


def test_security_and_policy_metrics() -> None:
    assert attack_success_rate([True, False, True]) == pytest.approx(2 / 3)  # noqa: F405
    assert laundering_persistence(0.7, 0.1) == pytest.approx(0.6)  # noqa: F405
    assert false_quarantine_rate([Decision.ALLOW, Decision.DENY]) == 0.5  # noqa: F405
    assert false_admission_rate([Decision.ALLOW, Decision.DENY]) == 0.5  # noqa: F405
    assert clean_trigger_false_activation([False, True]) == 0.5  # noqa: F405
    assert user_confirmation_burden(2, 4) == 0.5  # noqa: F405
    assert mean_reciprocal_rank([1, 2, None]) == pytest.approx(0.5)  # noqa: F405
    assert checkpoint_hash_equal("abc", "abc")  # noqa: F405
    assert math.isnan(attack_success_rate([]))  # noqa: F405


def test_bounds_and_distances() -> None:
    assert contaminated_displacement_bound(0.25, 2, [0.1, 0.2]) == pytest.approx(0.3)  # noqa: F405
    assert storage_upper_bound(10, 2, 3, 4, 1, 5, 2, 7, 9) == 136  # noqa: F405
    assert parameter_distance([0, 0], [3, 4]) == 5  # noqa: F405
    assert output_distribution_distance([0.5, 0.5], [0.5, 0.5]) == 0  # noqa: F405

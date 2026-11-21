from poisonguard.metrics.aggregation import bootstrap_mean_ci, median_iqr_count


def test_median_iqr_count() -> None:
    result = median_iqr_count([1.0, 2.0, 3.0, 4.0])
    assert result["count"] == 4
    assert result["median"] == 2.5
    assert result["min"] == 1.0
    assert result["max"] == 4.0


def test_empty() -> None:
    assert median_iqr_count([])["count"] == 0


def test_bootstrap() -> None:
    result = bootstrap_mean_ci([1.0, 2.0, 3.0], samples=100, seed=1)
    assert result["count"] == 3
    assert result["ci_low"] <= result["mean"] <= result["ci_high"]
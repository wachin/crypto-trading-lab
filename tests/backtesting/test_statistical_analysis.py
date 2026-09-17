"""Tests for statistical analysis (ROADMAP.md chapter 43)."""

from __future__ import annotations

import random
import statistics

import pytest

from crypto_trading_lab.backtesting.statistical_analysis import (
    BootstrapConfidence,
    AutocorrelationResult,
    DistributionStats,
    bootstrap_confidence_interval,
    check_autocorrelation,
    compute_distribution_stats,
    probabilistic_sharpe_ratio,
    warn_multiple_testing,
    warn_small_sample,
)


def test_empty_list_raises():
    with pytest.raises(ValueError):
        compute_distribution_stats([])


def test_distribution_stats_basic():
    values = [1.0, 2.0, 3.0, 4.0, 5.0]
    stats = compute_distribution_stats(values)
    
    assert stats.n == 5
    assert stats.mean == 3.0
    assert stats.median == 3.0
    assert stats.min == 1.0
    assert stats.max == 5.0


def test_distribution_stats_skewness():
    # Right-skewed distribution
    values = [1.0, 1.0, 1.0, 1.0, 10.0]
    stats = compute_distribution_stats(values)
    assert stats.skewness > 0  # Positive skew


def test_distribution_stats_kurtosis():
    # Distribution with extreme outliers (spike at mean + outliers)
    values = [1.0] * 50 + [100.0, -100.0]
    stats = compute_distribution_stats(values)
    # Heavy-tailed distributions have positive excess kurtosis
    assert stats.kurtosis > 0


def test_autocorrelation_small_sample():
    values = [1.0, 2.0, 3.0]
    result = check_autocorrelation(values)
    
    assert isinstance(result, AutocorrelationResult)
    assert "too small" in result.warning.lower()


def test_autocorrelation_independent():
    # Independent noise should have near-zero autocorrelation
    import random
    random.seed(42)
    values = [random.gauss(0, 1) for _ in range(1000)]
    result = check_autocorrelation(values)
    
    assert abs(result.lag_1) < 0.1  # Close to zero


def test_autocorrelation_dependent():
    # AR(1) process with positive autocorrelation
    values = []
    x = 0
    for _ in range(1000):
        x = 0.8 * x + 0.1 * random.gauss(0, 1)
        values.append(x)
    
    result = check_autocorrelation(values)
    assert result.lag_1 > 0.3  # Should detect positive autocorrelation


def test_bootstrap_confidence_interval():
    values = [1.0, 2.0, 3.0, 4.0, 5.0]
    
    result = bootstrap_confidence_interval(
        values,
        statistic_fn=statistics.mean,
        confidence_level=0.95,
        n_resamples=100,
        seed=42,
    )
    
    assert isinstance(result, BootstrapConfidence)
    assert result.n_resamples == 100
    assert result.lower <= result.upper
    # Mean should be close to 3.0
    assert 2.0 < result.statistic < 4.0


def test_bootstrap_interval_covers_true_mean():
    # With enough resamples, CI should cover true mean most of the time
    import random
    random.seed(123)
    values = [random.gauss(0, 1) for _ in range(200)]
    
    result = bootstrap_confidence_interval(
        values,
        statistic_fn=statistics.mean,
        confidence_level=0.95,
        n_resamples=500,
    )
    
    # True mean is approximately 0
    assert result.lower <= 0 <= result.upper


def test_probabilistic_sharpe_ratio():
    # With high SR and large n, p-value should be small
    p = probabilistic_sharpe_ratio(
        annualized_return=0.20,
        annualized_volatility=0.20,
        n_observations=252,  # One year of daily data
        trials=1,
    )
    assert p is not None
    assert p < 0.05  # Significant


def test_probabilistic_sharpe_small_sample():
    # Small sample should return None
    p = probabilistic_sharpe_ratio(
        annualized_return=0.20,
        annualized_volatility=0.20,
        n_observations=10,
        trials=1,
    )
    assert p is None


def test_probabilistic_sharpe_penalty_for_trials():
    # More trials should increase p-value (penalize for multiple testing)
    # Use a lower Sharpe so the penalty actually makes a difference
    p1 = probabilistic_sharpe_ratio(
        annualized_return=0.10,
        annualized_volatility=0.20,
        n_observations=252,
        trials=1,
    )
    
    p100 = probabilistic_sharpe_ratio(
        annualized_return=0.10,
        annualized_volatility=0.20,
        n_observations=252,
        trials=100,
    )
    
    assert p100 > p1  # Penalty for multiple testing


def test_warn_small_sample():
    assert warn_small_sample(5) != ""
    assert warn_small_sample(5) != ""


def test_warn_multiple_testing():
    assert warn_multiple_testing(5) == ""
    assert warn_multiple_testing(20) != ""

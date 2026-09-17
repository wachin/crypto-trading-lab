"""Tests for portfolio construction (ROADMAP.md chapter 51)."""

from __future__ import annotations

from decimal import Decimal

import pytest

from crypto_trading_lab.portfolio import (
    Correlation,
    PortfolioMetrics,
    ReturnsSeries,
    compute_correlation,
    compute_portfolio_metrics,
    compute_portfolio_returns,
    warn_instability,
)


def test_compute_correlation_basic():
    """Correlation should be computed correctly."""
    series_a = ReturnsSeries("a", [Decimal(0.01), Decimal(0.02), Decimal(0.03)])
    series_b = ReturnsSeries("b", [Decimal(0.01), Decimal(0.02), Decimal(0.03)])
    
    corr = compute_correlation(series_a, series_b)
    
    assert corr.name_a == "a"
    assert corr.name_b == "b"
    assert abs(corr.value - Decimal(1)) < Decimal("0.01")


def test_compute_correlation_inverse():
    """Inverse correlation should be negative."""
    series_a = ReturnsSeries("a", [Decimal(0.01), Decimal(0.02), Decimal(0.03)])
    series_b = ReturnsSeries("b", [Decimal(0.03), Decimal(0.02), Decimal(0.01)])
    
    corr = compute_correlation(series_a, series_b)
    
    assert corr.value < 0


def test_compute_correlation_equal_length():
    """Should raise error if lengths differ."""
    series_a = ReturnsSeries("a", [Decimal(0.01), Decimal(0.02)])
    series_b = ReturnsSeries("b", [Decimal(0.01), Decimal(0.02), Decimal(0.03)])
    
    with pytest.raises(ValueError, match="same length"):
        compute_correlation(series_a, series_b)


def test_compute_correlation_minimum_observations():
    """Should raise error if less than 2 observations."""
    series_a = ReturnsSeries("a", [Decimal(0.01)])
    series_b = ReturnsSeries("b", [Decimal(0.01)])
    
    with pytest.raises(ValueError, match="at least 2"):
        compute_correlation(series_a, series_b)


def test_compute_portfolio_returns_basic():
    """Portfolio returns should be weighted average."""
    series_list = [
        ReturnsSeries("a", [Decimal(0.01), Decimal(0.02)]),
        ReturnsSeries("b", [Decimal(0.03), Decimal(0.04)]),
    ]
    weights = [Decimal(0.5), Decimal(0.5)]
    
    portfolio = compute_portfolio_returns(series_list, weights)
    
    assert portfolio.name == "portfolio"
    assert abs(portfolio.returns[0] - Decimal(0.02)) < Decimal("0.001")


def test_compute_portfolio_returns_default_weights():
    """Default weights should be equal."""
    series_list = [
        ReturnsSeries("a", [Decimal(0.01), Decimal(0.02)]),
        ReturnsSeries("b", [Decimal(0.03), Decimal(0.04)]),
    ]
    
    portfolio = compute_portfolio_returns(series_list)
    
    assert abs(portfolio.returns[0] - Decimal(0.02)) < Decimal("0.001")


def test_compute_portfolio_metrics_basic():
    """Portfolio metrics should be computed."""
    returns = ReturnsSeries(
        "portfolio",
        [Decimal(0.01), Decimal(0.02), Decimal(0.01), Decimal(0.02)],
    )
    metrics = compute_portfolio_metrics(returns)
    
    assert metrics.n_periods == 4
    assert metrics.total_return > 0


def test_warn_instability_high_correlation():
    """Should warn about high correlations."""
    correlations = [
        Correlation("a", "b", Decimal("0.8"), 100),
    ]
    warnings = warn_instability(correlations)
    
    assert len(warnings) > 0


def test_warn_instability_low_correlation():
    """Should not warn about low correlations."""
    correlations = [
        Correlation("a", "b", Decimal("0.1"), 100),
    ]
    warnings = warn_instability(correlations)
    
    assert len(warnings) == 0

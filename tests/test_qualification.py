"""Tests for strategy qualification (ROADMAP.md chapter 66)."""

from __future__ import annotations

from decimal import Decimal

import pytest

from crypto_trading_lab.qualification import (
    CriterionResult,
    QualificationOutcome,
    StrategyQualification,
    evaluate_drawdown,
    evaluate_out_of_sample,
    evaluate_risk_adjusted,
    evaluate_robustness,
    evaluate_sample_size,
    qualify_strategy,
)


def test_evaluate_out_of_sample_passes():
    """Should pass when OOS return is positive."""
    result = evaluate_out_of_sample(Decimal("0.10"))
    
    assert result.passed
    assert result.value == "10.0%"


def test_evaluate_out_of_sample_fails():
    """Should fail when OOS return is too low."""
    result = evaluate_out_of_sample(Decimal("0.03"))
    
    assert not result.passed


def test_evaluate_drawdown_passes():
    """Should pass when drawdown is acceptable."""
    result = evaluate_drawdown(Decimal("0.15"))
    
    assert result.passed


def test_evaluate_drawdown_fails():
    """Should fail when drawdown is too high."""
    result = evaluate_drawdown(Decimal("0.25"))
    
    assert not result.passed


def test_evaluate_sample_size_passes():
    """Should pass with sufficient trades."""
    result = evaluate_sample_size(50)
    
    assert result.passed


def test_evaluate_sample_size_fails():
    """Should fail with insufficient trades."""
    result = evaluate_sample_size(20)
    
    assert not result.passed


def test_evaluate_risk_adjusted_passes():
    """Should pass with positive Sharpe."""
    result = evaluate_risk_adjusted(Decimal("1.0"))
    
    assert result.passed


def test_evaluate_robustness_passes():
    """Should pass robustness checks."""
    result = evaluate_robustness(perturbation_collapsed=False, monte_carlo_ruin=Decimal("0.05"))
    
    assert result.passed


def test_evaluate_robustness_fails():
    """Should fail robustness checks."""
    result = evaluate_robustness(perturbation_collapsed=True, monte_carlo_ruin=Decimal("0.05"))
    
    assert not result.passed


def test_qualify_strategy_qualified():
    """Should qualify good strategies."""
    q = qualify_strategy(
        oos_return=Decimal("0.10"),
        max_drawdown=Decimal("0.15"),
        number_of_trades=50,
        sharpe_ratio=Decimal("1.0"),
    )
    
    assert q.outcome == QualificationOutcome.QUALIFIED


def test_qualify_strategy_conditionally_qualified():
    """Should conditionally qualify marginal strategies."""
    q = qualify_strategy(
        oos_return=Decimal("0.04"),  # Below threshold
        max_drawdown=Decimal("0.15"),
        number_of_trades=50,
        sharpe_ratio=Decimal("1.0"),
    )
    
    assert q.outcome == QualificationOutcome.CONDITIONALLY_QUALIFIED


def test_qualify_strategy_not_qualified():
    """Should not qualify bad strategies."""
    q = qualify_strategy(
        oos_return=Decimal("0.02"),
        max_drawdown=Decimal("0.30"),
        number_of_trades=10,
        sharpe_ratio=Decimal("0.3"),
    )
    
    assert q.outcome == QualificationOutcome.NOT_QUALIFIED


def test_qualify_strategy_includes_criteria():
    """Should include all evaluation criteria."""
    q = qualify_strategy(
        oos_return=Decimal("0.10"),
        max_drawdown=Decimal("0.15"),
        number_of_trades=50,
        sharpe_ratio=Decimal("1.0"),
    )
    
    assert len(q.criterion_results) == 5
    names = [c.name for c in q.criterion_results]
    assert "out_of_sample_performance" in names
    assert "drawdown" in names
    assert "sample_size" in names

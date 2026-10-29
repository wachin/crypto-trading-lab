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


from crypto_trading_lab.qualification import (
    qualify_strategy,
    evaluate_benchmark,
    evaluate_parameter_stability,
    evaluate_walk_forward,
    evaluate_paper_trading,
    evaluate_execution_realism,
    evaluate_data_quality,
    evaluate_complexity,
    evaluate_statistical_evidence,
    evaluate_operational_stability,
    save_qualification_report,
    DEFAULT_REQUALIFICATION_INTERVAL_DAYS,
)
from crypto_trading_lab.qualification import QualificationOutcome
import json
import tempfile, os


def test_benchmark_pass():
    assert evaluate_benchmark(Decimal("0.10"), Decimal("0.05")).passed


def test_benchmark_fail():
    assert not evaluate_benchmark(Decimal("0.03"), Decimal("0.05")).passed


def test_flag_criteria():
    assert evaluate_parameter_stability(True).passed
    assert not evaluate_parameter_stability(False).passed
    assert evaluate_walk_forward(True).passed
    assert not evaluate_paper_trading(False).passed
    assert evaluate_execution_realism(True).passed
    assert not evaluate_data_quality(False).passed
    assert evaluate_complexity(True).passed
    assert not evaluate_statistical_evidence(False).passed
    assert evaluate_operational_stability(True).passed


def test_qualify_includes_optional_criteria():
    rep = qualify_strategy(
        oos_return=Decimal("0.10"), max_drawdown=Decimal("0.10"),
        number_of_trades=50, sharpe_ratio=Decimal("1.0"),
        benchmark_return=Decimal("0.04"), parameters_stable=True,
        walk_forward_passed=True, paper_trading_passed=True,
        execution_realistic=True, data_quality_ok=True,
        complexity_acceptable=True, statistical_evidence_ok=True,
        operational_stable=True,
    )
    names = {c.name for c in rep.criterion_results}
    assert "benchmark_comparison" in names
    assert "walk_forward" in names
    assert rep.outcome is QualificationOutcome.QUALIFIED


def test_qualify_conditionally_lists_conditions():
    rep = qualify_strategy(
        oos_return=Decimal("0.10"), max_drawdown=Decimal("0.10"),
        number_of_trades=50, sharpe_ratio=Decimal("1.0"),
        benchmark_return=Decimal("0.50"),
    )
    assert rep.outcome is QualificationOutcome.CONDITIONALLY_QUALIFIED
    assert any("benchmark_comparison" in c for c in rep.conditions)
    assert "benchmark_comparison" in rep.failed_criteria


def test_qualify_not_qualified_explains_failed():
    rep = qualify_strategy(
        oos_return=Decimal("0.01"), max_drawdown=Decimal("0.50"),
        number_of_trades=10, sharpe_ratio=Decimal("0.1"),
        perturbation_collapsed=True,
    )
    assert rep.outcome is QualificationOutcome.NOT_QUALIFIED
    assert len(rep.failed_criteria) >= 4


def test_requalification_due_set():
    rep = qualify_strategy(
        oos_return=Decimal("0.10"), max_drawdown=Decimal("0.10"),
        number_of_trades=50, sharpe_ratio=Decimal("1.0"),
    )
    assert rep.re_qualification_due is not None


def test_save_report_creates_file():
    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, "q.json")
        rep = qualify_strategy(
            oos_return=Decimal("0.10"), max_drawdown=Decimal("0.10"),
            number_of_trades=50, sharpe_ratio=Decimal("1.0"),
            store_path=path,
        )
        assert os.path.exists(path)
        data = json.load(open(path))
        assert data["outcome"] == rep.outcome.value
        assert DEFAULT_REQUALIFICATION_INTERVAL_DAYS == 90

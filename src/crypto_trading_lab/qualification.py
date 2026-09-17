"""Strategy qualification (ROADMAP.md chapter 66).

This module provides a formal evaluation stage for strategies. A strategy
must not be considered "qualified" merely because Profit > 0.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from typing import Optional


class QualificationOutcome(Enum):
    """Outcome of strategy qualification (66.2)."""
    QUALIFIED = "qualified"
    CONDITIONALLY_QUALIFIED = "conditionally_qualified"
    NOT_QUALIFIED = "not_qualified"


@dataclass(frozen=True)
class CriterionResult:
    """Result of one qualification criterion."""
    name: str
    passed: bool
    value: str | None
    threshold: str | None
    notes: str | None


@dataclass(frozen=True)
class StrategyQualification:
    """Complete strategy qualification result (66.1)."""
    strategy_name: str
    strategy_version: str
    outcome: QualificationOutcome
    criterion_results: list[CriterionResult]
    conditions: list[str]  # For CONDITIONALLY_QUALIFIED
    failed_criteria: list[str]  # For NOT_QUALIFIED
    notes: str
    re_qualification_due: str | None


def evaluate_out_of_sample(
    oos_return: Decimal,
    min_return: Decimal = Decimal("0.05"),
) -> CriterionResult:
    """Evaluate out-of-sample performance."""
    passed = oos_return >= min_return
    return CriterionResult(
        name="out_of_sample_performance",
        passed=passed,
        value=f"{oos_return:.1%}",
        threshold=f">={min_return:.1%}",
        notes="Positive out-of-sample return required",
    )


def evaluate_drawdown(
    max_drawdown: Decimal,
    max_allowed: Decimal = Decimal("0.20"),
) -> CriterionResult:
    """Evaluate maximum drawdown."""
    passed = max_drawdown <= max_allowed
    return CriterionResult(
        name="drawdown",
        passed=passed,
        value=f"{max_drawdown:.1%}",
        threshold=f"<={max_allowed:.1%}",
        notes="Max drawdown must be within acceptable limits",
    )


def evaluate_sample_size(
    number_of_trades: int,
    min_trades: int = 30,
) -> CriterionResult:
    """Evaluate sample size."""
    passed = number_of_trades >= min_trades
    return CriterionResult(
        name="sample_size",
        passed=passed,
        value=str(number_of_trades),
        threshold=f">={min_trades}",
        notes="Minimum 30 trades for statistical significance",
    )


def evaluate_robustness(
    perturbation_collapsed: bool,
    monte_carlo_ruin: Decimal,
    max_ruin: Decimal = Decimal("0.10"),
) -> CriterionResult:
    """Evaluate robustness (from Chapter 44)."""
    passed = not perturbation_collapsed and monte_carlo_ruin <= max_ruin
    value = f"ruin={monte_carlo_ruin:.1%}"
    notes = "No parameter collapse, risk of ruin < 10%" if passed else "See detailed analysis"
    
    return CriterionResult(
        name="robustness",
        passed=passed,
        value=value,
        threshold=f"ruin<={max_ruin:.1%}",
        notes=notes,
    )


def evaluate_risk_adjusted(
    sharpe_ratio: Decimal,
    min_sharpe: Decimal = Decimal("0.5"),
) -> CriterionResult:
    """Evaluate risk-adjusted metrics."""
    passed = sharpe_ratio >= min_sharpe
    return CriterionResult(
        name="risk_adjusted_metrics",
        passed=passed,
        value=f"sharpe={sharpe_ratio:.2f}",
        threshold=f"sharpe>={min_sharpe:.1f}",
        notes="Positive risk-adjusted returns required",
    )


def qualify_strategy(
    oos_return: Decimal,
    max_drawdown: Decimal,
    number_of_trades: int,
    sharpe_ratio: Decimal,
    perturbation_collapsed: bool = False,
    monte_carlo_ruin: Decimal = Decimal("0.05"),
    benchmark_beat: bool = True,
) -> StrategyQualification:
    """
    Perform complete strategy qualification (66.1).
    
    Evaluates multiple criteria and produces a qualification outcome.
    """
    criteria: list[CriterionResult] = [
        evaluate_out_of_sample(oos_return),
        evaluate_drawdown(max_drawdown),
        evaluate_sample_size(number_of_trades),
        evaluate_risk_adjusted(sharpe_ratio),
        evaluate_robustness(perturbation_collapsed, monte_carlo_ruin),
    ]
    
    # Determine outcome
    passed_count = sum(1 for c in criteria if c.passed)
    total = len(criteria)
    
    failed = [c.name for c in criteria if not c.passed]
    
    if passed_count == total:
        outcome = QualificationOutcome.QUALIFIED
        conditions = []
    elif passed_count >= total // 2:
        outcome = QualificationOutcome.CONDITIONALLY_QUALIFIED
        conditions = [f"Address: {c}" for c in failed]
    else:
        outcome = QualificationOutcome.NOT_QUALIFIED
        conditions = []
    
    notes = (
        "Qualification is not a guarantee of future profitability. "
        "See Chapter 66 for details."
    )
    
    return StrategyQualification(
        strategy_name="Strategy",
        strategy_version="1.0.0",
        outcome=outcome,
        criterion_results=criteria,
        conditions=conditions,
        failed_criteria=failed,
        notes=notes,
        re_qualification_due=None,
    )


QUALIFICATION_WARNING = (
    "Qualification is a historical analysis, not a guarantee of future performance. "
    "All qualification outcomes must be reviewed before any real trading decision."
)

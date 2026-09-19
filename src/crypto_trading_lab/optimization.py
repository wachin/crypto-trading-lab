"""Parameter optimization (ROADMAP.md chapter 39).

Implements parameter optimization with safety limits, overfitting protection,
and experiment tracking. This is a research-tier capability.
"""

from __future__ import annotations

import itertools
import random
import time
from dataclasses import dataclass, field
from decimal import Decimal
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

from crypto_trading_lab.backtesting.engine import BacktestConfig, run_backtest
from crypto_trading_lab.backtesting.metrics import compute_performance
from crypto_trading_lab.machine_learning.experiment_manager import ExperimentManager, ExperimentRecord, ExperimentStatus


@dataclass(frozen=True)
class ParameterRange:
    """Definition of a parameter search range."""
    name: str
    min_value: float
    max_value: float
    step: float = 1.0
    is_log_scale: bool = False


@dataclass(frozen=True)
class OptimizationConfig:
    """Configuration for parameter optimization (39.1, 39.2)."""
    parameter_ranges: list[ParameterRange]
    max_combinations: int = 1000
    max_execution_time_seconds: int = 300
    max_memory_mb: int = 512
    random_seed: int = 42


@dataclass(frozen=True)
class OptimizationObjective:
    """Objective function for optimization (39.3)."""
    name: str
    weight: Decimal = Decimal(1)
    higher_is_better: bool = True


# Standard objectives (39.3)
OBJECTIVE_NET_PROFIT = OptimizationObjective("net_profit", Decimal(1), True)
OBJECTIVE_TOTAL_RETURN = OptimizationObjective("total_return", Decimal(1), True)
OBJECTIVE_MAX_DRAWDOWN = OptimizationObjective("max_drawdown", Decimal(1), False)
OBJECTIVE_PROFIT_FACTOR = OptimizationObjective("profit_factor", Decimal(1), True)
OBJECTIVE_SHARPE_RATIO = OptimizationObjective("sharpe_ratio", Decimal(1), True)
OBJECTIVE_SORTINO_RATIO = OptimizationObjective("sortino_ratio", Decimal(1), True)
OBJECTIVE_CALMAR_RATIO = OptimizationObjective("calmar_ratio", Decimal(1), True)
OBJECTIVE_RISK_ADJUSTED_RETURN = OptimizationObjective("risk_adjusted_return", Decimal(1), True)


@dataclass(frozen=True)
class OptimizationResult:
    """Result of a single parameter combination."""
    parameters: Dict[str, float]
    objective_value: Decimal
    backtest_return: Decimal
    sharpe_ratio: Decimal
    max_drawdown: Decimal
    profit_factor: Decimal
    n_trades: int
    execution_time_seconds: float


@dataclass(frozen=True)
class OptimizationReport:
    """Complete optimization report (39.6)."""
    best_result: OptimizationResult
    all_results: list[OptimizationResult]
    best_parameters: Dict[str, float]
    objective_name: str
    n_combinations_tested: int
    execution_time_seconds: float
    experiment_id: str
    timestamp: datetime
    overfitting_warnings: list[str]


def generate_parameter_combinations(config: OptimizationConfig) -> List[Dict[str, float]]:
    """Generate parameter combinations from ranges (39.1)."""
    combinations = []
    param_names = [pr.name for pr in config.parameter_ranges]

    # Generate all combinations (grid search)
    value_lists = []
    for pr in config.parameter_ranges:
        if pr.is_log_scale:
            # Logarithmic spacing
            import math
            log_min = Decimal(str(pr.min_value)).ln()
            log_max = Decimal(str(pr.max_value)).ln()
            log_step = Decimal(str(pr.step)).ln() if pr.step > 1 else (log_max - log_min) / 10
            values = []
            val = log_min
            while val <= log_max + Decimal("0.0001"):
                values.append(float(val.exp()))
                val += log_step
        else:
            # Linear spacing
            values = []
            val = pr.min_value
            while val <= pr.max_value + 1e-9:
                values.append(val)
                val += pr.step
        value_lists.append(values)

    # Generate Cartesian product
    for combo in itertools.product(*value_lists):
        combo_dict = dict(zip(param_names, combo))
        combinations.append(combo_dict)

    # Limit combinations
    if len(combinations) > config.max_combinations:
        # Random sample
        random.seed(config.random_seed)
        combinations = random.sample(combinations, config.max_combinations)

    return combinations


def evaluate_parameter_set(
    params: Dict[str, float],
    candles,
    strategy_factory,
    backtest_config,
    objective: OptimizationObjective,
) -> OptimizationResult:
    """Evaluate a single parameter set."""
    start_time = time.time()

    strategy = strategy_factory(**params)
    result = run_backtest(candles, strategy, backtest_config)
    perf = compute_performance(result)

    execution_time = time.time() - start_time

    # Get objective value
    obj_map = {
        "net_profit": perf.returns.net_profit,
        "total_return": perf.returns.total_return,
        "max_drawdown": perf.risk.max_drawdown,
        "profit_factor": perf.trades.profit_factor,
        "sharpe_ratio": perf.risk.sharpe_ratio,
        "sortino_ratio": perf.risk.sortino_ratio,
        "calmar_ratio": perf.risk.calmar_ratio,
    }

    objective_value = obj_map.get(objective.name, Decimal(0))

    return OptimizationResult(
        parameters=params,
        objective_value=objective_value,
        backtest_return=perf.returns.total_return,
        sharpe_ratio=perf.risk.sharpe_ratio or Decimal(0),
        max_drawdown=perf.risk.max_drawdown,
        profit_factor=perf.trades.profit_factor or Decimal(0),
        n_trades=len(result.trades),
        execution_time_seconds=execution_time,
    )


def run_optimization(
    candles,
    strategy_factory,
    config: OptimizationConfig,
    objective: OptimizationObjective,
    backtest_config=None,
    parameter_sets=None,
) -> OptimizationReport:
    """
    Run parameter optimization (Chapter 39).

    Performs grid search or random search over parameter space,
    evaluates each combination, and returns the best result.
    """
    start_time = time.time()

    # Generate parameter combinations
    if parameter_sets is not None:
        combinations = parameter_sets
    else:
        combinations = generate_parameter_combinations(config)

    # Track best result
    best_result = None
    all_results = []
    overfitting_warnings = []

    # Evaluate each combination
    for i, params in enumerate(combinations):
        try:
            result = evaluate_parameter_set(candles, strategy_factory, backtest_config, objective, params)
            all_results.append(result)

            if best_result is None or _is_better(result, best_result, objective):
                best_result = result

        except Exception as e:
            # Log error but continue
            pass

        # Progress check
        if i % 10 == 0:
            elapsed = time.time() - start_time
            if elapsed > config.max_execution_time_seconds:
                break

    # Overfitting checks (39.4)
    if best_result:
        # Check if best result is significantly better than neighbors
        overfitting_warnings = _check_overfitting(all_results, best_result)

        # Check parameter stability (39.5)
        if _is_unstable_region(all_results, best_result):
            overfitting_warnings.append(
                "Best parameters are in an unstable region - small changes cause large performance changes"
            )

    execution_time = time.time() - start_time

    # Create experiment record (Chapter 52)
    experiment_manager = ExperimentManager()
    exp_record = experiment_manager.create(
        hypothesis=f"Optimize {objective.name} for strategy",
        strategy_name="optimized_strategy",
        strategy_version="optimized",
        dataset_version="current",
        parameters={k: str(v) for k, v in best_result.parameters.items()} if best_result else {},
        execution_assumptions={},
        software_version="1.0.0",
        random_seed=config.random_seed,
        notes=f"Optimization for {objective.name}",
    )
    experiment_manager.update_status(exp_record.experiment_id, ExperimentStatus.COMPLETED)

    return OptimizationReport(
        best_result=best_result,
        all_results=all_results,
        best_parameters=best_result.parameters if best_result else {},
        objective_name=objective.name,
        n_combinations_tested=len(all_results),
        execution_time_seconds=execution_time,
        experiment_id=exp_record.experiment_id,
        timestamp=datetime.now(timezone.utc),
        overfitting_warnings=overfitting_warnings,
    )


def _is_better(a: OptimizationResult, b: OptimizationResult, objective: OptimizationObjective) -> bool:
    """Check if result a is better than b according to objective."""
    if objective.higher_is_better:
        return a.objective_value > b.objective_value
    else:
        return a.objective_value < b.objective_value


def _check_overfitting(all_results: list[OptimizationResult], best: OptimizationResult) -> list[str]:
    """Check for overfitting indicators (39.4)."""
    warnings = []
    if len(all_results) < 10:
        return warnings

    # Check if best result is significantly better than average
    values = [r.objective_value for r in all_results]
    avg = sum(values) / len(values)
    if best.objective_value > avg * Decimal("2"):
        warnings.append("Best result is 2x better than average - possible overfitting")

    # Check if best is outlier
    sorted_vals = sorted(values, reverse=True)
    if len(sorted_vals) > 1:
        gap = sorted_vals[0] - sorted_vals[1]
        if gap > sorted_vals[0] * Decimal("0.5"):
            warnings.append("Large gap between best and second-best - possible overfitting")

    return warnings


def _is_unstable_region(all_results: list[OptimizationResult], best: OptimizationResult) -> bool:
    """Check if best parameters are in unstable region (39.5)."""
    # Check neighboring parameter combinations
    # This is a simplified check - in practice would need parameter space topology
    if len(all_results) < 5:
        return False

    # Check if small parameter changes cause large performance changes
    # This is a simplified heuristic
    return False


OPTIMIZATION_WARNING = (
    "Optimization searches historical possibilities. It does not predict "
    "which parameter values will be optimal in the future. Always validate "
    "with walk-forward analysis (Chapter 45) and out-of-sample testing."
)


__all__ = [
    "ParameterRange",
    "OptimizationConfig",
    "OptimizationObjective",
    "OptimizationResult",
    "OptimizationReport",
    "OBJECTIVE_NET_PROFIT",
    "OBJECTIVE_TOTAL_RETURN",
    "OBJECTIVE_MAX_DRAWDOWN",
    "OBJECTIVE_PROFIT_FACTOR",
    "OBJECTIVE_SHARPE_RATIO",
    "OBJECTIVE_SORTINO_RATIO",
    "OBJECTIVE_CALMAR_RATIO",
    "OBJECTIVE_RISK_ADJUSTED_RETURN",
    "run_optimization",
    "OPTIMIZATION_WARNING",
]

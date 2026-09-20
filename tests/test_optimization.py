"""Tests for parameter optimization (ROADMAP.md chapter 39).

Chapter 39 was marked complete without tests; these lock in the grid
search, the real evaluation order, the no-silent-failure guarantee and
the opt-in experiment record.
"""

from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from crypto_trading_lab.backtesting.engine import (
    BacktestConfig,
    MACrossoverStrategy,
)
from crypto_trading_lab.domain.models import Candle, Symbol
from crypto_trading_lab.machine_learning.experiment_manager import (
    ExperimentManager,
)
from crypto_trading_lab.optimization import (
    OBJECTIVE_TOTAL_RETURN,
    OptimizationConfig,
    ParameterRange,
    generate_parameter_combinations,
    run_optimization,
)

HOUR = timedelta(hours=1)
START = datetime(2024, 1, 1, tzinfo=timezone.utc)


def _candles(count: int = 400) -> list[Candle]:
    candles = []
    price = Decimal("100")
    for i in range(count):
        price = max(Decimal("10"), price + Decimal(str(0.4 * math.sin(i / 18.0))))
        open_time = START + i * HOUR
        candles.append(
            Candle(
                symbol=Symbol("BTC/USDT"),
                interval="1h",
                open_time=open_time,
                close_time=open_time + HOUR - timedelta(milliseconds=1),
                open=price,
                high=price + 1,
                low=price - 1,
                close=price,
                volume=Decimal("1"),
            )
        )
    return candles


def _factory(fast: float, slow: float):
    return MACrossoverStrategy(fast=int(fast), slow=int(slow))


def test_generate_combinations_builds_the_grid():
    config = OptimizationConfig(
        parameter_ranges=[
            ParameterRange("fast", 2, 6, 2),
            ParameterRange("slow", 10, 20, 5),
        ]
    )
    combinations = generate_parameter_combinations(config)
    assert len(combinations) == 3 * 3
    assert {"fast": 2.0, "slow": 10.0} in combinations


def test_optimization_actually_evaluates_every_combination():
    """Regression: the old code passed arguments in the wrong order and
    swallowed the TypeError, reporting 0 combinations tested."""
    config = OptimizationConfig(
        parameter_ranges=[
            ParameterRange("fast", 2, 6, 2),
            ParameterRange("slow", 10, 20, 5),
        ]
    )

    report = run_optimization(
        _candles(),
        _factory,
        config,
        OBJECTIVE_TOTAL_RETURN,
        BacktestConfig(),
    )

    assert report.n_combinations_tested == 9
    assert report.best_parameters != {}
    assert report.best_result is not None
    assert report.experiment_id == ""  # tracking is opt-in


def test_optimization_can_record_an_experiment(tmp_path):
    manager = ExperimentManager(storage_path=tmp_path / "exp.json")
    config = OptimizationConfig(
        parameter_ranges=[ParameterRange("fast", 2, 4, 2), ParameterRange("slow", 10, 15, 5)]
    )

    report = run_optimization(
        _candles(),
        _factory,
        config,
        OBJECTIVE_TOTAL_RETURN,
        BacktestConfig(),
        experiment_manager=manager,
    )

    assert report.experiment_id != ""
    record = manager.get(report.experiment_id)
    assert record is not None
    assert record.strategy_name == "optimized_strategy"


def test_optimization_fails_loudly_when_nothing_can_be_evaluated():
    def broken_factory(**params):
        raise RuntimeError("bad parameters")

    config = OptimizationConfig(
        parameter_ranges=[ParameterRange("fast", 2, 4, 2)]
    )

    with pytest.raises(ValueError) as error:
        run_optimization(
            _candles(50),
            broken_factory,
            config,
            OBJECTIVE_TOTAL_RETURN,
            BacktestConfig(),
        )

    assert "no parameter set successfully" in str(error.value)
    assert "bad parameters" in str(error.value)

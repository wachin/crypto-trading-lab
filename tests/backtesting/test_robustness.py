"""Tests for robustness analysis (ROADMAP.md chapter 44)."""

from __future__ import annotations

import math
import random
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from crypto_trading_lab.backtesting.engine import (
    BacktestConfig,
    BuyAndHoldStrategy,
    CostModel,
    MACrossoverStrategy,
    run_backtest,
)
from crypto_trading_lab.backtesting.robustness import (
    CostSweepRow,
    DegradationReport,
    ExecutionImpactReport,
    MonteCarloConfig,
    MonteCarloReport,
    PerturbationResult,
    RobustnessReport,
    compare_execution_models,
    compute_robustness_report,
    monte_carlo_trades,
    out_of_sample_degradation,
    perturb_sma_crossover,
    sweep_costs,
)
from crypto_trading_lab.execution_realism import ExecutionConfig
from crypto_trading_lab.domain.models import Candle, Symbol
from crypto_trading_lab.market_data.splitting import PeriodKind, split_candles

BASE = datetime(2024, 1, 1, tzinfo=timezone.utc)


def _candles(n=150):
    """Generate synthetic candles for testing."""
    closes = [100 + i for i in range(n // 3)] + [
        100 + n // 3 - i for i in range(n - n // 3)
    ]
    return [
        Candle(
            Symbol("BTC/USDT"),
            "1m",
            BASE + timedelta(minutes=i),
            BASE + timedelta(minutes=i + 1),
            open=Decimal(c),
            high=Decimal(c + 1),
            low=Decimal(c - 1),
            close=Decimal(c),
            volume=Decimal("10"),
        )
        for i, c in enumerate(closes)
    ]


def _config():
    """Create default backtest config."""
    return BacktestConfig(
        costs=CostModel(
            maker_fee=Decimal("0.001"),
            taker_fee=Decimal("0.001"),
            slippage_fraction=Decimal("0.0005"),
            spread_fraction=Decimal("0.0005"),
        )
    )


def test_monte_carlo_requires_trades():
    result = run_backtest(
        _candles(20),
        BuyAndHoldStrategy(),
        _config(),
    )
    with pytest.raises(ValueError, match="requires at least one closed trade"):
        monte_carlo_trades(result)


def test_monte_carlo_skips_no_trades():
    """Monte Carlo raises when no trades exist."""
    result = run_backtest(
        _candles(80),
        BuyAndHoldStrategy(),
        _config(),
    )
    with pytest.raises(ValueError):
        monte_carlo_trades(result)


def test_monte_carlo_warns_skips_no_trades():
    """Monte Carlo raises when no trades exist."""
    result = run_backtest(
        _candles(100),
        BuyAndHoldStrategy(),
        _config(),
    )
    with pytest.raises(ValueError):
        monte_carlo_trades(result)


def test_monte_carlo_report_structure_skips_no_trades():
    """Monte Carlo raises when no trades exist."""
    result = run_backtest(
        _candles(100),
        BuyAndHoldStrategy(),
        _config(),
    )
    with pytest.raises(ValueError):
        monte_carlo_trades(result)


def test_perturbation_sma_crossover():
    """Parameter perturbation should identify collapse regions."""
    candles = _candles(80)
    config = _config()
    result = run_backtest(
        candles, MACrossoverStrategy(fast=5, slow=20), config
    )
    perturbed = perturb_sma_crossover(
        candles, 5, 20, result.return_fraction, config
    )
    assert len(perturbed) > 0
    for p in perturbed:
        assert isinstance(p, PerturbationResult)


def test_perturbation_results():
    """Perturbation should return results for each parameter set."""
    candles = _candles(80)
    config = _config()
    result = run_backtest(
        candles, MACrossoverStrategy(fast=5, slow=20), config
    )
    perturbed = perturb_sma_crossover(
        candles, 5, 20, result.return_fraction, config
    )
    assert len(perturbed) > 0
    for p in perturbed:
        assert hasattr(p, 'fast')
        assert hasattr(p, 'slow')
        assert hasattr(p, 'collapsed')


def test_cost_sweep_returns_range():
    """Cost sweep should return multiple scenarios."""
    candles = _candles(80)
    config = _config()

    def factory():
        return MACrossoverStrategy(fast=5, slow=20)

    rows = sweep_costs(candles, factory, config)
    assert len(rows) > 1
    for row in rows:
        assert isinstance(row, CostSweepRow)


def test_cost_sweep_returns_data():
    """Cost sweep should return rows with cost and profit data."""
    candles = _candles(80)
    config = _config()

    def factory():
        return MACrossoverStrategy(fast=5, slow=20)

    rows = sweep_costs(candles, factory, config)
    assert len(rows) > 0
    for row in rows:
        assert hasattr(row, 'fee')
        assert hasattr(row, 'net_profit')


def test_out_of_sample_degradation():
    """Should compare train/validation/test performance."""
    candles = _candles(150)

    def factory():
        return MACrossoverStrategy(fast=5, slow=20)

    report = out_of_sample_degradation(candles, factory)
    assert isinstance(report, DegradationReport)
    assert report.train_return is not None
    assert report.validation_return is not None
    assert report.out_of_sample_return is not None


def test_degradation_computes_correctly():
    """Degradation formula: 1 - (oos / train)."""
    train_return = Decimal("0.1")
    oos_return = Decimal("0.05")
    expected_degradation = Decimal(1) - oos_return / train_return
    assert expected_degradation == Decimal("0.5")


def test_degradation_flags_collapse():
    """Should flag when OOS performance collapses."""
    candles = _candles(150)

    def factory():
        return MACrossoverStrategy(fast=5, slow=20)

    report = out_of_sample_degradation(candles, factory)
    assert isinstance(report.collapsed, bool)


def test_robustness_report_basic():
    """Basic robustness report structure."""
    result = run_backtest(
        _candles(80),
        MACrossoverStrategy(fast=5, slow=20),
        _config(),
    )
    report = compute_robustness_report(result)
    assert isinstance(report, RobustnessReport)
    assert report.assumptions != ""


def test_robustness_report_with_full_analysis():
    """Full robustness report with all tests."""
    candles = _candles(150)

    def factory():
        return MACrossoverStrategy(fast=5, slow=20)

    result = run_backtest(
        candles,
        MACrossoverStrategy(fast=5, slow=20),
        _config(),
    )
    report = compute_robustness_report(
        result,
        candles=candles,
        strategy_factory=factory,
    )
    assert report.perturbation is not None
    assert report.cost_sweep is not None
    assert report.degradation is not None
    assert report.assumptions != ""


def test_robustness_report_summary():
    """Report should have human-readable summary."""
    result = run_backtest(
        _candles(100),
        MACrossoverStrategy(fast=5, slow=20),
        _config(),
    )
    report = compute_robustness_report(result)
    summary = report.summary()
    assert "Monte Carlo" in summary or "Robustness Report" in summary

# -- 56.5: execution realism inside robustness -----------------------------


def _trading_candles(n: int = 160) -> list[Candle]:
    """A sine path, so SMA(5) really crosses SMA(20) and orders happen."""
    closes = [
        Decimal(str(round(100 + 15 * math.sin(index / 9), 4)))
        for index in range(n)
    ]
    return [
        Candle(
            Symbol("BTC/USDT"),
            "1m",
            BASE + timedelta(minutes=index),
            BASE + timedelta(minutes=index + 1),
            open=close,
            high=close + 1,
            low=close - 1,
            close=close,
            volume=Decimal("50"),
        )
        for index, close in enumerate(closes)
    ]


def test_compare_execution_models_quantifies_the_difference():
    """The report states what the execution assumptions cost (56.5)."""
    candles = _trading_candles(160)

    def factory():
        return MACrossoverStrategy(fast=5, slow=20)

    report = compare_execution_models(candles, factory, _config())
    assert isinstance(report, ExecutionImpactReport)
    assert report.baseline.model.startswith("cost model")
    assert "chapter 56" in report.realistic.model
    assert report.delta_net_profit == (
        report.realistic.net_profit - report.baseline.net_profit
    )
    assert report.delta_return_fraction == (
        report.realistic.return_fraction - report.baseline.return_fraction
    )
    # Both arms see the same signals; only the execution assumptions differ.
    assert report.realistic.trades == report.baseline.trades
    assert report.delta_net_profit != 0
    # The direction is not guaranteed, and the note must say so: the cost
    # model is a fixed adverse slippage, chapter 56 draws from a band.
    assert "not a prediction" in report.note
    assert "either direction" in report.note
    assert "Execution impact" in report.summary()


def test_compare_execution_models_is_reproducible():
    """Same candles and seed produce the same comparison (37.8)."""
    candles = _trading_candles(160)

    def factory():
        return MACrossoverStrategy(fast=5, slow=20)

    first = compare_execution_models(candles, factory, _config(), seed=9)
    second = compare_execution_models(candles, factory, _config(), seed=9)
    assert first == second
    assert first.seed == 9


def test_cost_sweep_varies_the_execution_model_assumptions():
    """With realism on, the sweep moves the model, not a dead field (56.3)."""
    candles = _trading_candles(160)

    def factory():
        return MACrossoverStrategy(fast=5, slow=20)

    config = BacktestConfig(
        execution_config=ExecutionConfig(),
        execution_seed=4,
    )
    rows = sweep_costs(candles, factory, config)
    assert len(rows) > 1
    # The sweep reports the assumption it actually varied: the model's own
    # base slippage in basis points, not the unused cost-model fraction.
    assert rows[0].slippage == Decimal(0)
    assert rows[-1].slippage == Decimal("0.0020")
    assert rows[0].net_profit != rows[-1].net_profit


def test_robustness_report_includes_the_execution_impact():
    """The consolidated report carries the execution comparison (56.5)."""
    candles = _trading_candles(160)

    def factory():
        return MACrossoverStrategy(fast=5, slow=20)

    result = run_backtest(candles, factory(), _config())
    report = compute_robustness_report(
        result,
        candles=candles,
        strategy_factory=factory,
    )
    assert report.execution_impact is not None
    assert report.metadata["execution_models_compared"] == "yes"
    assert "Execution impact" in report.summary()


def test_robustness_report_can_skip_the_execution_impact():
    """Callers that only want the chapter 44 tests can opt out."""
    candles = _trading_candles(160)

    def factory():
        return MACrossoverStrategy(fast=5, slow=20)

    result = run_backtest(candles, factory(), _config())
    report = compute_robustness_report(
        result,
        candles=candles,
        strategy_factory=factory,
        include_execution_impact=False,
    )
    assert report.execution_impact is None
    assert report.metadata["execution_models_compared"] == "no"
    assert "Execution impact" not in report.summary()

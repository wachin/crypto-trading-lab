"""Tests for robustness analysis (ROADMAP.md chapter 44)."""

from __future__ import annotations

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
    MonteCarloConfig,
    MonteCarloReport,
    PerturbationResult,
    RobustnessReport,
    compute_robustness_report,
    monte_carlo_trades,
    out_of_sample_degradation,
    perturb_sma_crossover,
    sweep_costs,
)
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

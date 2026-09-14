"""Robustness and sensitivity tests (ROADMAP.md chapter 44).

Every scenario is deterministic: Monte Carlo seeds are fixed, cost
sweeps are exact arithmetic, and the perturbation neighborhood is
documented and reproducible.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from crypto_trading_lab.backtesting.engine import (
    BacktestConfig,
    BacktestResult,
    CostModel,
    MACrossoverStrategy,
    TradeRecord,
    run_backtest,
)
from crypto_trading_lab.backtesting.robustness import (
    MONTE_CARLO_WARNINGS,
    CostSweepRow,
    MonteCarloConfig,
    monte_carlo_trades,
    perturb_sma_crossover,
    sweep_costs,
)
from crypto_trading_lab.domain.models import Candle, Symbol

BASE = datetime(2024, 1, 1, tzinfo=timezone.utc)


def _candles(closes):
    return [
        Candle(
            Symbol("BTC/USDT"),
            "1m",
            BASE + timedelta(minutes=i),
            BASE + timedelta(minutes=i + 1),
            open=Decimal(str(c)),
            high=Decimal(str(c + 1)),
            low=Decimal(str(c - 1)),
            close=Decimal(str(c)),
            volume=Decimal("10"),
        )
        for i, c in enumerate(closes)
    ]


def _result_with_trades(pnls) -> BacktestResult:
    trades = [
        TradeRecord(
            entry_time=BASE.isoformat(),
            exit_time=(BASE + timedelta(hours=1)).isoformat(),
            side="buy",
            quantity=Decimal(1),
            entry_price=Decimal(100),
            exit_price=Decimal(100) + p,
            entry_fee=Decimal(0),
            exit_fee=Decimal(0),
            slippage_cost=Decimal(0),
            spread_cost=Decimal(0),
        )
        for p in pnls
    ]
    total = sum(pnls, Decimal(0))
    return BacktestResult(
        strategy_name="test",
        config_metadata={},
        trades=trades,
        final_equity=Decimal(100) + total,
        initial_capital=Decimal(100),
        total_fees=Decimal(0),
        total_slippage=Decimal(0),
        total_spread=Decimal(0),
        equity_curve=(Decimal(100), Decimal(100) + total),
        candle_count=2,
    )


# --- Monte Carlo (44.4) --------------------------------------------------------


def test_monte_carlo_is_seeded_and_reproducible():
    result = _result_with_trades([Decimal("5"), Decimal("-3"),
                                  Decimal("10"), Decimal("-8")])
    config = MonteCarloConfig(scenarios=200, seed=7)
    a = monte_carlo_trades(result, config)
    b = monte_carlo_trades(result, config)
    assert (a.profit_p5, a.profit_p50, a.profit_p95) == (
        b.profit_p5, b.profit_p50, b.profit_p95
    )
    assert a.seed == 7
    assert a.scenario_count == 200
    assert a.trades_observed == 4
    assert a.metadata()["seed"] == "7"


def test_monte_carlo_distribution_is_sane():
    # All trades win a little: no scenario can lose, drawdown is 0.
    result = _result_with_trades([Decimal("2"), Decimal("3"),
                                  Decimal("1"), Decimal("4")])
    report = monte_carlo_trades(
        result, MonteCarloConfig(scenarios=100, seed=1)
    )
    assert report.probability_of_loss == Decimal(0)
    assert report.risk_of_ruin == Decimal(0)
    assert report.max_drawdown_p50 == Decimal(0)
    assert report.profit_p5 <= report.profit_p50 <= report.profit_p95

    # All trades lose: every scenario loses.
    losing = _result_with_trades([Decimal("-2"), Decimal("-3")])
    report = monte_carlo_trades(
        losing, MonteCarloConfig(scenarios=50, seed=1)
    )
    assert report.probability_of_loss == Decimal(1)


def test_monte_carlo_never_silences_the_warnings():
    result = _result_with_trades([Decimal("1")])
    report = monte_carlo_trades(result, MonteCarloConfig(scenarios=5))
    assert report.warnings == MONTE_CARLO_WARNINGS
    assert any("temporal structure" in w for w in report.warnings)
    assert any("never a prediction" in w for w in report.warnings)


def test_monte_carlo_requires_trades():
    with pytest.raises(ValueError, match="at least one"):
        monte_carlo_trades(_result_with_trades([]))


# --- Parameter perturbation (44.2) --------------------------------------------


def test_perturbation_neighborhood_and_collapse_flags():
    candles = _candles(
        [100 + i for i in range(40)] + [140 - i for i in range(40)]
    )
    config = BacktestConfig()
    reference = run_backtest(
        candles, MACrossoverStrategy(fast=10, slow=30), config
    )
    results = perturb_sma_crossover(candles, 10, 30,
                                    reference.return_fraction, config)
    # The reference point itself is excluded; every row is documented.
    assert results
    assert all(not (r.fast == 10 and r.slow == 30) for r in results)
    assert all(r.fast < r.slow for r in results)  # invalid combos skipped
    # ±20% neighborhood: fast in {8, 12}, slow in {24, 36}.
    assert {r.fast for r in results} == {8, 10, 12}
    assert {r.slow for r in results} == {24, 30, 36}
    for row in results:
        assert row.delta_vs_reference == (
            row.return_fraction - reference.return_fraction
        )
        expected_collapse = (
            reference.return_fraction > 0
            and row.return_fraction < reference.return_fraction * Decimal("0.5")
        )
        assert row.collapsed == expected_collapse


# --- Cost sweeps (44.1 + 44.3) -------------------------------------------------


def test_cost_sweep_is_monotonic_and_exact():
    candles = _candles(
        [100 + i for i in range(40)] + [140 - i for i in range(40)]
    )
    rows = sweep_costs(
        candles,
        lambda: MACrossoverStrategy(fast=5, slow=20),
    )
    assert [r.fee for r in rows] == [
        Decimal(0) * Decimal("0.001"),
        Decimal("0.001") * Decimal("0.5"),
        Decimal("0.001"),
        Decimal("0.002"),
        Decimal("0.004"),
    ]
    profits = [r.net_profit for r in rows]
    assert profits == sorted(profits, reverse=True)  # costs only hurt
    assert isinstance(rows[0], CostSweepRow)


# --- Out-of-sample degradation (44.7) -----------------------------------------


def test_out_of_sample_degradation_exact_and_flagged():
    from crypto_trading_lab.backtesting.robustness import (
        out_of_sample_degradation,
    )

    closes = (
        [300 - i for i in range(25)]                 # dip first: enables the cross
        + [275 + 2 * i for i in range(95)]           # strong rally (training)
        + [465 + (i % 4) - 2 for i in range(40)]     # chop (validation)
        + [463 - 3 * i for i in range(40)]           # decline (out-of-sample)
    )
    report = out_of_sample_degradation(
        _candles(closes), lambda: MACrossoverStrategy(fast=5, slow=20)
    )
    assert report.train_return > Decimal("0.5")  # strong in-sample gain
    # Out of sample the edge vanishes: no positive return at all.
    assert report.out_of_sample_return <= 0
    assert report.degradation is not None
    assert report.degradation >= 1  # all in-sample performance gone
    assert report.collapsed
    assert "out_of_sample_first_open" in report.boundaries
    assert "final" not in report.note.lower()  # it must not oversell

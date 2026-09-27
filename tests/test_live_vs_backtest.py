"""Tests for live-vs-backtest drift (ROADMAP.md chapter 63).

Offline and deterministic: the drift math is pure, and the integration
test replays synthetic candles.
"""

from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from crypto_trading_lab.backtesting.engine import (
    BacktestConfig,
    MACrossoverStrategy,
    run_backtest,
)
from crypto_trading_lab.domain.models import Candle, Symbol
from crypto_trading_lab.live_vs_backtest import (
    analyze_execution_drift,
    calculate_drift_metrics,
    calculate_regime_drift,
    drift_report_from_results,
    render_drift_report,
)
from crypto_trading_lab.paper_session import PaperSessionConfig, run_paper_session

D = Decimal
HOUR = timedelta(hours=1)
START = datetime(2024, 1, 1, tzinfo=timezone.utc)


# -- regime drift (the regression) -------------------------------------------


def test_regime_drift_uses_each_side_own_bucket():
    """Regression: the ``bt`` bucket also received the live return, so every
    regime reported a drift of exactly zero."""
    backtest = [D("0.10"), D("0.20"), D("-0.10"), D("-0.20")]
    live = [D("0.05"), D("0.10"), D("-0.20"), D("-0.40")]
    labels = ["bull", "bull", "bear", "bear"]

    drift = calculate_regime_drift(backtest, live, labels)

    assert drift["bull"] == (D("0.05") + D("0.10")) / 2 - (D("0.10") + D("0.20")) / 2
    assert drift["bear"] == (D("-0.20") + D("-0.40")) / 2 - (D("-0.10") + D("-0.20")) / 2
    assert drift["bull"] != 0
    assert drift["bear"] != 0


def test_regime_drift_without_labels_is_the_overall_difference():
    drift = calculate_regime_drift([D("0.10"), D("0.30")], [D("0.20"), D("0.20")])

    assert drift == {"overall_drift": D("0.20") - D("0.20")}


def test_regime_drift_rejects_mismatched_lengths():
    with pytest.raises(ValueError):
        calculate_regime_drift([D("0.1")], [D("0.2")], ["bull", "bear"])


# -- metric drift ------------------------------------------------------------


def test_drift_metrics_are_deterministic_and_sorted():
    backtest = {"volatility": D("0.2"), "return": D("0.1"), "sharpe": D("1.0")}
    live = {"return": D("0.1"), "sharpe": D("1.0"), "volatility": D("0.2")}

    first = calculate_drift_metrics(backtest, live)
    second = calculate_drift_metrics(backtest, live)

    assert [m.name for m in first] == ["return", "sharpe", "volatility"]
    assert first == second


def test_a_zero_baseline_is_material_not_absent():
    metrics = calculate_drift_metrics({"profit_factor": D("0")}, {"profit_factor": D("1.5")})

    assert metrics[0].significance == "high"
    assert metrics[0].difference == D("1.5")


def test_execution_drift_keeps_decimal_precision():
    """Regression: fill rates were computed with float division."""
    backtest_fills = [
        {"slippage_bps": 10, "filled": True, "quantity": 1},
        {"slippage_bps": 10, "filled": False, "quantity": 1},
        {"slippage_bps": 10, "filled": False, "quantity": 1},
    ]
    live_fills = list(backtest_fills)

    report = analyze_execution_drift(backtest_fills, live_fills)
    fill_rate = next(m for m in report.metrics if m.name == "fill_rate")

    assert fill_rate.backtest_value == D(1) / D(3)
    assert fill_rate.live_value == D(1) / D(3)


def test_execution_drift_without_data_is_explicit():
    report = analyze_execution_drift([], [])

    assert report.drift_classification == "insufficient_data"
    assert report.warnings


# -- the bridge --------------------------------------------------------------


def _candles(count: int = 400) -> list[Candle]:
    candles = []
    price = D("100")
    for index in range(count):
        price = max(D("10"), price + D(str(0.5 * math.sin(index / 12.0))))
        open_time = START + index * HOUR
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
                volume=D("10"),
            )
        )
    return candles


def _runs(position_fraction: Decimal = D("0.5")):
    candles = _candles()
    config = PaperSessionConfig(
        interval="1h",
        initial_capital=D("10000"),
        position_fraction=position_fraction,
    )
    paper = run_paper_session(
        candles, MACrossoverStrategy(fast=5, slow=20), config=config
    )
    backtest = run_backtest(
        candles,
        MACrossoverStrategy(fast=5, slow=20),
        BacktestConfig(
            initial_capital=D("10000"),
            position_fraction=position_fraction,
            costs=config.costs(),
        ),
    )
    return backtest, paper


def test_bridge_compares_a_matched_pair_without_a_sizing_warning():
    backtest, paper = _runs(D("0.5"))

    report = drift_report_from_results(backtest, paper)

    assert report.metrics
    assert not any("SIZING MISMATCH" in w for w in report.warnings)
    returns = next(m for m in report.metrics if m.name == "return")
    assert returns.pct_difference < D("0.05"), (
        "same strategy, same candles and same sizing must not show return drift"
    )


def test_bridge_flags_a_sizing_mismatch_instead_of_reporting_it_as_drift():
    candles = _candles()
    config = PaperSessionConfig(
        interval="1h", initial_capital=D("10000"), position_fraction=D("0.5")
    )
    paper = run_paper_session(
        candles, MACrossoverStrategy(fast=5, slow=20), config=config
    )
    backtest = run_backtest(
        candles,
        MACrossoverStrategy(fast=5, slow=20),
        BacktestConfig(initial_capital=D("10000"), position_fraction=D("1")),
    )

    report = drift_report_from_results(backtest, paper)

    assert any("SIZING MISMATCH" in w for w in report.warnings)


def test_render_drift_report_is_plain_text_with_the_metrics():
    backtest, paper = _runs(D("0.5"))

    text = render_drift_report(drift_report_from_results(backtest, paper))

    assert "Live vs backtest drift" in text
    assert "return" in text
    assert "max_drawdown" in text
    assert "Past drift does not predict future drift" in text

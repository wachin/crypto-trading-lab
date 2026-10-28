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
    DRAWDOWN_TOLERANCE,
    LIKELY_CAUSES,
    StrategyHealth,
    analyze_execution_drift,
    assess_drift,
    calculate_drift_metrics,
    calculate_regime_drift,
    drift_over_time,
    drift_report_from_results,
    expected_ranges,
    likely_causes,
    render_drift_analysis,
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

# -- 63.2 expected ranges, drift over time and the verdict ------------------


def _backtest_and_paper(taker_fee: Decimal = D("0.001")):
    """The matched pair used by the chapter 63.2 tests."""
    candles = _candles()
    config = PaperSessionConfig(
        interval="1h",
        initial_capital=D("10000"),
        position_fraction=D("0.5"),
        taker_fee=taker_fee,
    )
    paper = run_paper_session(
        candles, MACrossoverStrategy(fast=5, slow=20), config=config
    )
    # The backtest keeps the engine defaults (0.1 % taker fee) so raising the
    # paper fee is a real difference between the two runs, not a matched one.
    backtest = run_backtest(
        candles,
        MACrossoverStrategy(fast=5, slow=20),
        BacktestConfig(
            initial_capital=D("10000"),
            position_fraction=D("0.5"),
        ),
    )
    return backtest, paper


def test_expected_ranges_contain_the_return_the_backtest_realised():
    """The band must be anchored on the observed run, not on its trades only."""
    backtest, _ = _backtest_and_paper()

    ranges = expected_ranges(backtest)

    assert set(ranges) == {"return", "max_drawdown"}
    assert ranges["return"].contains(backtest.return_fraction)
    assert ranges["return"].low < ranges["return"].high
    assert ranges["return"].basis != ""


def test_expected_ranges_are_deterministic():
    """The seed is recorded and the same seed gives the same band."""
    backtest, _ = _backtest_and_paper()

    first = expected_ranges(backtest, scenarios=100, seed=7)
    second = expected_ranges(backtest, scenarios=100, seed=7)

    assert first == second
    assert first["return"].seed == 7
    assert first["return"].scenarios == 100


def test_expected_ranges_need_two_trades_and_say_nothing_when_they_lack_them():
    """One trade is not a distribution; the band stays empty on purpose."""
    from crypto_trading_lab.backtesting.engine import NullStrategy

    backtest = run_backtest(_candles(80), NullStrategy(), BacktestConfig())

    assert expected_ranges(backtest) == {}


def test_drawdown_band_is_anchored_on_the_observed_drawdown():
    """Trade resampling cannot see intra-trade drawdown, and the basis says so."""
    backtest, _ = _backtest_and_paper()

    band = expected_ranges(backtest)["max_drawdown"]

    assert band.low == 0
    assert "tolerance" in band.basis
    assert "intra-trade" in band.basis
    assert band.high >= 0
    assert DRAWDOWN_TOLERANCE > 1


def test_drift_over_time_reports_each_slice():
    """63.2: drift over time, not a single value."""
    curve = [D(value) for value in ("100", "110", "120", "90", "95", "100")]

    periods = drift_over_time(curve, curve, buckets=3)

    assert len(periods) == 3
    assert all(period.drift == 0 for period in periods)
    assert [period.index for period in periods] == [0, 1, 2]
    assert periods[-1].end == len(curve)


def test_drift_over_time_shows_a_divergence_the_total_hides():
    """Two curves with the same end value can drift in opposite directions."""
    backtest = [D("100"), D("120"), D("80"), D("100")]
    live = [D("100"), D("80"), D("120"), D("100")]

    periods = drift_over_time(backtest, live, buckets=2)

    assert periods[0].drift < 0
    assert periods[1].drift > 0


def test_drift_over_time_uses_the_common_length():
    """A shorter paper run compares the part both runs share."""
    periods = drift_over_time([D("100")] * 6, [D("100")] * 4, buckets=2)

    assert periods
    assert periods[-1].end == 4


def test_assess_drift_calls_a_matched_run_healthy():
    """Same strategy, candles and sizing: no degradation to report."""
    backtest, paper = _backtest_and_paper()

    assessment = assess_drift(backtest, paper)

    assert assessment.health is StrategyHealth.HEALTHY
    assert assessment.report is not None
    assert {item.name for item in assessment.metrics} == {
        "return",
        "max_drawdown",
    }
    assert assessment.evidence["rule"]
    assert "inside" in assessment.reasons[0]


def test_assess_drift_marks_meaningful_degradation():
    """A 5 % taker fee is not noise: the verdict must say so."""
    backtest, paper = _backtest_and_paper(taker_fee=D("0.05"))

    assessment = assess_drift(backtest, paper)

    assert assessment.health is StrategyHealth.DEGRADED
    degraded = [item for item in assessment.metrics if item.verdict == "degraded"]
    assert degraded
    assert "degradation, not noise" in assessment.reasons[0] or any(
        "degradation, not noise" in reason for reason in assessment.reasons
    )
    assert degraded[0].causes


def test_assess_drift_without_a_distribution_is_not_called_healthy():
    """A run with no trades cannot be validated, and is not "healthy"."""
    from crypto_trading_lab.backtesting.engine import NullStrategy

    candles = _candles(120)
    backtest = run_backtest(candles, NullStrategy(), BacktestConfig())
    paper = run_paper_session(
        candles,
        MACrossoverStrategy(fast=5, slow=20),
        config=PaperSessionConfig(interval="1h"),
    )

    assessment = assess_drift(backtest, paper)

    assert assessment.health is StrategyHealth.SUSPICIOUS
    assert assessment.metrics == ()
    assert any("unvalidated" in reason for reason in assessment.reasons)


def test_every_likely_cause_is_a_whole_sentence():
    """Causes are shown to a beginner: no fragments, no dangling clauses."""
    for metric, causes in LIKELY_CAUSES.items():
        assert causes, metric
        for cause in causes:
            assert cause[0].isupper(), (metric, cause)
            assert cause.endswith("."), (metric, cause)
    assert likely_causes("return") == LIKELY_CAUSES["return"]
    assert likely_causes("something_else")


def test_render_drift_analysis_has_the_chapter_63_2_sections():
    backtest, paper = _backtest_and_paper()

    text = render_drift_analysis(assess_drift(backtest, paper))

    assert "Live vs backtest drift" in text
    assert "Drift over time" in text
    assert "Expected ranges and verdict" in text
    assert "status: healthy" in text
    assert "basis:" in text

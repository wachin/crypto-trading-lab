"""Live vs backtest drift analysis (ROADMAP.md chapter 63).

Quantifies how far a paper/live run has moved from the backtest that
motivated it: returns, drawdown, trades, fees and slippage. The comparison
is only meaningful when both runs used the same strategy over the same
candles, which is the caller's responsibility (``drift_report_from_results``
documents it).

Drift is a *research* signal: it says the live behaviour differs from the
model, never that the strategy will keep working.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import TYPE_CHECKING, Sequence

if TYPE_CHECKING:  # pragma: no cover - typing only, avoids an import cycle
    from crypto_trading_lab.backtesting.engine import BacktestResult
    from crypto_trading_lab.paper_session import PaperSessionResult

#: Relative difference above which a metric counts as materially drifted,
#: used when the caller does not provide a per-metric threshold.
DEFAULT_DRIFT_THRESHOLD = Decimal("0.15")


@dataclass(frozen=True)
class DriftMetric:
    """Single drift metric."""

    name: str
    backtest_value: Decimal
    live_value: Decimal
    difference: Decimal
    pct_difference: Decimal
    significance: str  # "low", "medium", "high"


@dataclass(frozen=True)
class DriftReport:
    """Complete drift analysis report."""

    strategy_name: str
    backtest_period: str
    live_period: str
    metrics: list[DriftMetric]
    overall_drift_score: Decimal
    drift_classification: str  # "low", "moderate", "high", "severe"
    warnings: list[str]
    timestamp: datetime


def calculate_drift_metrics(
    backtest_metrics: dict[str, Decimal],
    live_metrics: dict[str, Decimal],
    thresholds: dict[str, Decimal] | None = None,
) -> list[DriftMetric]:
    """Calculate drift between backtest and live metrics (63.1).

    ``thresholds`` are **relative** fractions (``0.10`` means 10 %), and
    the default set follows the chapter-63 document ("drift exceeds 20 % of
    the backtest metric"). The result is sorted by metric name so the same
    inputs always produce the same report.
    """
    if thresholds is None:
        thresholds = {
            "return": Decimal("0.10"),        # 10 % relative difference
            "sharpe": Decimal("0.30"),        # 30 % relative difference
            "max_drawdown": Decimal("0.05"),  # 5 % relative difference
            "win_rate": Decimal("0.10"),
            "profit_factor": Decimal("0.20"),
            "volatility": Decimal("0.15"),
            "avg_trade": Decimal("0.20"),
        }

    metrics: list[DriftMetric] = []
    common_keys = sorted(set(backtest_metrics) & set(live_metrics))

    for key in common_keys:
        bt_val = backtest_metrics[key]
        live_val = live_metrics[key]

        if bt_val == 0:
            # No baseline to take a percentage of. A metric that appears
            # (or vanishes) is material, not "no drift".
            difference = live_val
            pct_diff = Decimal(0)
            significance = "high" if live_val != 0 else "low"
        else:
            difference = live_val - bt_val
            pct_diff = abs(difference / bt_val)
            threshold = thresholds.get(key, DEFAULT_DRIFT_THRESHOLD)
            if pct_diff > threshold * Decimal(2):
                significance = "high"
            elif pct_diff > threshold:
                significance = "medium"
            else:
                significance = "low"

        metrics.append(
            DriftMetric(
                name=key,
                backtest_value=bt_val,
                live_value=live_val,
                difference=difference,
                pct_difference=pct_diff,
                significance=significance,
            )
        )

    return metrics


def classify_drift(drift_metrics: list[DriftMetric]) -> tuple[Decimal, str]:
    """Classify overall drift level (63.2).

    Returns: (drift_score, classification)
    """
    if not drift_metrics:
        return Decimal(0), "low"

    # Weight by significance so a high-drift metric cannot be averaged away
    # by several quiet ones.
    weights = {"low": 1, "medium": 2, "high": 3}
    total_weight = 0
    weighted_sum = Decimal(0)

    for metric in drift_metrics:
        weight = weights.get(metric.significance, 1)
        total_weight += weight
        weighted_sum += metric.pct_difference * Decimal(weight)

    avg_drift = (
        weighted_sum / Decimal(total_weight) if total_weight > 0 else Decimal(0)
    )

    if avg_drift < Decimal("0.05"):
        classification = "low"
    elif avg_drift < Decimal("0.15"):
        classification = "moderate"
    elif avg_drift < Decimal("0.30"):
        classification = "high"
    else:
        classification = "severe"

    return avg_drift, classification


def generate_drift_report(
    strategy_name: str,
    backtest_metrics: dict[str, Decimal],
    live_metrics: dict[str, Decimal],
    backtest_period: str,
    live_period: str,
) -> DriftReport:
    """Generate complete drift analysis report (63.3)."""
    drift_metrics = calculate_drift_metrics(backtest_metrics, live_metrics)
    drift_score, classification = classify_drift(drift_metrics)

    warnings = []
    for metric in drift_metrics:
        if metric.significance == "high":
            warnings.append(
                f"HIGH DRIFT in {metric.name}: backtest={metric.backtest_value:.4f}, "
                f"live={metric.live_value:.4f}, diff={metric.difference:.4f} "
                f"({metric.pct_difference:.1%})"
            )
        elif metric.significance == "medium":
            warnings.append(
                f"MODERATE DRIFT in {metric.name}: backtest={metric.backtest_value:.4f}, "
                f"live={metric.live_value:.4f}, diff={metric.difference:.4f} "
                f"({metric.pct_difference:.1%})"
            )

    if drift_score > Decimal("0.3"):
        warnings.append("OVERALL DRIFT IS SEVERE - Strategy may not be viable live")
    elif drift_score > Decimal("0.15"):
        warnings.append("OVERALL DRIFT IS HIGH - Strategy requires investigation")
    elif drift_score > Decimal("0.05"):
        warnings.append("MODERATE DRIFT detected - Monitor closely")

    return DriftReport(
        strategy_name=strategy_name,
        backtest_period=backtest_period,
        live_period=live_period,
        metrics=drift_metrics,
        overall_drift_score=drift_score,
        drift_classification=classification,
        warnings=warnings,
        timestamp=datetime.now(timezone.utc),
    )


def analyze_execution_drift(
    backtest_fills: list[dict],
    live_fills: list[dict],
) -> DriftReport:
    """Analyze execution drift between backtest and live fills (63.4).

    Compares fill prices, quantities, slippage, and timing.
    """
    if not backtest_fills or not live_fills:
        return DriftReport(
            strategy_name="unknown",
            backtest_period="",
            live_period="",
            metrics=[],
            overall_drift_score=Decimal(0),
            drift_classification="insufficient_data",
            warnings=["Insufficient fill data for comparison"],
            timestamp=datetime.now(timezone.utc),
        )

    bt_slippage = [Decimal(str(f.get("slippage_bps", 0))) for f in backtest_fills]
    live_slippage = [Decimal(str(f.get("slippage_bps", 0))) for f in live_fills]

    bt_avg_slippage = sum(bt_slippage) / Decimal(len(bt_slippage))
    live_avg_slippage = sum(live_slippage) / Decimal(len(live_slippage))

    # Decimal division, not float: ``sum(...) / len(...)`` would leak
    # binary floating point into a money-adjacent report.
    bt_fill_rate = Decimal(
        sum(1 for f in backtest_fills if f.get("filled", False))
    ) / Decimal(len(backtest_fills))
    live_fill_rate = Decimal(
        sum(1 for f in live_fills if f.get("filled", False))
    ) / Decimal(len(live_fills))

    bt_avg_size = (
        sum(Decimal(str(f.get("quantity", 0))) for f in backtest_fills)
        / Decimal(len(backtest_fills))
    )
    live_avg_size = (
        sum(Decimal(str(f.get("quantity", 0))) for f in live_fills)
        / Decimal(len(live_fills))
    )

    metrics = calculate_drift_metrics(
        {
            "avg_slippage_bps": bt_avg_slippage,
            "fill_rate": bt_fill_rate,
            "avg_fill_size": bt_avg_size,
        },
        {
            "avg_slippage_bps": live_avg_slippage,
            "fill_rate": live_fill_rate,
            "avg_fill_size": live_avg_size,
        },
    )

    drift_score, classification = classify_drift(metrics)
    warnings = [
        f"{m.significance.upper()} execution drift in {m.name}"
        for m in metrics
        if m.significance != "low"
    ]

    return DriftReport(
        strategy_name="execution_analysis",
        backtest_period="backtest",
        live_period="live",
        metrics=metrics,
        overall_drift_score=drift_score,
        drift_classification=classification,
        warnings=warnings,
        timestamp=datetime.now(timezone.utc),
    )


def _mean(values: Sequence[Decimal]) -> Decimal:
    if not values:
        return Decimal(0)
    return sum(values) / Decimal(len(values))


def _max_drawdown(equity_curve: Sequence[Decimal]) -> Decimal:
    """Largest peak-to-trough decline in an equity curve (chapter 40)."""
    peak = Decimal(0)
    worst = Decimal(0)
    for value in equity_curve:
        if value > peak:
            peak = value
        if peak > 0:
            drawdown = (peak - value) / peak
            if drawdown > worst:
                worst = drawdown
    return worst


def calculate_regime_drift(
    backtest_returns: list[Decimal],
    live_returns: list[Decimal],
    regime_labels: list[str] | None = None,
) -> dict[str, Decimal]:
    """Calculate drift per market regime (63.5).

    Compares performance in different market regimes. Regression: the
    ``"bt"`` bucket used to receive the *live* return as well, so every
    regime reported a drift of exactly zero.
    """
    if regime_labels is None:
        return {"overall_drift": _mean(live_returns) - _mean(backtest_returns)}

    if not (
        len(regime_labels) == len(backtest_returns) == len(live_returns)
    ):
        raise ValueError(
            "backtest_returns, live_returns and regime_labels must have "
            "the same length"
        )

    regimes: dict[str, dict[str, list[Decimal]]] = {}
    for backtest_return, live_return, regime in zip(
        backtest_returns, live_returns, regime_labels
    ):
        bucket = regimes.setdefault(regime, {"bt": [], "live": []})
        bucket["bt"].append(backtest_return)
        bucket["live"].append(live_return)

    return {
        regime: _mean(data["live"]) - _mean(data["bt"])
        for regime, data in regimes.items()
    }


def drift_report_from_results(
    backtest: "BacktestResult",
    paper: "PaperSessionResult",
    *,
    strategy_name: str | None = None,
) -> DriftReport:
    """Compare a backtest with a paper session on the same strategy (63).

    Both runs must share the strategy, the candles **and the position
    sizing** (``BacktestConfig.position_fraction`` equal to the paper
    session's ``position_fraction``); otherwise the report would present a
    sizing artefact as execution drift. A mismatch is reported as a warning
    rather than silently producing a misleading number. Metrics are
    normalised by initial capital so two account sizes stay comparable.
    """
    backtest_capital = backtest.initial_capital or Decimal(1)
    paper_capital = paper.config.initial_capital or Decimal(1)

    backtest_metrics = {
        "return": backtest.return_fraction,
        "max_drawdown": _max_drawdown(backtest.equity_curve),
        "number_of_trades": Decimal(len(backtest.trades)),
        "fee_drag": backtest.total_fees / backtest_capital,
        # The engine tracks slippage and spread separately, while the paper
        # session's ``total_slippage`` is the whole price concession at fill
        # time. Sum them so the two sides mean the same thing.
        "slippage_spread_drag": (
            backtest.total_slippage + backtest.total_spread
        ) / backtest_capital,
    }
    live_metrics = {
        "return": paper.net_profit / paper_capital,
        "max_drawdown": paper.max_drawdown,
        "number_of_trades": Decimal(len(paper.journal.closed_trades())),
        "fee_drag": paper.total_fees / paper_capital,
        "slippage_spread_drag": paper.total_slippage / paper_capital,
    }

    report = generate_drift_report(
        strategy_name=(
            strategy_name or backtest.strategy_name or paper.strategy_name
        ),
        backtest_metrics=backtest_metrics,
        live_metrics=live_metrics,
        backtest_period=backtest.dataset_period or "backtest",
        live_period=paper.dataset_id or "paper",
    )

    backtest_fraction = backtest.config_metadata.get("position_fraction")
    paper_fraction = paper.config.position_fraction
    if (
        backtest_fraction is not None
        and Decimal(backtest_fraction) != paper_fraction
    ):
        report = replace(
            report,
            warnings=[
                (
                    "SIZING MISMATCH: the backtest used position_fraction="
                    f"{backtest_fraction} and the paper session used "
                    f"{paper_fraction}. Return, drawdown and cost drift "
                    "below are distorted by sizing; re-run the backtest "
                    "with the same fraction."
                )
            ]
            + report.warnings,
        )

    return report


def render_drift_report(report: DriftReport) -> str:
    """Plain-text rendering shared by the UI and the CLI."""
    lines = [
        "== Live vs backtest drift (chapter 63) ==",
        f"Strategy: {report.strategy_name}",
        f"Backtest period: {report.backtest_period}",
        f"Paper/live period: {report.live_period}",
        (
            f"Overall drift: {report.overall_drift_score:.2%} "
            f"({report.drift_classification})"
        ),
        "",
        f"{'Metric':<20}{'Backtest':>14}{'Paper/live':>14}"
        f"{'Drift':>10}  Significance",
    ]
    for metric in report.metrics:
        lines.append(
            f"{metric.name:<20}{metric.backtest_value:>14.6f}"
            f"{metric.live_value:>14.6f}{metric.pct_difference:>10.2%}"
            f"  {metric.significance}"
        )
    if report.warnings:
        lines.append("")
        lines.extend(report.warnings)
    lines.append("")
    lines.append(DRIFT_ANALYSIS_WARNING)
    return "\n".join(lines)


# --- 63.2 Expected ranges, drift over time, and the strategy status --------

#: Resampling defaults for the expected-range band (63.2). Recorded in the
#: assessment evidence so a reader can reproduce the band.
DEFAULT_BOOTSTRAP_SCENARIOS = 500
DEFAULT_BOOTSTRAP_SEED = 1
DEFAULT_DRIFT_BUCKETS = 5

#: Metrics where a *larger* value is worse. Everything else is worse when it
#: falls below the expected range.
HIGHER_IS_WORSE = frozenset({"max_drawdown"})


#: A live drawdown up to this multiple of the backtest's own drawdown is
#: treated as normal variability. Drawdowns are systematically understated by
#: any single backtest sample, so a live run exceeding it slightly is
#: expected; exceeding it by a lot is not.
DRAWDOWN_TOLERANCE = Decimal("1.5")


@dataclass(frozen=True)
class ExpectedRange:
    """Range a metric is expected to fall in, built from the backtest (63.2)."""

    low: Decimal
    high: Decimal
    scenarios: int
    seed: int
    #: How the band was produced, stated in the report so the reader can
    #: judge it instead of trusting it.
    basis: str = "resampled backtest trades, 5th-95th percentile"

    def contains(self, value: Decimal) -> bool:
        return self.low <= value <= self.high

    def half_width(self) -> Decimal:
        """Half the range width; the unit used to judge a miss (63.2)."""
        return (self.high - self.low) / Decimal(2)


def _percentile(values: Sequence[Decimal], fraction: Decimal) -> Decimal:
    """Nearest-rank percentile of a non-empty sequence."""
    ordered = sorted(values)
    index = int((fraction * Decimal(len(ordered) - 1)).to_integral_value())
    return ordered[index]


def expected_ranges(
    backtest: "BacktestResult",
    *,
    scenarios: int = DEFAULT_BOOTSTRAP_SCENARIOS,
    seed: int = DEFAULT_BOOTSTRAP_SEED,
) -> dict[str, ExpectedRange]:
    """Range a live run is expected to fall in, from the backtest itself (63.2).

    The trades the backtest actually produced are resampled with replacement
    (a bootstrap) to measure how much the total return of such a sequence
    varies. That spread is then centred on the return the backtest actually
    realised, because the bootstrap knows the closed trades only while the
    run also holds open positions. Maximum drawdown is not resampled at all:
    a trade-level bootstrap cannot see the drawdown that happens *inside* a
    trade, so that band is anchored on the drawdown the equity curve showed
    and widened by a documented tolerance. Each band carries its ``basis``.

    This is deliberately narrow in what it claims: it says *"if live trades
    came from the same distribution as these backtest trades, the result
    would usually land here"*. It does not model a change of regime, and a
    result inside the band is not evidence that the edge is real.

    Returns an empty dict when the backtest has fewer than two trades: with
    one trade there is no distribution to resample, and inventing one would
    be the kind of false precision this project refuses.
    """
    if scenarios < 1:
        raise ValueError("scenarios must be at least 1")
    trades = list(backtest.trades)
    if len(trades) < 2:
        return {}

    payoffs = [trade.net_pnl for trade in trades]
    capital = backtest.initial_capital or Decimal(1)
    rng = random.Random(seed)

    sampled: list[Decimal] = []
    for _ in range(scenarios):
        total = Decimal(0)
        for _ in payoffs:
            total += payoffs[rng.randrange(len(payoffs))]
        sampled.append(total / capital)

    five = Decimal("0.05")
    ninety_five = Decimal("0.95")
    # The bootstrap only describes the *spread* of the trade sequence, so it
    # is anchored on the return the backtest actually realised. Without the
    # anchor the band drifts away from the observed result whenever the run
    # ends holding a position: the open position is marked to market in
    # ``final_equity`` but is not a closed trade, so it never appears in the
    # sampled payoffs.
    centre = _mean(sampled)
    observed = backtest.return_fraction
    return_low = observed + (_percentile(sampled, five) - centre)
    return_high = observed + (_percentile(sampled, ninety_five) - centre)
    # Drawdown comes from the equity curve, not from the resampled trades
    # (see the docstring): it is widened by DRAWDOWN_TOLERANCE and says so.
    backtest_drawdown = _max_drawdown(backtest.equity_curve)
    return {
        "return": ExpectedRange(
            low=return_low,
            high=return_high,
            scenarios=scenarios,
            seed=seed,
            basis=(
                "backtest return widened by the resampled trade spread "
                "(5th-95th percentile, anchored on the observed return)"
            ),
        ),
        "max_drawdown": ExpectedRange(
            low=Decimal(0),
            high=backtest_drawdown * DRAWDOWN_TOLERANCE,
            scenarios=scenarios,
            seed=seed,
            basis=(
                "backtest max drawdown x "
                f"{DRAWDOWN_TOLERANCE} tolerance (trade resampling cannot "
                "see intra-trade drawdown)"
            ),
        ),
    }


@dataclass(frozen=True)
class DriftPeriod:
    """Drift inside one slice of the run (63.2: not a single value)."""

    index: int
    start: int
    end: int          # exclusive
    backtest_return: Decimal
    live_return: Decimal
    drift: Decimal


def drift_over_time(
    backtest_curve: Sequence[Decimal],
    live_curve: Sequence[Decimal],
    *,
    buckets: int = DEFAULT_DRIFT_BUCKETS,
) -> tuple[DriftPeriod, ...]:
    """Split both equity curves into equal slices and compare each (63.2).

    A single drift number hides the shape of a run: a strategy can match the
    backtest overall while drifting away from it in the last third. The two
    curves are cut into ``buckets`` contiguous slices of equal candle count
    and the return of each slice is compared. Only the overlapping candles
    are used, so a paper session shorter than the backtest compares the
    common part instead of failing.
    """
    if buckets < 1:
        raise ValueError("buckets must be at least 1")
    length = min(len(backtest_curve), len(live_curve))
    if length < 2:
        return ()

    size = length // buckets
    if size < 1:
        buckets = 1
        size = length

    periods: list[DriftPeriod] = []
    for index in range(buckets):
        start = index * size
        end = length if index == buckets - 1 else start + size
        if end - start < 2:
            continue
        base = start - 1 if start > 0 else 0
        backtest_return = _slice_return(backtest_curve, base, end)
        live_return = _slice_return(live_curve, base, end)
        periods.append(
            DriftPeriod(
                index=index,
                start=start,
                end=end,
                backtest_return=backtest_return,
                live_return=live_return,
                drift=live_return - backtest_return,
            )
        )
    return tuple(periods)


def _slice_return(curve: Sequence[Decimal], base: int, end: int) -> Decimal:
    """Return from ``curve[base]`` to the last value before ``end``."""
    start_value = curve[base]
    if start_value == 0:
        return Decimal(0)
    return (curve[end - 1] - start_value) / start_value


#: Likely causes per drift dimension (63.2). Written for a beginner: each
#: line names a mechanism the user can check, not a verdict.
LIKELY_CAUSES: dict[str, tuple[str, ...]] = {
    "return": (
        "A market regime the strategy was not built for (chapter 46), for "
        "example a trending market where the backtest was mostly ranging.",
        "Different volatility: the same signal produces bigger or smaller "
        "moves, so a fixed stop or sizing behaves differently.",
        "Position sizing that differs from the backtest (check for the "
        "SIZING MISMATCH warning before reading this number).",
        "The paper session covering a different slice of history than the "
        "backtest period.",
    ),
    "max_drawdown": (
        "A run of losses the backtest never sampled, which a band can only "
        "bound, never rule out.",
        "A volatility increase that widens every swing, including the "
        "losing ones.",
        "Risk-manager rejections or forced exits that the backtest does "
        "not model.",
    ),
    "fee_drag": (
        "More trades than the backtest for the same period, so fixed fees "
        "accumulate faster.",
        "A fee schedule that changed, or a maker/taker mix that differs "
        "from the assumption.",
        "Smaller average position sizes, which make the fixed part of the "
        "cost relatively larger.",
    ),
    "slippage_spread_drag": (
        "Thinner liquidity than the model assumed (chapter 56.4).",
        "Latency: the price moved between the decision and the fill.",
        "The execution model and the live fills are not the same thing; "
        "compare them with compare_execution_models (chapter 56.5).",
    ),
    "number_of_trades": (
        "The risk manager rejecting orders the backtest would have filled.",
        "A fill-rate difference: partial fills or rejections (chapter 56).",
        "Signals that depend on an indicator warm-up the session did not "
        "have at the start of the replay.",
    ),
}

#: Generic causes used for a metric the table does not name.
GENERIC_CAUSES = (
    "The live sample is small; one or two trades can move this metric a lot.",
    "Market conditions differ from the backtest period.",
    "The execution and risk assumptions differ between the two runs.",
)


def likely_causes(metric_name: str) -> tuple[str, ...]:
    """Likely causes for one drift dimension (63.2)."""
    return LIKELY_CAUSES.get(metric_name, GENERIC_CAUSES)


class StrategyHealth(Enum):
    """How a strategy looks after the drift analysis (63.2, chapter 64)."""

    HEALTHY = "healthy"
    SUSPICIOUS = "suspicious"
    DEGRADED = "degraded"


@dataclass(frozen=True)
class MetricAssessment:
    """One metric judged against the range the backtest predicted (63.2)."""

    name: str
    live_value: Decimal
    expected: ExpectedRange
    verdict: str  # "within_expected" | "outside_expected" | "degraded"
    causes: tuple[str, ...]


@dataclass(frozen=True)
class DriftAssessment:
    """Chapter 63.2 verdict: expected variability, or meaningful degradation."""

    report: DriftReport
    health: StrategyHealth
    metrics: tuple[MetricAssessment, ...]
    periods: tuple[DriftPeriod, ...]
    reasons: tuple[str, ...]
    evidence: dict[str, str]
    note: str

    def summary(self) -> str:
        """Plain-language summary for beginners."""
        lines = [
            f"Strategy status: {self.health.value.upper()}",
            (
                f"Overall drift: {self.report.overall_drift_score:.2%} "
                f"({self.report.drift_classification})"
            ),
        ]
        lines.extend(f"- {reason}" for reason in self.reasons)
        if self.periods:
            worst = min(self.periods, key=lambda period: period.drift)
            lines.append(
                f"Worst period: slice {worst.index + 1} "
                f"(candles {worst.start}-{worst.end - 1}), drift "
                f"{worst.drift:+.2%}"
            )
        lines.append(self.note)
        return "\n".join(lines)


def _judge(
    name: str, live_value: Decimal, expected: ExpectedRange
) -> tuple[str, str]:
    """Return (verdict, one-line reason) for one metric (63.2).

    The verdicts separate three situations the chapter insists on keeping
    apart: inside the band (expected variability), just outside it by less
    than one half-width (a tail of the same variability), and beyond that
    (meaningful). A favourable excursion beyond the band is *also*
    meaningful: it usually means the model or the data is wrong, and calling
    it "good news" would hide that.
    """
    band = f"[{expected.low:.2%}, {expected.high:.2%}]"
    if expected.contains(live_value):
        return "within_expected", (
            f"{name} {live_value:.2%} is inside the backtest's expected "
            f"range {band} — normal variability, not degradation."
        )

    half_width = expected.half_width()
    if name in HIGHER_IS_WORSE:
        adverse = live_value > expected.high
        beyond = (
            live_value - expected.high if adverse else expected.low - live_value
        )
        side = "above" if adverse else "below"
    else:
        adverse = live_value < expected.low
        beyond = (
            expected.low - live_value if adverse else live_value - expected.high
        )
        side = "below" if adverse else "above"

    if half_width <= 0 or beyond <= half_width:
        return "expected_tail", (
            f"{name} {live_value:.2%} is {side} the expected range {band} "
            f"by {beyond:.2%}, within one half-width of it — treat it as a "
            "tail of normal variability and keep watching."
        )

    if adverse:
        return "degraded", (
            f"{name} {live_value:.2%} is {side} the expected range {band} "
            f"by {beyond:.2%}, more than half the range width — this is "
            "degradation, not noise."
        )
    return "outside_expected", (
        f"{name} {live_value:.2%} is {side} the expected range {band} by "
        f"{beyond:.2%}. A result better than the model predicted is also a "
        "warning: the model, the data or the assumptions may be wrong."
    )


DRIFT_ASSESSMENT_NOTE = (
    "The expected range comes from resampling the trades this backtest "
    "actually produced. It describes that sample, not the future: a result "
    "inside the range is not proof that the edge is real, and a result "
    "outside it is a reason to look, not a reason to stop thinking."
)


def assess_drift(
    backtest: "BacktestResult",
    paper: "PaperSessionResult",
    *,
    strategy_name: str | None = None,
    scenarios: int = DEFAULT_BOOTSTRAP_SCENARIOS,
    seed: int = DEFAULT_BOOTSTRAP_SEED,
    buckets: int = DEFAULT_DRIFT_BUCKETS,
    report: DriftReport | None = None,
) -> DriftAssessment:
    """Judge a paper session against what the backtest predicted (63.2).

    Combines the four things the chapter asks for: the expected range from
    the backtest, the drift over time, the likely causes of each difference,
    and a verdict that separates expected variability from meaningful
    degradation. The verdict is evidence for chapter 64; it never changes
    the risk manager or places an order.
    """
    drift = report or drift_report_from_results(
        backtest, paper, strategy_name=strategy_name
    )
    ranges = expected_ranges(backtest, scenarios=scenarios, seed=seed)
    live_values = {metric.name: metric.live_value for metric in drift.metrics}

    assessments: list[MetricAssessment] = []
    reasons: list[str] = []
    for name in sorted(ranges):
        if name not in live_values:
            continue
        verdict, reason = _judge(name, live_values[name], ranges[name])
        assessments.append(
            MetricAssessment(
                name=name,
                live_value=live_values[name],
                expected=ranges[name],
                verdict=verdict,
                causes=likely_causes(name),
            )
        )
        reasons.append(reason)

    periods = drift_over_time(
        backtest.equity_curve, paper.equity_curve, buckets=buckets
    )

    degraded = [item for item in assessments if item.verdict == "degraded"]
    outside = [item for item in assessments if item.verdict == "outside_expected"]
    if degraded:
        health = StrategyHealth.DEGRADED
    elif outside or drift.drift_classification in ("high", "severe"):
        health = StrategyHealth.SUSPICIOUS
    elif not assessments:
        # Fewer than two backtest trades: nothing to compare against.
        health = StrategyHealth.SUSPICIOUS
        reasons.append(
            "The backtest produced fewer than two trades, so there is no "
            "distribution to compare against. Treat this run as "
            "unvalidated rather than healthy."
        )
    else:
        health = StrategyHealth.HEALTHY

    if periods:
        losing = [period for period in periods if period.drift < 0]
        if len(losing) == len(periods) and len(periods) > 1:
            reasons.append(
                f"Drift is negative in all {len(periods)} slices, so it is "
                "persistent over time rather than one bad window."
            )
            if health is StrategyHealth.HEALTHY:
                health = StrategyHealth.SUSPICIOUS

    evidence = {
        "scenarios": str(scenarios),
        "seed": str(seed),
        "buckets": str(len(periods)),
        "backtest_trades": str(len(backtest.trades)),
        "paper_closed_trades": str(len(paper.journal.closed_trades())),
        "drift_classification": drift.drift_classification,
        "overall_drift_score": str(drift.overall_drift_score),
        "rule": (
            "inside the 5th-95th percentile range = expected variability; "
            "outside it by more than half the range width = degradation"
        ),
    }
    for name, band in sorted(ranges.items()):
        evidence[f"{name}_expected"] = f"{band.low} to {band.high}"

    return DriftAssessment(
        report=drift,
        health=health,
        metrics=tuple(assessments),
        periods=periods,
        reasons=tuple(reasons),
        evidence=evidence,
        note=DRIFT_ASSESSMENT_NOTE,
    )


def render_drift_analysis(assessment: DriftAssessment) -> str:
    """Plain-text rendering of the full chapter 63.2 analysis."""
    lines = [render_drift_report(assessment.report), ""]
    lines.append("== Drift over time ==")
    if not assessment.periods:
        lines.append("Not enough candles to compare the curves over time.")
    for period in assessment.periods:
        lines.append(
            f"  slice {period.index + 1} "
            f"(candles {period.start}-{period.end - 1}): "
            f"backtest {period.backtest_return:+.2%}, "
            f"paper {period.live_return:+.2%}, "
            f"drift {period.drift:+.2%}"
        )
    lines.append("")
    lines.append("== Expected ranges and verdict (chapter 63.2) ==")
    for item in assessment.metrics:
        lines.append(
            f"  {item.name}: {item.live_value:.4f} vs expected "
            f"[{item.expected.low:.4f}, {item.expected.high:.4f}] "
            f"-> {item.verdict}"
        )
        lines.append(f"    basis: {item.expected.basis}")
    lines.append(f"  status: {assessment.health.value}")
    for reason in assessment.reasons:
        lines.append(f"  - {reason}")
    causes: list[str] = []
    for item in assessment.metrics:
        if item.verdict not in ("degraded", "outside_expected"):
            continue
        for cause in item.causes:
            if cause not in causes:
                causes.append(cause)
    if causes:
        lines.append("  likely causes to check:")
        lines.extend(f"    - {cause}" for cause in causes)
    lines.append("")
    lines.append(assessment.note)
    return "\n".join(lines)


DRIFT_ANALYSIS_WARNING = (
    "Drift analysis compares historical backtest with live results. "
    "Past drift does not predict future drift. Market regime changes, "
    "liquidity shifts, and exchange changes can cause new drift patterns. "
    "Always validate with out-of-sample data before trusting any strategy."
)


__all__ = [
    "DriftMetric",
    "DriftReport",
    "calculate_drift_metrics",
    "classify_drift",
    "generate_drift_report",
    "analyze_execution_drift",
    "calculate_regime_drift",
    "drift_report_from_results",
    "render_drift_report",
    "ExpectedRange",
    "DriftPeriod",
    "DriftAssessment",
    "MetricAssessment",
    "StrategyHealth",
    "expected_ranges",
    "drift_over_time",
    "assess_drift",
    "likely_causes",
    "render_drift_analysis",
    "LIKELY_CAUSES",
    "DRIFT_ASSESSMENT_NOTE",
    "DRIFT_ANALYSIS_WARNING",
]

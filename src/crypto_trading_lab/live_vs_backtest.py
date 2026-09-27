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

from dataclasses import dataclass, replace
from datetime import datetime, timezone
from decimal import Decimal
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
    "DRIFT_ANALYSIS_WARNING",
]

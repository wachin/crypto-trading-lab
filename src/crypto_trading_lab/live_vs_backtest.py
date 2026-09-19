"""Live vs backtest drift analysis (ROADMAP.md chapter 63).

Analyzes and quantifies the difference between backtest results
and live/paper trading performance.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from typing import Sequence


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
    """
    Calculate drift between backtest and live metrics (63.1).
    
    Compares key performance metrics between backtest and live results.
    """
    if thresholds is None:
        thresholds = {
            "return": Decimal("0.10"),        # 10% difference threshold
            "sharpe": Decimal("0.3"),         # 0.3 Sharpe difference
            "max_drawdown": Decimal("0.05"),  # 5% drawdown difference
            "win_rate": Decimal("0.10"),      # 10% win rate difference
            "profit_factor": Decimal("0.2"),  # 20% profit factor difference
            "volatility": Decimal("0.15"),    # 15% volatility difference
            "avg_trade": Decimal("0.20"),     # 20% avg trade difference
        }
    
    metrics = []
    common_keys = set(backtest_metrics.keys()) & set(live_metrics.keys())
    
    for key in common_keys:
        bt_val = backtest_metrics[key]
        live_val = live_metrics[key]
        
        if bt_val == 0:
            diff = Decimal(0)
            pct_diff = Decimal(0)
        else:
            diff = live_val - bt_val
            pct_diff = abs(diff / bt_val)
        
        # Determine significance
        threshold = thresholds.get(key, Decimal("0.15"))
        if pct_diff > threshold * Decimal("2"):
            significance = "high"
        elif pct_diff > threshold:
            significance = "medium"
        else:
            significance = "low"
        
        metrics.append(DriftMetric(
            name=key,
            backtest_value=bt_val,
            live_value=live_val,
            difference=diff,
            pct_difference=pct_diff,
            significance=significance,
        ))
    
    return metrics


def classify_drift(drift_metrics: list[DriftMetric]) -> tuple[Decimal, str]:
    """
    Classify overall drift level (63.2).
    
    Returns: (drift_score, classification)
    """
    if not drift_metrics:
        return Decimal(0), "low"
    
    # Weight by significance
    weights = {"low": 1, "medium": 2, "high": 3}
    total_weight = 0
    weighted_sum = Decimal(0)
    
    for m in drift_metrics:
        w = weights.get(m.significance, 1)
        total_weight += w
        weighted_sum += m.pct_difference * Decimal(w)
    
    avg_drift = weighted_sum / Decimal(total_weight) if total_weight > 0 else Decimal(0)
    
    # Classify
    if avg_drift < Decimal("0.05"):
        classification = "low"
    elif avg_drift < Decimal("0.15"):
        classification = "moderate"
    elif avg_drift < Decimal("0.30"):
        classification = "high"
    else:
        classification = "severe"
    
    return Decimal(str(avg_drift)), classification


def generate_drift_report(
    strategy_name: str,
    backtest_metrics: dict[str, Decimal],
    live_metrics: dict[str, Decimal],
    backtest_period: str,
    live_period: str,
) -> DriftReport:
    """
    Generate complete drift analysis report (63.3).
    """
    drift_metrics = calculate_drift_metrics(backtest_metrics, live_metrics)
    drift_score, classification = classify_drift(drift_metrics)
    
    warnings = []
    for m in drift_metrics:
        if m.significance == "high":
            warnings.append(
                f"HIGH DRIFT in {m.name}: backtest={m.backtest_value:.4f}, "
                f"live={m.live_value:.4f}, diff={m.difference:.4f} ({m.pct_difference:.1%})"
            )
        elif m.significance == "medium":
            warnings.append(
                f"MODERATE DRIFT in {m.name}: backtest={m.backtest_value:.4f}, "
                f"live={m.live_value:.4f}, diff={m.difference:.4f} ({m.pct_difference:.1%})"
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
        overall_drift_score=Decimal(str(drift_score)),
        drift_classification=classification,
        warnings=warnings,
        timestamp=datetime.now(timezone.utc),
    )


def analyze_execution_drift(
    backtest_fills: list[dict],
    live_fills: list[dict],
) -> DriftReport:
    """
    Analyze execution drift between backtest and live fills (63.4).
    
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
    
    # Calculate fill statistics
    bt_slippage = [Decimal(str(f.get("slippage_bps", 0))) for f in backtest_fills]
    live_slippage = [Decimal(str(f.get("slippage_bps", 0))) for f in live_fills]
    
    bt_avg_slippage = sum(bt_slippage) / len(bt_slippage) if bt_slippage else Decimal(0)
    live_avg_slippage = sum(live_slippage) / len(live_slippage) if live_slippage else Decimal(0)
    
    bt_fill_rate = sum(1 for f in backtest_fills if f.get("filled", False)) / len(backtest_fills)
    live_fill_rate = sum(1 for f in live_fills if f.get("filled", False)) / len(live_fills)
    
    bt_avg_size = sum(Decimal(str(f.get("quantity", 0))) for f in backtest_fills) / len(backtest_fills)
    live_avg_size = sum(Decimal(str(f.get("quantity", 0))) for f in live_fills) / len(live_fills)
    
    metrics = calculate_drift_metrics(
        {
            "avg_slippage_bps": bt_avg_slippage,
            "fill_rate": Decimal(str(bt_fill_rate)),
            "avg_fill_size": bt_avg_size,
        },
        {
            "avg_slippage_bps": live_avg_slippage,
            "fill_rate": Decimal(str(live_fill_rate)),
            "avg_fill_size": live_avg_size,
        },
    )
    
    drift_score, classification = classify_drift(metrics)
    
    return DriftReport(
        strategy_name="execution_analysis",
        backtest_period="backtest",
        live_period="live",
        metrics=metrics,
        overall_drift_score=Decimal(str(drift_score)),
        drift_classification=classification,
        warnings=[],
        timestamp=datetime.now(timezone.utc),
    )


def calculate_regime_drift(
    backtest_returns: list[Decimal],
    live_returns: list[Decimal],
    regime_labels: list[str] | None = None,
) -> dict[str, Decimal]:
    """
    Calculate drift per market regime (63.5).
    
    Compares performance in different market regimes.
    """
    if not regime_labels or len(regime_labels) != len(backtest_returns):
        # Simple overall comparison
        bt_avg = sum(backtest_returns) / len(backtest_returns) if backtest_returns else Decimal(0)
        live_avg = sum(live_returns) / len(live_returns) if live_returns else Decimal(0)
        return {"overall_drift": live_avg - bt_avg}
    
    # Group by regime
    regimes = {}
    for bt_r, live_r, regime in zip(backtest_returns, live_returns, regime_labels):
        if regime not in regimes:
            regimes[regime] = {"bt": [], "live": []}
        regimes[regime]["bt"].append(live_r)
        regimes[regime]["live"].append(live_r)
    
    result = {}
    for regime, data in regimes.items():
        bt_avg = sum(data["bt"]) / len(data["bt"]) if data["bt"] else Decimal(0)
        live_avg = sum(data["live"]) / len(data["live"]) if data["live"] else Decimal(0)
        result[regime] = live_avg - bt_avg
    
    return result


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
    "DRIFT_ANALYSIS_WARNING",
]

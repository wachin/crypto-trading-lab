"""Market regime analysis (ROADMAP.md chapter 46).

This module provides research tools for identifying different market conditions
(regimes) and analyzing strategy performance under each regime.

Important: Regime detection is a MODEL, not ground truth. All classifications
carry uncertainty and should be treated as hypotheses to be validated.
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass
from decimal import Decimal
from typing import Sequence


@dataclass(frozen=True)
class Candle:
    """Minimal candle structure for regime analysis."""
    timestamp: str
    close: Decimal
    volume: Decimal


@dataclass(frozen=True)
class RegimeLabels:
    """
    Labels for each point in the series. Each label indicates the dominant
    regime (trending/ranging, high/low volatility) based on the detection
    method and parameters used.
    """
    is_trending: list[bool]
    is_high_volatility: list[bool]
    method: str
    parameters: dict[str, str]


def detect_trending_ranging(
    closes: Sequence[Decimal],
    lookback: int = 20,
    threshold: Decimal = Decimal("0.5"),
) -> RegimeLabels:
    """
    Detect trending vs ranging regimes (Chapter 46.1).

    Uses ADX-like logic: if price moves directionally over a lookback
    window, it's trending; if it oscillates, it's ranging.

    Warning: This is a MODEL, not ground truth. Different methods produce
    different regime labels.
    """
    if len(closes) < lookback:
        raise ValueError("Need enough candles for regime detection")

    labels = []
    for i in range(lookback, len(closes)):
        window = closes[i - lookback:i + 1]
        total_move = abs(window[-1] - window[0])
        sum_moves = sum(abs(window[j] - window[j - 1]) for j in range(1, len(window)))

        # Directionality ratio (similar to ADX concept)
        if sum_moves == 0:
            is_trending = False
        else:
            ratio = total_move / sum_moves
            is_trending = ratio > threshold

        labels.append(is_trending)

    return RegimeLabels(
        is_trending=labels,
        is_high_volatility=[],  # Compute separately
        method="directionality_ratio",
        parameters={
            "lookback": str(lookback),
            "threshold": str(threshold),
        },
    )


def detect_volatility_regime(
    closes: Sequence[Decimal],
    lookback: int = 20,
    threshold_multiplier: Decimal = Decimal("1.0"),
) -> RegimeLabels:
    """
    Detect high vs low volatility regimes (Chapter 46.1).

    Compares recent volatility to historical average volatility.

    Warning: This is a MODEL, not ground truth.
    """
    if len(closes) < lookback * 2:
        raise ValueError("Need enough candles for volatility regime detection")

    # Compute returns
    returns = [
        (closes[i] - closes[i - 1]) / closes[i - 1]
        for i in range(1, len(closes))
    ]

    labels = []
    for i in range(lookback, len(returns)):
        recent = returns[i - lookback:i + 1]
        historical = returns[:i - lookback] if i > lookback else []

        recent_vol = statistics.stdev(recent) if len(recent) > 1 else 0
        hist_vol = statistics.stdev(historical) if len(historical) > 1 else recent_vol

        threshold = hist_vol * threshold_multiplier if hist_vol > 0 else recent_vol
        is_high_vol = recent_vol > threshold

        labels.append(is_high_vol)

    return RegimeLabels(
        is_trending=[],
        is_high_volatility=labels,
        method="volatility_comparison",
        parameters={
            "lookback": str(lookback),
            "threshold_multiplier": str(threshold_multiplier),
        },
    )


@dataclass(frozen=True)
class RegimePerformance:
    """Performance metrics for one regime type (Chapter 46.2)."""
    regime_name: str
    n_periods: int
    total_return: Decimal
    profit_factor: Decimal
    win_rate: Decimal
    avg_return_per_period: Decimal


def compute_regime_performance(
    returns: Sequence[Decimal],
    regime_labels: Sequence[bool],
    regime_name: str,
) -> RegimePerformance | None:
    """
    Compute performance metrics conditioned on regime state (Chapter 46.2).

    Returns None if the regime never occurs in the data.
    """
    if len(returns) != len(regime_labels):
        raise ValueError("Returns and regime labels must have same length")

    regime_returns = [r for r, label in zip(returns, regime_labels) if label]

    if not regime_returns:
        return None

    total_return = sum(regime_returns)
    avg_return = total_return / len(regime_returns)

    winners = sum(1 for r in regime_returns if r > 0)
    win_rate = Decimal(winners) / Decimal(len(regime_returns))

    gross_profit = sum(r for r in regime_returns if r > 0)
    gross_loss = abs(sum(r for r in regime_returns if r < 0))

    if gross_loss == 0:
        profit_factor = Decimal("999.0")  # Arbitrarily large
    else:
        profit_factor = gross_profit / gross_loss

    return RegimePerformance(
        regime_name=regime_name,
        n_periods=len(regime_returns),
        total_return=total_return,
        profit_factor=profit_factor,
        win_rate=win_rate,
        avg_return_per_period=avg_return,
    )


def check_regime_concentration(
    regime_labels: Sequence[bool],
    threshold: Decimal = Decimal("0.8"),
) -> str:
    """
    Check if a strategy's performance is concentrated in one regime
    (Chapter 46.2). Returns a warning message if concentration detected.
    """
    n_true = sum(1 for l in regime_labels if l)
    n_false = len(regime_labels) - n_true
    n_total = len(regime_labels)

    if n_total == 0:
        return ""

    concentration = max(n_true, n_false) / n_total

    if concentration > threshold:
        dominant = "active" if n_true > n_false else "inactive"
        return (
            f"Strategy performance appears concentrated ({concentration:.1%}) "
            f"in the {dominant} regime. This may indicate regime dependency."
        )

    return ""


REGIME_DETECTION_WARNING = (
    "Regime detection is a model, not ground truth. Different methods "
    "and parameters produce different regime labels. Treat regime "
    "classifications as hypotheses subject to validation."
)

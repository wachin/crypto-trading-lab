"""Tests for regime analysis (ROADMAP.md chapter 46)."""

from __future__ import annotations

from decimal import Decimal

import pytest

from crypto_trading_lab.market_data.regimes import (
    RegimeLabels,
    RegimePerformance,
    check_regime_concentration,
    compute_regime_performance,
    detect_trending_ranging,
    detect_volatility_regime,
    REGIME_DETECTION_WARNING,
)


def test_trending_detection_requires_enough_data():
    with pytest.raises(ValueError, match="Need enough candles"):
        detect_trending_ranging([Decimal("100"), Decimal("101")])


def test_trending_detection_returns_labels():
    closes = [Decimal(i) for i in range(1, 51)]
    labels = detect_trending_ranging(closes, lookback=10)

    assert isinstance(labels, RegimeLabels)
    assert len(labels.is_trending) == len(closes) - 10
    assert labels.method == "directionality_ratio"


def test_ranging_detection():
    # Oscillating prices should be detected as ranging
    closes = [Decimal(100 + (i % 5)) for i in range(1, 51)]
    labels = detect_trending_ranging(closes, lookback=10)

    # Oscillating series should have fewer trending periods
    trending_count = sum(labels.is_trending)
    assert trending_count < len(closes) - 10


def test_volatility_detection_requires_enough_data():
    with pytest.raises(ValueError, match="Need enough candles"):
        detect_volatility_regime([Decimal(i) for i in range(1, 10)])


def test_volatility_detection_returns_labels():
    closes = [Decimal(100 + i * 0.1) for i in range(1, 51)]
    labels = detect_volatility_regime(closes, lookback=10)

    assert isinstance(labels, RegimeLabels)
    assert len(labels.is_high_volatility) == len(closes) - 11


def test_high_volatility_detected():
    # Series with sudden volatility spike
    closes = [Decimal(100) for _ in range(30)] + [
        Decimal(100 + i * 5) for i in range(1, 21)
    ]
    labels = detect_volatility_regime(closes, lookback=10)

    # End of series should have high volatility
    assert len(labels.is_high_volatility) > 0


def test_compute_regime_performance_basic():
    returns = [Decimal("0.01"), Decimal("0.02"), Decimal("-0.01")]
    labels = [True, True, False]

    perf = compute_regime_performance(returns, labels, "trending")

    assert perf is not None
    assert perf.regime_name == "trending"
    assert perf.n_periods == 2
    assert perf.total_return == Decimal("0.03")


def test_compute_regime_performance_no_data():
    returns = [Decimal("0.01"), Decimal("0.02")]
    labels = [False, False]  # Never in regime

    perf = compute_regime_performance(returns, labels, "trending")

    assert perf is None


def test_compute_regime_performance_win_rate():
    returns = [Decimal("0.01"), Decimal("-0.01"), Decimal("0.01"), Decimal("0.01")]
    labels = [True, True, True, True]

    perf = compute_regime_performance(returns, labels, "trending")

    assert perf.win_rate == Decimal("0.75")


def test_regime_concentration_warning():
    # Highly concentrated in one regime
    labels = [True] * 95 + [False] * 5
    warning = check_regime_concentration(labels, threshold=Decimal("0.8"))

    assert warning != ""
    assert "concentrated" in warning.lower()


def test_regime_no_concentration_warning():
    # Balanced regimes
    labels = [True] * 50 + [False] * 50
    warning = check_regime_concentration(labels, threshold=Decimal("0.8"))

    assert warning == ""


def test_regime_detection_is_a_model():
    """Verify warning text emphasizes model uncertainty."""
    assert "model" in REGIME_DETECTION_WARNING.lower()
    assert "not ground truth" in REGIME_DETECTION_WARNING.lower()

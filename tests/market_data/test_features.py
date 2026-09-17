"""Tests for feature engineering (ROADMAP.md chapter 47)."""

from __future__ import annotations

from decimal import Decimal

import pytest

from crypto_trading_lab.market_data.features import (
    FeatureMetadata,
    compute_ema,
    compute_momentum,
    compute_returns,
    compute_rsi,
    compute_volatility,
    compute_zscore,
    get_feature_metadata,
    get_feature_function,
    FEATURE_CATALOG,
    FEATURE_LEAKAGE_WARNING,
)


def test_returns_basic():
    closes = [Decimal(100), Decimal(110), Decimal(120), Decimal(115)]
    returns = compute_returns(closes)

    assert len(returns) == len(closes)
    # First value is padding (0)
    assert returns[0] == Decimal(0)
    # Second value should be (110-100)/100 = 0.1
    assert returns[1] == Decimal("0.1")


def test_returns_period():
    closes = [Decimal(100), Decimal(110), Decimal(120), Decimal(130)]
    returns = compute_returns(closes, period=2)

    # First 2 values are padding
    assert returns[0] == Decimal(0)
    assert returns[1] == Decimal(0)
    # Third value: (120-100)/100 = 0.2
    assert returns[2] == Decimal("0.2")


def test_returns_insufficient_data():
    closes = [Decimal(100), Decimal(110)]
    returns = compute_returns(closes, period=5)

    assert returns == []


def test_returns_no_divide_by_zero():
    closes = [Decimal(0), Decimal(100), Decimal(110)]
    returns = compute_returns(closes)

    assert returns[1] == Decimal(0)  # Safe handling


def test_volatility_basic():
    # Constant prices = 0 volatility
    closes = [Decimal(100)] * 30
    vol = compute_volatility(closes)

    assert len(vol) == len(closes)
    assert vol[-1] == Decimal(0)


def test_volatility_increasing():
    # Increasing prices = increasing volatility
    closes = [Decimal(100 + i * 2) for i in range(30)]
    vol = compute_volatility(closes, window=10)

    assert len(vol) == len(closes)
    assert vol[-1] > Decimal(0)


def test_volatility_insufficient_data():
    closes = [Decimal(100)] * 5
    vol = compute_volatility(closes, window=10)

    assert vol == []


def test_momentum_basic():
    closes = [Decimal(100), Decimal(110), Decimal(120)]
    mom = compute_momentum(closes, lookback=1)

    assert mom[1] == Decimal("0.1")  # (110-100)/100


def test_momentum_insufficient_data():
    closes = [Decimal(100)]
    mom = compute_momentum(closes, lookback=5)

    assert mom == []


def test_rsi_basic():
    # Rising prices = RSI approaching 100
    closes = [Decimal(100 + i) for i in range(30)]
    rsi = compute_rsi(closes)

    assert len(rsi) == len(closes) - 1
    assert rsi[-1] > Decimal(50)  # Rising prices should give RSI > 50


def test_rsi_insufficient_data():
    closes = [Decimal(100 + i) for i in range(5)]
    rsi = compute_rsi(closes)

    assert rsi == []


def test_ema_basic():
    closes = [Decimal(100), Decimal(100), Decimal(100)]
    ema = compute_ema(closes)

    # EMA of constant prices should equal the price
    assert ema[-1] == Decimal(100)


def test_ema_response():
    closes = [Decimal(100), Decimal(110), Decimal(120)]
    ema = compute_ema(closes, period=2)

    # EMA should move up but lag behind price
    assert ema[-1] > Decimal(100)


def test_zscore_basic():
    # Values equal to mean = z-score of 0
    values = [Decimal(100)] * 30
    zscore = compute_zscore(values, window=10)

    assert zscore[-1] == Decimal(0)


def test_zscore_deviations():
    # One extreme value
    values = [Decimal(100)] * 20 + [Decimal(150)]
    zscore = compute_zscore(values, window=10)

    # The extreme value should have high positive z-score
    assert zscore[-1] > Decimal(1)


def test_zscore_insufficient_data():
    values = [Decimal(100)] * 5
    zscore = compute_zscore(values, window=10)

    assert len(zscore) == 5


def test_get_feature_metadata():
    metadata = get_feature_metadata("rsi")
    assert metadata is not None
    assert metadata.name == "rsi"
    assert metadata.warmup_period == 14


def test_get_feature_metadata_not_found():
    metadata = get_feature_metadata("unknown_feature")
    assert metadata is None


def test_get_feature_function():
    func = get_feature_function("returns")
    assert func is not None


def test_get_feature_function_not_found():
    func = get_feature_function("unknown")
    assert func is None


def test_feature_catalog_complete():
    for feat in FEATURE_CATALOG:
        assert isinstance(feat, FeatureMetadata)
        assert feat.name != ""
        assert feat.formula != ""
        assert feat.warmup_period >= 0


def test_feature_leakage_warning():
    assert "look-ahead bias" in FEATURE_LEAKAGE_WARNING.lower()
    assert "data leakage" in FEATURE_LEAKAGE_WARNING.lower()


def test_no_lookahead_in_returns():
    """Verify returns only use data up to that point."""
    closes = [Decimal(100), Decimal(110), Decimal(120)]
    returns = compute_returns(closes)

    # Returns[2] should only use closes[2] and closes[1]
    assert returns[2] == (Decimal(120) - Decimal(110)) / Decimal(110)


def test_all_features_computable_on_point():
    """All features should be computable without future data."""
    closes = [Decimal(100 + i) for i in range(30)]

    features = [
        compute_returns(closes),
        compute_volatility(closes),
        compute_momentum(closes),
        compute_rsi(closes),
        compute_ema(closes),
        compute_zscore(closes),
    ]

    for feat in features:
        if feat:  # Skip empty results
            assert isinstance(feat, list)

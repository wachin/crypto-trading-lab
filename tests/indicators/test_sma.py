"""Tests for the SMA indicator (ROADMAP.md chapter 31).

Includes a hand-verifiable dataset as the chapter requires: "tests
using small datasets with manually verifiable results".
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from crypto_trading_lab.indicators.library import (
    IndicatorError,
    SMA,
)
from crypto_trading_lab.domain.models import Candle, Symbol


def _candles(closes):
    base = datetime(2024, 1, 1, tzinfo=timezone.utc)
    return [
        Candle(
            symbol=Symbol("BTC/USDT"),
            interval="1m",
            open_time=base + timedelta(minutes=i),
            close_time=base + timedelta(minutes=i + 1),
            open=Decimal(str(c)),
            high=Decimal(str(c + 1)),
            low=Decimal(str(c - 1)),
            close=Decimal(str(c)),
            volume=Decimal("10"),
        )
        for i, c in enumerate(closes)
    ]


def test_sma_hand_verified():
    # closes: 1, 2, 3, 4, 5 → SMA(3) = [None, None, 2, 3, 4]
    closes = [1, 2, 3, 4, 5]
    result = SMA(period=3).compute(_candles(closes))
    assert result.values == (
        None,
        None,
        Decimal("2"),
        Decimal("3"),
        Decimal("4"),
    )


def test_sma_warmup_length_matches_period():
    sma = SMA(period=5)
    assert sma.warmup() == 4
    result = sma.compute(_candles([1, 2, 3, 4, 5]))
    assert result.warmup_length == 4


def test_sma_period_one_equals_close():
    result = SMA(period=1).compute(_candles([10, 20, 30]))
    assert result.values == (
        Decimal("10"),
        Decimal("20"),
        Decimal("30"),
    )


def test_sma_shorter_than_period_all_none():
    result = SMA(period=10).compute(_candles([1, 2, 3]))
    assert all(value is None for value in result.values)


def test_sma_rejects_invalid_period():
    with pytest.raises(IndicatorError):
        SMA(period=0)
    with pytest.raises(IndicatorError):
        SMA(period=-3)


def test_sma_rejects_unordered_candles():
    candles = _candles([1, 2, 3])
    unordered = [candles[2], candles[0], candles[1]]
    with pytest.raises(IndicatorError):
        SMA(period=2).compute(unordered)


def test_sma_no_lookahead_each_value_uses_only_past():
    # If value i changed when a FUTURE candle is appended, there is
    # look-ahead bias. Append and compare.
    first = SMA(period=3).compute(_candles([1, 2, 3, 4]))
    second = SMA(period=3).compute(_candles([1, 2, 3, 4, 100]))
    assert first.values == second.values[:4]


def test_sma_formula_documented():
    assert "C1" in SMA(period=3).formula

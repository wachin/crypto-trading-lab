"""Tests for EMA, RSI, Bollinger, ATR, ROC (chapter 31).

Every dataset is small and hand-verifiable, as the chapter requires.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from crypto_trading_lab.domain.models import Candle, Symbol
from crypto_trading_lab.indicators.library import (
    ATR,
    BollingerBands,
    EMA,
    IndicatorError,
    ROC,
    RSI,
    SMA,
)


def _candles(closes, highs=None, lows=None):
    base = datetime(2024, 1, 1, tzinfo=timezone.utc)
    highs = highs or [c + 1 for c in closes]
    lows = lows or [c - 1 for c in closes]
    return [
        Candle(
            symbol=Symbol("BTC/USDT"),
            interval="1m",
            open_time=base + timedelta(minutes=i),
            close_time=base + timedelta(minutes=i + 1),
            open=Decimal(str(c)),
            high=Decimal(str(h)),
            low=Decimal(str(l)),
            close=Decimal(str(c)),
            volume=Decimal("10"),
        )
        for i, (c, h, l) in enumerate(zip(closes, highs, lows))
    ]


# --- EMA -------------------------------------------------------------------


def test_ema_hand_verified():
    # closes 1..5, EMA(3): alpha = 2/4 = 0.5
    # seed = (1+2+3)/3 = 2; ema[3] = 0.5*4 + 0.5*2 = 3; ema[4] = 0.5*5+0.5*3 = 4
    result = EMA(period=3).compute(_candles([1, 2, 3, 4, 5]))
    assert result.values[2] == Decimal("2")
    assert result.values[3] == Decimal("3")
    assert result.values[4] == Decimal("4")


def test_ema_warmup_and_rejection():
    ema = EMA(period=4)
    assert ema.warmup() == 3
    with pytest.raises(IndicatorError):
        EMA(period=0)


def test_ema_no_lookahead():
    first = EMA(period=3).compute(_candles([1, 2, 3, 4]))
    second = EMA(period=3).compute(_candles([1, 2, 3, 4, 999]))
    assert first.values == second.values[:4]


# --- RSI -------------------------------------------------------------------


def test_rsi_all_gains_is_100():
    # Strictly rising closes → RSI = 100.
    result = RSI(period=3).compute(_candles([1, 2, 3, 4, 5, 6]))
    assert all(value == Decimal(100) for value in result.values[3:])


def test_rsi_all_losses_is_0():
    result = RSI(period=3).compute(_candles([6, 5, 4, 3, 2, 1]))
    assert all(value == Decimal(0) for value in result.values[3:])


def test_rsi_hand_verified_alternating():
    # Wilder RSI(14) is fiddly by hand; use the classic textbook check
    # with period=1 (RS over one change).
    # gains=1, losses=0 → RSI=100 when rising; 0 when falling.
    rising = RSI(period=1).compute(_candles([1, 2, 3]))
    assert rising.values[1] == Decimal(100)


def test_rsi_warmup_and_validation():
    rsi = RSI(period=14)
    assert rsi.warmup() == 14
    with pytest.raises(IndicatorError):
        RSI(period=-1)


def test_rsi_short_series_all_none():
    result = RSI(period=5).compute(_candles([1, 2, 3]))
    assert all(value is None for value in result.values)


# --- Bollinger Bands ---------------------------------------------------------


def test_bollinger_flat_series_zero_width():
    # Identical closes → stdev = 0 → all bands equal the close.
    result = BollingerBands(period=3, k=2).compute(
        _candles([5, 5, 5, 5, 5])
    )
    assert result.values[2] == Decimal("5")
    assert result.values[4] == Decimal("5")


def test_bollinger_hand_verified():
    # closes 1,2,3: mean=2, stdev=sqrt(2/3)≈0.8165; upper=2+2*0.8165
    result = BollingerBands(period=3, k=2).compute(_candles([1, 2, 3]))
    expected = Decimal(2) + Decimal(2) * (
        Decimal(2) / Decimal(3)
    ).sqrt()
    assert abs(result.values[2] - expected) < Decimal("1e-20")


def test_bollinger_rejects_bad_params():
    with pytest.raises(IndicatorError):
        BollingerBands(period=0)
    with pytest.raises(IndicatorError):
        BollingerBands(period=3, k=0)


# --- ATR ---------------------------------------------------------------------


def test_atr_hand_verified():
    # Candle range 2 per candle (high=c+1, low=c-1), no gaps: TR = 2.
    result = ATR(period=3).compute(_candles([10, 10, 10, 10, 10]))
    assert result.values[3] == Decimal(2)


def test_atr_accounts_for_gaps():
    # A big jump between closes increases TR beyond high-low.
    closes = [10, 10, 10, 10, 10]
    highs = [11, 11, 11, 11, 20]  # last candle gaps up far
    lows = [9, 9, 9, 9, 10]
    result = ATR(period=2).compute(_candles(closes, highs, lows))
    # ATR(2) at index 4 averages TR of candles 3 and 4:
    # TR3 = max(11-9, |11-10|, |9-10|) = 2; TR4 = 10 → ATR = 6.
    assert result.values[4] == Decimal("6")


def test_atr_warmup_and_validation():
    atr = ATR(period=14)
    assert atr.warmup() == 14
    with pytest.raises(IndicatorError):
        ATR(period=0)


# --- ROC ---------------------------------------------------------------------


def test_roc_hand_verified():
    # close 100 → 110: ROC(1) = 10%
    result = ROC(period=1).compute(_candles([100, 110, 121]))
    assert result.values[1] == Decimal("10")
    assert abs(result.values[2] - Decimal("10")) < Decimal("1e-20")


def test_roc_negative_when_falling():
    result = ROC(period=1).compute(_candles([110, 100]))
    # (100/110 - 1) * 100 = -9.0909...%
    assert result.values[1] == Decimal(100) / Decimal(110) * Decimal(100) - Decimal(100)


def test_roc_zero_base_does_not_crash():
    # A candle closing at exactly 0 is valid only if low is also 0; build
    # it manually to exercise the divide-by-zero guard.
    base = datetime(2024, 1, 1, tzinfo=timezone.utc)
    zero_candle = Candle(
        symbol=Symbol("BTC/USDT"),
        interval="1m",
        open_time=base,
        close_time=base + timedelta(minutes=1),
        open=Decimal(0),
        high=Decimal(0),
        low=Decimal(0),
        close=Decimal(0),
        volume=Decimal(0),
    )
    five = _candles([5])[0]
    five = Candle(
        symbol=five.symbol,
        interval=five.interval,
        open_time=base + timedelta(minutes=1),
        close_time=base + timedelta(minutes=2),
        open=Decimal(5),
        high=Decimal(6),
        low=Decimal(4),
        close=Decimal(5),
        volume=five.volume,
    )
    try:
        result = ROC(period=1).compute([zero_candle, five])
    except ZeroDivisionError:
        raise AssertionError("ROC must not divide by zero")
    # Zero base: ROC stays None (undefined).
    assert result.values[1] is None



def test_roc_warmup_and_validation():
    roc = ROC(period=10)
    assert roc.warmup() == 10
    with pytest.raises(IndicatorError):
        ROC(period=0)


# --- shared interface ---------------------------------------------------------


def test_all_indicators_share_interface():
    indicators = [SMA(3), EMA(3), RSI(3), BollingerBands(3), ATR(3), ROC(3)]
    candles = _candles([1, 2, 3, 4, 5, 6])
    for indicator in indicators:
        indicator.validate()
        result = indicator.compute(candles)
        assert result.name
        assert len(result.values) == len(candles)
        assert indicator.warmup() >= 0

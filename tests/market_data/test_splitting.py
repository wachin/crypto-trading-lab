"""Chronological data-splitting tests (ROADMAP.md chapter 38)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from crypto_trading_lab.domain.models import Candle, Symbol
from crypto_trading_lab.market_data.splitting import (
    PeriodKind,
    split_candles,
)

BASE = datetime(2024, 1, 1, tzinfo=timezone.utc)


def _candles(n=100, shuffled=False):
    candles = [
        Candle(
            Symbol("BTC/USDT"),
            "1m",
            BASE + timedelta(minutes=i),
            BASE + timedelta(minutes=i + 1),
            open=Decimal(100 + i),
            high=Decimal(101 + i),
            low=Decimal(99 + i),
            close=Decimal(100 + i),
            volume=Decimal("10"),
        )
        for i in range(n)
    ]
    if shuffled:
        candles[10], candles[20] = candles[20], candles[10]
    return candles


def test_default_split_is_chronological_and_exact():
    split = split_candles(_candles(100))
    assert len(split.training.candles) == 60
    assert len(split.validation.candles) == 20
    assert len(split.out_of_sample.candles) == 20
    # Exact recorded boundaries (38.1/38.6).
    bounds = split.boundaries()
    assert bounds["training_last_close"] == _candles(100)[59].close_time.isoformat()
    assert bounds["validation_first_open"] == _candles(100)[60].open_time.isoformat()
    assert bounds["out_of_sample_first_open"] == _candles(100)[80].open_time.isoformat()
    # Temporal ordering strictly increasing across periods.
    assert (
        bounds["training_last_close"] <= bounds["validation_first_open"]
        <= bounds["out_of_sample_first_open"]
    )


def test_no_observation_moves_backward():
    candles = _candles(100)
    split = split_candles(candles)
    ids = [id(c) for period in (
        split.training, split.validation, split.out_of_sample
    ) for c in period.candles]
    # Every candle once, in the original order (no future leakage).
    assert ids == [id(c) for c in candles]


def test_warmup_prefix_is_borrowed_not_part_of_the_period():
    split = split_candles(_candles(100), warmup=5)
    # Validation keeps 20 true candles plus a 5-candle warm-up prefix.
    assert len(split.validation.candles) == 25
    assert len(split.validation.warmup) == 5
    assert split.validation.first_open == split.validation.candles[5].open_time.isoformat()
    assert split.boundaries()["validation_warmup_candles"] == "5"
    # The warm-up prefix is the TAIL of training — never from the future.
    assert split.validation.warmup == tuple(split.training.candles[-5:])


def test_shuffled_input_is_rejected():
    with pytest.raises(ValueError, match="chronological"):
        split_candles(_candles(100, shuffled=True))


def test_fraction_guards():
    with pytest.raises(ValueError):
        split_candles(_candles(), Decimal("0.9"), Decimal("0.9"))
    with pytest.raises(ValueError):
        split_candles(_candles(5))  # too few candles


def test_reusing_the_test_period_is_recorded_and_warned():
    split = split_candles(_candles(100))
    assert split.record_evaluation(PeriodKind.VALIDATION) is None
    assert split.record_evaluation(PeriodKind.OUT_OF_SAMPLE) is None
    warning = split.record_evaluation(PeriodKind.OUT_OF_SAMPLE)
    assert warning is not None
    assert "optimization process" in warning
    assert split.evaluation_log.count(PeriodKind.OUT_OF_SAMPLE) == 2

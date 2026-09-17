"""Tests for triple-barrier labeling (ROADMAP.md chapter 49.2)."""

from __future__ import annotations

from decimal import Decimal

import pytest

from crypto_trading_lab.machine_learning.triple_barrier import (
    TripleBarrierConfig,
    TripleBarrierLabel,
    apply_triple_barrier,
    compute_label_statistics,
)


def test_triple_barrier_take_profit():
    """Should detect take-profit barrier hit."""
    candles = [
        {"open": Decimal(100), "high": Decimal(105), "low": Decimal(99), "close": Decimal(100)},
        {"open": Decimal(100), "high": Decimal(110), "low": Decimal(99), "close": Decimal(110)},
        {"open": Decimal(110), "high": Decimal(115), "low": Decimal(109), "close": Decimal(115)},
    ]
    config = TripleBarrierConfig(vertical_barrier=5, take_profit=Decimal("0.05"), stop_loss=Decimal("0.03"))
    labels = apply_triple_barrier(candles, config)
    
    assert len(labels) > 0
    assert labels[0].barrier_hit == 1  # Take-profit hit


def test_triple_barrier_stop_loss():
    """Should detect stop-loss barrier hit."""
    candles = [
        {"open": Decimal(100), "high": Decimal(101), "low": Decimal(97), "close": Decimal(100)},
        {"open": Decimal(100), "high": Decimal(101), "low": Decimal(90), "close": Decimal(90)},
    ]
    config = TripleBarrierConfig(vertical_barrier=5, take_profit=Decimal("0.10"), stop_loss=Decimal("0.05"))
    labels = apply_triple_barrier(candles, config)
    
    assert len(labels) > 0
    assert labels[0].barrier_hit == -1  # Stop-loss hit


def test_triple_barrier_vertical_barrier():
    """Should use vertical barrier when others not hit."""
    candles = [
        {"open": Decimal(100), "high": Decimal(102), "low": Decimal(98), "close": Decimal(100)},
        {"open": Decimal(100), "high": Decimal(102), "low": Decimal(98), "close": Decimal(101)},
        {"open": Decimal(101), "high": Decimal(103), "low": Decimal(99), "close": Decimal(102)},
        {"open": Decimal(102), "high": Decimal(104), "low": Decimal(100), "close": Decimal(101)},
        {"open": Decimal(101), "high": Decimal(103), "low": Decimal(99), "close": Decimal(102)},
        {"open": Decimal(102), "high": Decimal(104), "low": Decimal(100), "close": Decimal(103)},
    ]
    config = TripleBarrierConfig(vertical_barrier=3, take_profit=Decimal("0.10"), stop_loss=Decimal("0.10"))
    labels = apply_triple_barrier(candles, config)
    
    assert len(labels) > 0
    assert labels[0].barrier_hit == 0  # Time barrier hit
    assert labels[0].holding_period == 3


def test_triple_barrier_empty_result():
    """Empty candles should return empty labels."""
    candles = []
    config = TripleBarrierConfig(vertical_barrier=5, take_profit=Decimal("0.05"), stop_loss=Decimal("0.03"))
    labels = apply_triple_barrier(candles, config)
    
    assert labels == []


def test_triple_barrier_zero_price():
    """Should handle zero price safely."""
    candles = [
        {"open": Decimal(0), "high": Decimal(0), "low": Decimal(0), "close": Decimal(0)},
        {"open": Decimal(0), "high": Decimal(0), "low": Decimal(0), "close": Decimal(0)},
    ]
    config = TripleBarrierConfig(vertical_barrier=1, take_profit=Decimal("0.05"), stop_loss=Decimal("0.03"))
    labels = apply_triple_barrier(candles, config)
    
    assert len(labels) > 0
    assert labels[0].label == 0


def test_triple_barrier_statistics():
    """Should compute correct label statistics."""
    labels = [
        TripleBarrierLabel(label=1, return_value=Decimal("0.05"), barrier_hit=1, holding_period=2),
        TripleBarrierLabel(label=-1, return_value=Decimal("-0.05"), barrier_hit=-1, holding_period=3),
        TripleBarrierLabel(label=0, return_value=Decimal("0.01"), barrier_hit=0, holding_period=5),
    ]
    stats = compute_label_statistics(labels)
    
    assert stats["total"] == 3
    assert stats["take_profit"] == 1
    assert stats["stop_loss"] == 1
    assert stats["time_barrier"] == 1


def test_triple_barrier_empty_statistics():
    """Should handle empty labels."""
    stats = compute_label_statistics([])
    
    assert stats["total"] == 0
    assert stats["avg_return"] == Decimal(0)

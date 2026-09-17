"""Tests for ensemble methods (ROADMAP.md chapter 50)."""

from __future__ import annotations

from decimal import Decimal

import pytest

from crypto_trading_lab.ensembles import (
    CombinationMethod,
    EnsembleSignal,
    StrategySignal,
    combine_signals_average,
    combine_signals_majORITY,
    combine_signals_weighted,
)


def test_majORITY_voting_unanimous():
    """Unanimous buy should give buy signal."""
    signals = [
        StrategySignal("s1", "1.0", 1, Decimal("0.8"), {}),
        StrategySignal("s2", "1.0", 1, Decimal("0.7"), {}),
        StrategySignal("s3", "1.0", 1, Decimal("0.6"), {}),
    ]
    result = combine_signals_majORITY(signals)
    
    assert result.signal == 1
    assert result.confidence == Decimal(1)


def test_majORITY_voting_mixed():
    """Mixed signals should be counted correctly."""
    signals = [
        StrategySignal("s1", "1.0", 1, Decimal("0.8"), {}),
        StrategySignal("s2", "1.0", -1, Decimal("0.7"), {}),
        StrategySignal("s3", "1.0", 1, Decimal("0.6"), {}),
    ]
    result = combine_signals_majORITY(signals)
    
    assert result.signal == 1  # 2 buy vs 1 sell


def test_majORITY_voting_warning_for_few_members():
    """Should warn with few members."""
    signals = [
        StrategySignal("s1", "1.0", 1, Decimal("0.8"), {}),
    ]
    result = combine_signals_majORITY(signals)
    
    assert len(result.warnings) > 0


def test_average_combination():
    """Average combination should compute correctly."""
    signals = [
        StrategySignal("s1", "1.0", 1, Decimal("0.8"), {}),
        StrategySignal("s2", "1.0", -1, Decimal("0.7"), {}),
    ]
    result = combine_signals_average(signals)
    
    assert result.signal == 0
    assert result.confidence == Decimal(0)


def test_weighted_combination():
    """Weighted combination should work."""
    signals = [
        StrategySignal("s1", "1.0", 1, Decimal("0.8"), {}),
        StrategySignal("s2", "1.0", -1, Decimal("0.7"), {}),
    ]
    weights = [Decimal("0.8"), Decimal("0.2")]
    result = combine_signals_weighted(signals, weights)
    
    assert result.signal == 1  # 0.8 - 0.2 = 0.6 rounds to 1


def test_weighted_combination_raises_wrong_length():
    """Should raise error if weights length doesn't match."""
    signals = [
        StrategySignal("s1", "1.0", 1, Decimal("0.8"), {}),
        StrategySignal("s2", "1.0", 1, Decimal("0.7"), {}),
    ]
    weights = [Decimal("0.8")]  # Wrong length
    
    with pytest.raises(ValueError, match="Weights length"):
        combine_signals_weighted(signals, weights)


def test_empty_signals():
    """Empty signals should return neutral ensemble."""
    result = combine_signals_average([])
    
    assert result.signal == 0
    assert len(result.warnings) > 0

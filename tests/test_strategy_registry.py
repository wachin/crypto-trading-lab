"""Tests for Strategy Registry (ROADMAP chapter 36)."""

from __future__ import annotations

from pathlib import Path
from crypto_trading_lab.strategy_registry import StrategyRegistry
from crypto_trading_lab.backtesting.engine import MACrossoverStrategy


def test_registry_loads_builtins(tmp_path):
    registry = StrategyRegistry(storage_path=tmp_path)
    strategies = registry.list_strategies()
    assert len(strategies) >= 3
    
    ids = [s.strategy_id for s in strategies]
    assert "ma_crossover" in ids
    assert "buy_and_hold" in ids
    assert "null_strategy" in ids


def test_registry_create_instance(tmp_path):
    registry = StrategyRegistry(storage_path=tmp_path)
    strategy = registry.create_instance("ma_crossover", fast=5, slow=15)
    assert isinstance(strategy, MACrossoverStrategy)
    assert strategy.fast == 5
    assert strategy.slow == 15

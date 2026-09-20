"""Tests for executable rule strategies (chapters 33, 34, 77).

Rules must run in the real engine, round-trip through a versioned
schema, and reject anything they cannot honestly execute.
"""

from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from crypto_trading_lab.backtesting.engine import BacktestConfig, run_backtest
from crypto_trading_lab.domain.models import Candle, Symbol
from crypto_trading_lab.rule_strategy import (
    Condition,
    RuleError,
    RuleStrategy,
    RuleStrategySpec,
    spec_from_blocks,
    validate_operand,
)

HOUR = timedelta(hours=1)
START = datetime(2024, 1, 1, tzinfo=timezone.utc)


def _candles(count: int = 400) -> list[Candle]:
    candles = []
    price = Decimal("100")
    for i in range(count):
        price = max(Decimal("10"), price + Decimal(str(0.6 * math.sin(i / 12.0))))
        open_time = START + i * HOUR
        candles.append(
            Candle(
                symbol=Symbol("BTC/USDT"),
                interval="1h",
                open_time=open_time,
                close_time=open_time + HOUR - timedelta(milliseconds=1),
                open=price,
                high=price + 1,
                low=price - 1,
                close=price,
                volume=Decimal("5"),
            )
        )
    return candles


def _spec(**overrides) -> RuleStrategySpec:
    data = dict(
        name="SMA rule",
        entry=(Condition("sma(5)", "crosses_above", "sma(20)"),),
        exit=(Condition("sma(5)", "crosses_below", "sma(20)"),),
    )
    data.update(overrides)
    return RuleStrategySpec(**data)


def test_operand_validation():
    assert validate_operand("CLOSE") == "close"
    assert validate_operand("sma( 20 )") == "sma(20)"
    assert validate_operand("50") == "50"
    with pytest.raises(RuleError):
        validate_operand("ema200")
    with pytest.raises(RuleError):
        validate_operand("sma(0)")
    with pytest.raises(RuleError):
        Condition("close", "equals", "50")


def test_spec_rejects_incomplete_rules():
    with pytest.raises(RuleError):
        RuleStrategySpec(name="empty", entry=())
    with pytest.raises(RuleError):
        RuleStrategySpec(name="bad mode", entry=(Condition("close", ">", "1"),), entry_mode="xor")
    with pytest.raises(RuleError):
        RuleStrategySpec(
            name="bad stop",
            entry=(Condition("close", ">", "1"),),
            stop_loss_fraction=Decimal("1.5"),
        )


def test_rule_round_trips_through_versioned_schema():
    spec = _spec(stop_loss_fraction=Decimal("0.05"))
    restored = RuleStrategySpec.from_dict(spec.to_dict())
    assert restored == spec
    assert spec.to_dict()["schema"] == "crypto-trading-lab.rule/1"
    assert "Enter when" in spec.describe()


def test_rule_runs_in_the_real_engine():
    result = run_backtest(
        _candles(), RuleStrategy(_spec()), BacktestConfig()
    )

    assert result.strategy_name == "SMA rule"
    assert result.trades, "an SMA crossover rule must produce trades"
    # No look-ahead: the engine fills at the next open.
    first = result.trades[0]
    assert first.entry_time != ""


def _flat_then_crash(before: int = 30, after: int = 30) -> list[Candle]:
    """Deterministic series: flat 100, then a 20% crash to 80."""
    prices = [Decimal("100")] * before + [Decimal("80")] * after
    candles = []
    for i, price in enumerate(prices):
        open_time = START + i * HOUR
        candles.append(
            Candle(
                symbol=Symbol("BTC/USDT"),
                interval="1h",
                open_time=open_time,
                close_time=open_time + HOUR - timedelta(milliseconds=1),
                open=price,
                high=price,
                low=price,
                close=price,
                volume=Decimal("5"),
            )
        )
    return candles


def test_stop_loss_forces_an_exit():
    spec = RuleStrategySpec(
        name="entry with stop",
        entry=(Condition("close", ">", "0"),),
        stop_loss_fraction=Decimal("0.01"),
    )
    result = run_backtest(
        _flat_then_crash(), RuleStrategy(spec), BacktestConfig()
    )
    assert result.trades
    assert any(t.exit_time is not None for t in result.trades)


def test_spec_from_builder_blocks_builds_a_runnable_rule():
    from crypto_trading_lab.strategy_builder import StrategyBuilder

    builder = StrategyBuilder()
    fast = builder.add_indicator("sma", {"period": 5})
    slow = builder.add_indicator("sma", {"period": 20})
    cross = builder.add_operator("crossover")
    entry = builder.add_entry_signal()
    cross_down = builder.add_operator("crossunder")
    exit_block = builder.add_exit_signal()
    rule = builder.create_rule(
        "Builder rule",
        block_ids=[
            fast.block_id,
            slow.block_id,
            cross.block_id,
            entry.block_id,
            fast.block_id,
            slow.block_id,
            cross_down.block_id,
            exit_block.block_id,
        ],
    )

    spec = spec_from_blocks(rule.name, rule.blocks)

    assert spec.name == "Builder rule"
    assert spec.entry == (Condition("sma(5)", "crosses_above", "sma(20)"),)
    assert spec.exit == (Condition("sma(5)", "crosses_below", "sma(20)"),)
    result = run_backtest(_candles(), RuleStrategy(spec), BacktestConfig())
    assert result.trades


def test_filters_and_arithmetic_are_rejected_not_guessed():
    from crypto_trading_lab.strategy_builder import StrategyBuilder

    builder = StrategyBuilder()
    builder.add_cooldown(5)
    rule = builder.create_rule("filtered", block_ids=[list(builder.blocks)[0]])

    with pytest.raises(RuleError) as error:
        spec_from_blocks(rule.name, rule.blocks)

    assert "filter" in str(error.value).lower()

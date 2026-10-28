"""Execution realism inside the backtest engine (ROADMAP.md 56.5).

Chapter 56.5 requires the execution model to feed the backtest, paper
trading and robustness, not only one of them. These tests hold the engine
to that: the model is selectable, recorded, reproducible, and it never
assumes unlimited liquidity.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from crypto_trading_lab.backtesting.engine import (
    BacktestConfig,
    BuyAndHoldStrategy,
    run_backtest,
)
from crypto_trading_lab.domain.models import Candle, OrderSide, Symbol
from crypto_trading_lab.execution_realism import ExecutionConfig

BASE = datetime(2024, 1, 1, tzinfo=timezone.utc)


def _candles(count: int = 5, volume: str = "10") -> list[Candle]:
    """Flat 100.00 candles: every price effect is attributable to execution."""
    return [
        Candle(
            Symbol("BTC/USDT"),
            "1m",
            BASE + timedelta(minutes=index),
            BASE + timedelta(minutes=index + 1),
            open=Decimal("100"),
            high=Decimal("101"),
            low=Decimal("99"),
            close=Decimal("100"),
            volume=Decimal(volume),
        )
        for index in range(count)
    ]


class _BuyThenSell:
    """Buys on the first candle and closes on the third: two orders."""

    name = "buy then sell"
    version = "1.0.0"

    def on_candle(self, index, candles):
        if index == 0:
            return OrderSide.BUY
        if index == 2:
            return OrderSide.SELL
        return None


def test_cost_model_is_the_default_and_says_so():
    """A run that does not ask for realism records the cost model (56.2)."""
    result = run_backtest(_candles(), BuyAndHoldStrategy())
    assert result.config_metadata["execution_realism"] == "cost_model (chapter 37.1)"
    assert result.config_metadata["execution_seed"] == "not applicable"
    assert result.rejected_orders == 0
    assert result.partial_fills == 0


def test_realistic_model_is_recorded_with_its_seed():
    """The selected execution model and seed are part of every run (56.2)."""
    config = BacktestConfig(
        execution_config=ExecutionConfig(), execution_seed=17
    )
    result = run_backtest(_candles(), BuyAndHoldStrategy(), config)
    assert (
        result.config_metadata["execution_realism"]
        == "chapter_56_execution_realism"
    )
    assert result.config_metadata["execution_seed"] == "17"


def test_realistic_fills_are_adverse_to_the_trader():
    """Chapter 56 prices come from the book, never better than the reference."""
    config = BacktestConfig(
        execution_config=ExecutionConfig(), execution_seed=5
    )
    result = run_backtest(_candles(), _BuyThenSell(), config)
    trade = result.trades[0]
    assert trade.entry_price > Decimal("100")
    assert trade.exit_price < Decimal("100")
    assert trade.slippage_cost > 0
    # The chapter 56 price already contains the half-spread; charging the
    # spread again would double count it (56.5).
    assert trade.spread_cost == 0


def test_same_seed_reproduces_the_same_fills():
    """Determinism (37.8): the seed, not the clock, drives the model."""
    config = BacktestConfig(
        execution_config=ExecutionConfig(), execution_seed=11
    )
    first = run_backtest(_candles(), _BuyThenSell(), config)
    second = run_backtest(_candles(), _BuyThenSell(), config)
    assert first.trades == second.trades
    assert first.final_equity == second.final_equity


def test_unknown_depth_rejects_instead_of_assuming_liquidity():
    """No volume history means no depth: the order is rejected (56.4)."""
    config = BacktestConfig(
        execution_config=ExecutionConfig(), execution_seed=3
    )
    result = run_backtest(_candles(volume="0"), _BuyThenSell(), config)
    assert result.order_count == 0
    assert result.rejected_orders >= 1
    assert result.trades == []
    assert result.final_equity == result.initial_capital


def test_partial_fill_sells_only_what_the_book_absorbs():
    """Depth decides the size, so a large order fills in part (56.1, 56.4)."""
    config = BacktestConfig(
        execution_config=ExecutionConfig(
            max_order_size_frac=Decimal("0.00347")
        ),
        execution_seed=3,
    )
    result = run_backtest(_candles(), _BuyThenSell(), config)
    assert result.partial_fills == 1
    assert result.order_count == 2
    assert result.trades[0].quantity < Decimal("100")


def test_cost_model_results_are_unchanged_by_the_new_fields():
    """Selecting nothing must keep the chapter 37.1 arithmetic identical."""
    config = BacktestConfig()
    result = run_backtest(_candles(), _BuyThenSell(), config)
    trade = result.trades[0]
    # The default cost model worsens the reference open by its half-spread
    # plus slippage fraction: 100.00 * (1 + 0.0002 + 0.0005).
    expected_entry = Decimal("100") * (
        Decimal(1) + Decimal("0.0002") + Decimal("0.0005")
    )
    assert trade.entry_price == expected_entry
    assert trade.spread_cost > 0

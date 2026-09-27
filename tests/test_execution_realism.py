"""Tests for the chapter-56 execution model and its wiring into paper
trading (ROADMAP.md chapters 56 and 57).

Offline and deterministic: every random draw comes from a seeded
``random.Random`` passed explicitly.
"""

from __future__ import annotations

import math
import random
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from crypto_trading_lab.backtesting.engine import MACrossoverStrategy
from crypto_trading_lab.domain.models import Candle, Symbol
from crypto_trading_lab.execution_realism import (
    ExecutionConfig,
    FillType,
    OrderBookSnapshot,
    OrderBookLevel,
    OrderType,
    calculate_slippage,
    simulate_execution,
    simulate_market_order,
    synthetic_order_book,
)
from crypto_trading_lab.paper_session import PaperSessionConfig, run_paper_session

HOUR = timedelta(hours=1)
START = datetime(2024, 1, 1, tzinfo=timezone.utc)
REFERENCE = Decimal("100")


# -- the synthetic book ------------------------------------------------------


def test_synthetic_book_is_symmetric_around_the_reference():
    book = synthetic_order_book(
        REFERENCE,
        spread_fraction=Decimal("0.0002"),
        depth_quantity=Decimal("240"),
    )

    assert book.mid_price() == REFERENCE
    assert book.spread() == REFERENCE * Decimal("0.0002")
    assert sum(level.quantity for level in book.asks) == Decimal("240")
    assert sum(level.quantity for level in book.bids) == Decimal("240")
    # Asks above the mid, bids below it.
    assert all(level.price > REFERENCE for level in book.asks)
    assert all(level.price < REFERENCE for level in book.bids)


def test_synthetic_book_rejects_a_non_positive_number_of_levels():
    with pytest.raises(ValueError):
        synthetic_order_book(
            REFERENCE,
            spread_fraction=Decimal("0.0002"),
            depth_quantity=Decimal("10"),
            levels=0,
        )


# -- market orders -----------------------------------------------------------


def test_market_order_fills_fully_when_the_book_is_deep():
    result = simulate_market_order(
        REFERENCE,
        "buy",
        Decimal("0.1"),
        ExecutionConfig(),
        adv=Decimal("240"),
        rng=random.Random(42),
    )

    assert result.fill_type is FillType.FULL
    assert result.filled_quantity == Decimal("0.1")


def test_slippage_is_always_adverse():
    """A buy never fills below mid and a sell never above it.

    Regression: a lucky random draw used to produce a negative slippage and
    a price *better* than mid.
    """
    config = ExecutionConfig()
    for seed in range(12):
        buy = simulate_market_order(
            REFERENCE, "buy", Decimal("0.5"), config,
            adv=Decimal("240"), rng=random.Random(seed),
        )
        sell = simulate_market_order(
            REFERENCE, "sell", Decimal("0.5"), config,
            adv=Decimal("240"), rng=random.Random(seed),
        )
        assert buy.average_price >= REFERENCE, seed
        assert sell.average_price <= REFERENCE, seed
        assert buy.slippage_bps >= 0
        assert sell.slippage_bps >= 0


def test_market_impact_is_reported_separately_from_slippage():
    result = simulate_market_order(
        REFERENCE,
        "buy",
        Decimal("20"),
        ExecutionConfig(),
        adv=Decimal("240"),
        rng=random.Random(1),
    )

    assert result.market_impact_bps > 0
    # The reported slippage includes the impact but is not just the impact.
    assert result.slippage_bps >= result.market_impact_bps


def test_price_comes_from_the_slippage_model_not_the_book_ladder():
    """Regression for a dead computation in ``simulate_execution``.

    It used to compute ``exec_price``/``slippage`` and then throw them away,
    returning the raw book-level average instead. With impact and the random
    component disabled, the price must be mid adjusted by half the spread.
    """
    config = ExecutionConfig(base_slippage_bps=0, impact_factor=Decimal("0"))
    book = synthetic_order_book(
        REFERENCE,
        spread_fraction=Decimal("0.0002"),
        depth_quantity=Decimal("240"),
    )
    # 60 units walk two ladder levels, so the book average is *not* the price
    # the slippage model returns.
    quantity = Decimal("60")
    expected_price, expected_bps = calculate_slippage(
        quantity, "buy", book, config, Decimal("240")
    )

    result = simulate_execution(
        quantity, "buy", OrderType.MARKET, None, book, config,
        Decimal("240"), fees_bps=Decimal(0),
    )

    assert result.average_price == expected_price
    assert result.slippage_bps == expected_bps
    assert result.slippage_bps == Decimal("1")  # spread_fraction / 2 in bps
    ladder_quantity = sum(q for q, _ in result.partial_fills)
    ladder_value = sum(q * p for q, p in result.partial_fills)
    assert ladder_quantity == quantity
    assert result.average_price < ladder_value / ladder_quantity


def test_a_large_order_is_not_filled_at_the_touch():
    result = simulate_market_order(
        REFERENCE,
        "buy",
        Decimal("1000"),  # four times the modelled depth
        ExecutionConfig(),
        adv=Decimal("240"),
        rng=random.Random(42),
    )

    assert result.fill_type in (FillType.PARTIAL, FillType.REJECTED)
    assert result.filled_quantity < Decimal("1000")


def test_an_empty_book_rejects_the_order():
    empty = OrderBookSnapshot(timestamp=0, bids=(), asks=())
    result = simulate_execution(
        Decimal("1"), "buy", OrderType.MARKET, None, empty,
        ExecutionConfig(), Decimal("240"),
    )

    assert result.fill_type is FillType.REJECTED
    assert result.filled_quantity == 0


def test_market_order_rejects_an_unknown_side():
    with pytest.raises(ValueError):
        simulate_market_order(
            REFERENCE, "sideways", Decimal("1"), ExecutionConfig(),
            adv=Decimal("240"),
        )


# -- determinism -------------------------------------------------------------


def test_simulate_execution_is_reproducible_with_a_seed():
    config = ExecutionConfig()

    def run(seed: int):
        return simulate_market_order(
            REFERENCE, "buy", Decimal("1"), config,
            adv=Decimal("240"), rng=random.Random(seed),
        )

    first, second = run(7), run(7)
    assert first.average_price == second.average_price
    assert first.latency_ms == second.latency_ms
    assert first.slippage_bps == second.slippage_bps
    assert first.filled_quantity == second.filled_quantity


# -- wiring into paper trading ------------------------------------------

MINUTE = timedelta(minutes=1)


def _candles(count: int = 400, volume: str = "10") -> list[Candle]:
    candles = []
    price = Decimal("100")
    for index in range(count):
        price = max(Decimal("10"), price + Decimal(str(0.5 * math.sin(index / 12.0))))
        open_time = START + index * HOUR
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
                volume=Decimal(volume),
            )
        )
    return candles


def _run(config: PaperSessionConfig):
    return run_paper_session(
        _candles(), MACrossoverStrategy(fast=5, slow=20), config=config
    )


def test_without_execution_config_the_basic_model_is_unchanged():
    config = PaperSessionConfig(interval="1h")
    result = _run(config)

    filled = result.journal.filled_entries[0]
    adjustment = config.slippage_fraction + config.spread_fraction
    assert filled.fill_price == filled.reference_price * (Decimal(1) + adjustment)
    # The basic model never leaves an approved entry unfilled.
    assert all(
        entry.fill_price is not None
        for entry in result.journal.entries
        if entry.risk_decision == "approve"
    )


def test_execution_config_is_actually_used():
    """With a realistic model the fills stop matching the basic model.

    Regression: ``simulate_execution`` was imported and never called, so an
    ``execution_config`` had no effect beyond one ``impact_factor`` term.
    """
    basic = _run(PaperSessionConfig(interval="1h"))
    realistic = _run(
        PaperSessionConfig(
            interval="1h",
            execution_config=ExecutionConfig(),
            seed=42,
        )
    )

    assert realistic.journal.filled_entries, "the realistic model must fill"
    assert [
        entry.fill_price for entry in realistic.journal.filled_entries
    ] != [entry.fill_price for entry in basic.journal.filled_entries]
    # A different execution path, not a different risk outcome.
    assert realistic.final_equity != basic.final_equity


def test_execution_model_can_leave_an_approved_entry_unfilled():
    """Scarce liquidity must be visible, not assumed away (56.4)."""
    config = PaperSessionConfig(
        interval="1h",
        execution_config=ExecutionConfig(max_order_size_frac=Decimal("0.000001")),
        seed=42,
    )
    result = _run(config)

    approved = [e for e in result.journal.entries if e.risk_decision == "approve"]
    assert approved, "the strategy should still produce approved orders"
    assert any(entry.fill_price is None for entry in approved), (
        "an order far larger than the modelled depth must not fill"
    )


def test_paper_session_with_execution_config_is_deterministic():
    """The same seed must reproduce the same fills.

    Regression: the old path drew partial fills from the unseeded global RNG.
    """
    config = PaperSessionConfig(
        interval="1h",
        execution_config=ExecutionConfig(),
        seed=20260927,
    )

    first = _run(config)
    second = _run(config)

    assert first.final_equity == second.final_equity
    assert [e.to_dict() for e in first.journal.entries] == [
        e.to_dict() for e in second.journal.entries
    ]


def test_paper_session_documents_its_seed():
    config = PaperSessionConfig(interval="1h", seed=7)
    assert config.to_dict()["seed"] == 7

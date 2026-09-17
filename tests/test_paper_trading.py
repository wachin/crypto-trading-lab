"""Tests for paper trading (ROADMAP.md chapter 57)."""

from __future__ import annotations

from decimal import Decimal

import pytest

from crypto_trading_lab.paper_trading import (
    OrderSide,
    OrderStatus,
    PaperAccount,
    PaperExecutionSimulator,
    PaperOrder,
    PaperTradingEngine,
)


def test_paper_account_initial_balance():
    """Account should start with initial balance."""
    account = PaperAccount(initial_balance=Decimal(10000))
    
    assert account.get_balance("USDT") == Decimal(10000)
    assert account.get_position("BTC") == Decimal(0)


def test_paper_account_update_balance():
    """Should update balance correctly."""
    account = PaperAccount(initial_balance=Decimal(10000))
    account.update_balance("USDT", Decimal(-500))
    
    assert account.get_balance("USDT") == Decimal(9500)


def test_paper_account_update_position():
    """Should update position correctly."""
    account = PaperAccount(initial_balance=Decimal(10000))
    account.update_position("BTC", Decimal(0.1))
    
    assert abs(account.get_position("BTC") - Decimal(0.1)) < Decimal("0.001")


def test_paper_account_history():
    """Should track account history."""
    account = PaperAccount(initial_balance=Decimal(10000))
    account.update_balance("USDT", Decimal(-500))
    
    assert len(account.history) > 0
    assert account.history[-1]["type"] == "balance_change"


def test_execution_simulator_market_order():
    """Should simulate market orders with slippage."""
    execution = PaperExecutionSimulator()
    
    order = PaperOrder(
        order_id="1",
        symbol="BTC/USDT",
        side=OrderSide.BUY,
        quantity=Decimal(0.1),
        price=None,
    )
    
    result = execution.simulate_order(order, Decimal(10000))
    
    assert result.status == OrderStatus.FILLED
    assert result.fill_price is not None


def test_execution_simulator_limit_order():
    """Should respect limit orders."""
    execution = PaperExecutionSimulator()
    
    # Buy limit at 9900, current price 10000 - should reject
    order = PaperOrder(
        order_id="1",
        symbol="BTC/USDT",
        side=OrderSide.BUY,
        quantity=Decimal(0.1),
        price=Decimal(9900),
    )
    
    result = execution.simulate_order(order, Decimal(10000))
    
    assert result.status == OrderStatus.REJECTED


def test_paper_trading_engine_buy():
    """Should execute buy order correctly."""
    account = PaperAccount(initial_balance=Decimal(10000))
    engine = PaperTradingEngine(account)
    
    order = PaperOrder(
        order_id="1",
        symbol="BTC/USDT",
        side=OrderSide.BUY,
        quantity=Decimal(0.1),
        price=None,
    )
    
    result, fee = engine.execute_order(order, Decimal(10000))
    
    assert result.status == OrderStatus.FILLED
    assert abs(account.get_position("BTC") - Decimal(0.1)) < Decimal("0.001")
    assert account.get_balance("USDT") < Decimal(10000)


def test_paper_trading_engine_sell():
    """Should execute sell order correctly."""
    account = PaperAccount(initial_balance=Decimal(10000))
    account.update_position("BTC", Decimal(0.1))
    engine = PaperTradingEngine(account)
    
    order = PaperOrder(
        order_id="1",
        symbol="BTC/USDT",
        side=OrderSide.SELL,
        quantity=Decimal(0.1),
        price=None,
    )
    
    result, fee = engine.execute_order(order, Decimal(10000))
    
    assert result.status == OrderStatus.FILLED
    assert account.get_position("BTC") == Decimal(0)


def test_paper_trading_tracks_fees():
    """Should track fees."""
    account = PaperAccount(initial_balance=Decimal(10000))
    engine = PaperTradingEngine(account)
    
    order = PaperOrder(
        order_id="1",
        symbol="BTC/USDT",
        side=OrderSide.BUY,
        quantity=Decimal(0.1),
        price=None,
    )
    
    engine.execute_order(order, Decimal(10000))
    
    assert account.total_fees > 0

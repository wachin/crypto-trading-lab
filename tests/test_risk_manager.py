"""Tests for risk manager (ROADMAP.md chapter 58)."""

from __future__ import annotations

from decimal import Decimal

import pytest

from crypto_trading_lab.risk_manager import (
    LossLimits,
    OperationalLimits,
    OrderRequest,
    PortfolioState,
    RiskDecision,
    RiskLimits,
    RiskManager,
)


def test_risk_manager_approves_valid_order():
    """Should approve orders that pass all limits."""
    limits = RiskLimits(
        max_risk_per_trade=Decimal("0.02"),
        max_position_size=Decimal("0.10"),
        max_total_exposure=Decimal("0.50"),
        max_long_exposure=Decimal("0.30"),
        max_short_exposure=Decimal("0.30"),
    )
    rm = RiskManager(limits)
    
    portfolio = PortfolioState(
        total_value=Decimal(10000),
        long_exposure=Decimal(0),
        short_exposure=Decimal(0),
        daily_pnl=Decimal(0),
        weekly_pnl=Decimal(0),
        current_drawdown=Decimal(0),
        consecutive_losses=0,
    )
    
    order = OrderRequest(
        strategy_name="test",
        symbol="BTC/USDT",
        side="buy",
        quantity=Decimal(0.1),
        price=Decimal(100),
        timestamp="2024-01-01T00:00:00Z",
    )
    
    result = rm.evaluate(order, portfolio)
    
    assert result.decision == RiskDecision.APPROVE


def test_risk_manager_rejects_large_position():
    """Should reject orders exceeding position limits."""
    limits = RiskLimits(
        max_risk_per_trade=Decimal("0.02"),
        max_position_size=Decimal("0.10"),
        max_total_exposure=Decimal("0.50"),
        max_long_exposure=Decimal("0.30"),
        max_short_exposure=Decimal("0.30"),
    )
    rm = RiskManager(limits)
    
    portfolio = PortfolioState(
        total_value=Decimal(10000),
        long_exposure=Decimal(0),
        short_exposure=Decimal(0),
        daily_pnl=Decimal(0),
        weekly_pnl=Decimal(0),
        current_drawdown=Decimal(0),
        consecutive_losses=0,
    )
    
    order = OrderRequest(
        strategy_name="test",
        symbol="BTC/USDT",
        side="buy",
        quantity=Decimal(100),  # Very large
        price=Decimal(100),
        timestamp="2024-01-01T00:00:00Z",
    )
    
    result = rm.evaluate(order, portfolio)
    
    assert result.decision == RiskDecision.REJECT


def test_risk_manager_rejects_loss_limit():
    """Should reject when daily loss exceeded."""
    limits = RiskLimits(
        max_risk_per_trade=Decimal("0.02"),
        max_position_size=Decimal("0.10"),
        max_total_exposure=Decimal("0.50"),
        max_long_exposure=Decimal("0.30"),
        max_short_exposure=Decimal("0.30"),
    )
    rm = RiskManager(limits)
    
    portfolio = PortfolioState(
        total_value=Decimal(10000),
        long_exposure=Decimal(0),
        short_exposure=Decimal(0),
        daily_pnl=Decimal(-300),  # 3% loss
        weekly_pnl=Decimal(0),
        current_drawdown=Decimal(0),
        consecutive_losses=0,
    )
    
    order = OrderRequest(
        strategy_name="test",
        symbol="BTC/USDT",
        side="buy",
        quantity=Decimal(0.1),
        price=Decimal(100),
        timestamp="2024-01-01T00:00:00Z",
    )
    
    result = rm.evaluate(order, portfolio)
    
    assert result.decision == RiskDecision.REJECT


def test_risk_manager_rejects_consecutive_losses():
    """Should reject when consecutive losses limit reached."""
    limits = RiskLimits(
        max_risk_per_trade=Decimal("0.02"),
        max_position_size=Decimal("0.10"),
        max_total_exposure=Decimal("0.50"),
        max_long_exposure=Decimal("0.30"),
        max_short_exposure=Decimal("0.30"),
    )
    rm = RiskManager(limits)
    
    portfolio = PortfolioState(
        total_value=Decimal(10000),
        long_exposure=Decimal(0),
        short_exposure=Decimal(0),
        daily_pnl=Decimal(0),
        weekly_pnl=Decimal(0),
        current_drawdown=Decimal(0),
        consecutive_losses=5,  # At limit
    )
    
    order = OrderRequest(
        strategy_name="test",
        symbol="BTC/USDT",
        side="buy",
        quantity=Decimal(0.1),
        price=Decimal(100),
        timestamp="2024-01-01T00:00:00Z",
    )
    
    result = rm.evaluate(order, portfolio)
    
    assert result.decision == RiskDecision.REJECT


def test_risk_manager_rejects_max_trades():
    """Should reject when max trades per day reached."""
    limits = RiskLimits(
        max_risk_per_trade=Decimal("0.02"),
        max_position_size=Decimal("0.10"),
        max_total_exposure=Decimal("0.50"),
        max_long_exposure=Decimal("0.30"),
        max_short_exposure=Decimal("0.30"),
    )
    rm = RiskManager(limits)
    rm._trades_today = 100  # Exceeds limit
    
    portfolio = PortfolioState(
        total_value=Decimal(10000),
        long_exposure=Decimal(0),
        short_exposure=Decimal(0),
        daily_pnl=Decimal(0),
        weekly_pnl=Decimal(0),
        current_drawdown=Decimal(0),
        consecutive_losses=0,
    )
    
    order = OrderRequest(
        strategy_name="test",
        symbol="BTC/USDT",
        side="buy",
        quantity=Decimal(0.1),
        price=Decimal(100),
        timestamp="2024-01-01T00:00:00Z",
    )
    
    result = rm.evaluate(order, portfolio)
    
    assert result.decision == RiskDecision.REJECT


# -- exits must never be blocked by the position limits ---------------------


def _manager() -> RiskManager:
    return RiskManager(
        RiskLimits(
            max_risk_per_trade=Decimal("0.02"),
            max_position_size=Decimal("0.60"),
            max_total_exposure=Decimal("0.90"),
            max_long_exposure=Decimal("0.90"),
            max_short_exposure=Decimal("0"),
        )
    )


def _portfolio(long_exposure: str, total: str = "10000") -> PortfolioState:
    return PortfolioState(
        total_value=Decimal(total),
        long_exposure=Decimal(long_exposure),
        short_exposure=Decimal(0),
        daily_pnl=Decimal(0),
        weekly_pnl=Decimal(0),
        current_drawdown=Decimal(0),
        consecutive_losses=0,
    )


def test_a_sell_that_closes_a_long_is_approved():
    """Regression: the manager added the sell notional to the exposure, so
    the order that reduces risk was the one it rejected."""
    order = OrderRequest(
        strategy_name="test",
        symbol="BTC/USDT",
        side="sell",
        quantity=Decimal("50"),
        price=Decimal("102"),
        timestamp="2024-01-01T00:00:00Z",
    )

    result = _manager().evaluate(order, _portfolio("5100"))

    assert result.decision == RiskDecision.APPROVE


def test_a_sell_cannot_open_an_unlimited_short():
    """Closing the long is free; the excess is a new short and is limited."""
    manager = RiskManager(
        RiskLimits(
            max_risk_per_trade=Decimal("0.02"),
            max_position_size=Decimal("0.95"),
            max_total_exposure=Decimal("0.95"),
            max_long_exposure=Decimal("0.95"),
            max_short_exposure=Decimal("0.30"),
        )
    )
    order = OrderRequest(
        strategy_name="test",
        symbol="BTC/USDT",
        side="sell",
        quantity=Decimal("120"),
        price=Decimal("100"),
        timestamp="2024-01-01T00:00:00Z",
    )

    # 5000 long + 7000 new short: the short is what breaks the limit.
    result = manager.evaluate(order, _portfolio("5000"))

    assert result.decision == RiskDecision.REJECT
    assert "short" in result.reason


def test_a_partial_exit_is_approved():
    """Selling half of a long is still a reduction, not a new position."""
    order = OrderRequest(
        strategy_name="test",
        symbol="BTC/USDT",
        side="sell",
        quantity=Decimal("25"),
        price=Decimal("100"),
        timestamp="2024-01-01T00:00:00Z",
    )

    result = _manager().evaluate(order, _portfolio("5000"))

    assert result.decision == RiskDecision.APPROVE


def test_a_buy_that_exceeds_the_total_exposure_is_still_rejected():
    """The fix must not weaken the limit it was fixing."""
    manager = RiskManager(
        RiskLimits(
            max_risk_per_trade=Decimal("0.02"),
            max_position_size=Decimal("0.95"),
            max_total_exposure=Decimal("0.90"),
            max_long_exposure=Decimal("0.95"),
            max_short_exposure=Decimal("0.30"),
        )
    )
    order = OrderRequest(
        strategy_name="test",
        symbol="BTC/USDT",
        side="buy",
        quantity=Decimal("41"),
        price=Decimal("100"),
        timestamp="2024-01-01T00:00:00Z",
    )

    # 5000 held + 4100 more = 9100, above the 9000 total-exposure ceiling.
    result = manager.evaluate(order, _portfolio("5000"))

    assert result.decision == RiskDecision.REJECT
    assert "total exposure" in result.reason

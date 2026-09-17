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

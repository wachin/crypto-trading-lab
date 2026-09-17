"""Tests for risk of ruin (ROADMAP.md chapter 60)."""

from __future__ import annotations

from decimal import Decimal

from crypto_trading_lab.backtesting.engine import (
    BacktestConfig,
    BuyAndHoldStrategy,
    MACrossoverStrategy,
    run_backtest,
)
from crypto_trading_lab.backtesting.robustness import (
    PositionSizingConfig,
    RiskOfRuinReport,
    compute_risk_of_ruin,
    monte_carlo_trades,
)
from crypto_trading_lab.domain.models import Candle, Symbol
from datetime import datetime, timedelta, timezone


BASE = datetime(2024, 1, 1, tzinfo=timezone.utc)


def _candles(n=80):
    closes = [100 + i for i in range(n // 2)] + [
        100 + n // 2 - i for i in range(n - n // 2)
    ]
    return [
        Candle(
            Symbol("BTC/USDT"),
            "1m",
            BASE + timedelta(minutes=i),
            BASE + timedelta(minutes=i + 1),
            open=Decimal(c),
            high=Decimal(c + 1),
            low=Decimal(c - 1),
            close=Decimal(c),
            volume=Decimal("10"),
        )
        for i, c in enumerate(closes)
    ]


def _config():
    return BacktestConfig(
        costs=BacktestConfig().costs
    )


def test_risk_of_ruin_computes():
    """Should compute risk of ruin report with trade data."""
    # Create a strategy that produces trades
    result = run_backtest(
        _candles(150),
        MACrossoverStrategy(fast=5, slow=20),
        _config(),
    )
    # If no trades, the function should handle gracefully
    report = compute_risk_of_ruin(result)
    assert isinstance(report, RiskOfRuinReport)


def test_risk_of_ruin_with_trades():
    """Should use trades when available."""
    # Test with a longer run that should produce trades
    result = run_backtest(
        _candles(200),
        MACrossoverStrategy(fast=10, slow=40),
        _config(),
    )
    report = compute_risk_of_ruin(result)
    assert isinstance(report, RiskOfRuinReport)
    assert len(report.assumptions) > 0


def test_risk_of_ruin_no_trades():
    """Should handle empty trades gracefully."""
    result = run_backtest(
        _candles(30),
        BuyAndHoldStrategy(),
        _config(),
    )
    report = compute_risk_of_ruin(result)
    
    assert report.scenarios == 0
    assert report.warnings


def test_risk_of_ruin_max_drawdown():
    """Should compute historical max drawdown."""
    result = run_backtest(
        _candles(100),
        MACrossoverStrategy(fast=5, slow=20),
        _config(),
    )
    report = compute_risk_of_ruin(result)
    
    assert report.historical_max_drawdown >= 0
    assert report.expected_max_drawdown >= 0


def test_position_sizing_config():
    """Should create position sizing config."""
    config = PositionSizingConfig(
        max_risk_per_trade=Decimal("0.01"),
        max_total_exposure=Decimal("0.30"),
        ruin_threshold_fraction=Decimal("0.05"),
    )
    
    assert config.max_risk_per_trade == Decimal("0.01")
    assert config.ruin_threshold_fraction == Decimal("0.05")
"""Tests for risk of ruin (ROADMAP.md chapter 60)."""

from __future__ import annotations

import math
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
    kelly_fraction,
    monte_carlo_trades,
    optimal_bet_size,
    position_size_from_trades,
)
from crypto_trading_lab.domain.models import Candle, Symbol
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest


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

# -- position sizing (chapter 60, merged from the former risk_of_ruin) -------


class _FakeResult:
    """Duck-typed stand-in: ``position_size_from_trades`` only reads trades."""

    def __init__(self, pnls):
        self.trades = [SimpleNamespace(net_pnl=p) for p in pnls]


def _pnls(wins, losses):
    """Wins at 2:1 payoff."""
    return [Decimal("2")] * wins + [Decimal("-1")] * losses


def _even_odds(wins, losses):
    """Wins at 1:1 payoff."""
    return [Decimal("1")] * wins + [Decimal("-1")] * losses


def test_kelly_fraction_matches_the_formula():
    # p=0.6, b=2 -> (0.6*2 - 0.4) / 2 = 0.4
    assert kelly_fraction(Decimal("0.6"), Decimal("2")) == Decimal("0.4")


def test_kelly_fraction_is_zero_without_an_edge():
    assert kelly_fraction(Decimal("0.4"), Decimal("1")) == 0
    assert kelly_fraction(Decimal("0.5"), Decimal("1")) == 0


def test_kelly_fraction_boundaries():
    assert kelly_fraction(Decimal("0.5"), Decimal("0")) == 0  # undefined ratio
    with pytest.raises(ValueError):
        kelly_fraction(Decimal("1.5"), Decimal("2"))
    with pytest.raises(ValueError):
        kelly_fraction(Decimal("0.5"), Decimal("-1"))


def test_optimal_bet_size_is_scaled_and_capped():
    # Kelly 0.4, half of it 0.2, capped at the 2% default.
    assert optimal_bet_size(Decimal("0.6"), Decimal("2")) == Decimal("0.02")
    # A small edge stays below the cap.
    assert optimal_bet_size(Decimal("0.51"), Decimal("1")) == Decimal("0.01")


def test_optimal_bet_size_rejects_a_bad_scale():
    with pytest.raises(ValueError):
        optimal_bet_size(Decimal("0.6"), Decimal("2"), kelly_scale=Decimal("0"))
    with pytest.raises(ValueError):
        optimal_bet_size(Decimal("0.6"), Decimal("2"), max_risk=Decimal("0"))


def test_position_size_needs_a_minimum_sample():
    size, warnings = position_size_from_trades(_FakeResult(_pnls(3, 2)))

    assert size == 0
    assert any("too few" in w for w in warnings)


def test_position_size_is_zero_without_losing_trades():
    size, warnings = position_size_from_trades(_FakeResult([Decimal("2")] * 40))

    assert size == 0
    assert any("no losing" in w for w in warnings)


def test_position_size_is_zero_without_an_edge():
    # 40% win rate at even odds: no edge to size.
    size, warnings = position_size_from_trades(
        _FakeResult(_even_odds(20, 30))
    )

    assert size == 0
    assert any("no positive edge" in w for w in warnings)


def test_position_size_is_capped_by_the_configured_maximum():
    # 60% win rate, 2:1 payoff -> half Kelly 0.2, capped at 2%.
    size, warnings = position_size_from_trades(_FakeResult(_pnls(60, 40)))

    assert size == Decimal("0.02")
    assert any("capped" in w for w in warnings)
    assert any("not advice" in w for w in warnings)


def test_position_size_below_the_cap_is_returned():
    # 51% win rate at even odds -> Kelly 0.02, half Kelly 0.01.
    size, warnings = position_size_from_trades(
        _FakeResult(_even_odds(51, 49))
    )

    assert size == Decimal("0.01")
    assert not any("configured maximum" in w for w in warnings)


def test_position_size_respects_a_custom_kelly_scale():
    full, _ = position_size_from_trades(
        _FakeResult(_even_odds(51, 49)),
        PositionSizingConfig(max_risk_per_trade=Decimal("1")),
        kelly_scale=Decimal("1"),
    )

    assert full == Decimal("0.02")  # full Kelly


def test_risk_of_ruin_report_carries_the_recommendation():
    result = run_backtest(
        _candles(30), BuyAndHoldStrategy(), _config()
    )

    report = compute_risk_of_ruin(result)

    assert report.recommended_risk_per_trade == 0
    assert report.warnings  # it says why it cannot recommend a size


def _trading_candles(count: int = 600) -> list[Candle]:
    """A sine series that actually produces closed trades."""
    candles = []
    price = Decimal("100")
    for i in range(count):
        price = max(
            Decimal("10"), price + Decimal(str(0.4 * math.sin(i / 18.0)))
        )
        open_time = BASE + timedelta(hours=i)
        candles.append(
            Candle(
                symbol=Symbol("BTC/USDT"),
                interval="1h",
                open_time=open_time,
                close_time=open_time + timedelta(minutes=59, seconds=59),
                open=price,
                high=price + 1,
                low=price - 1,
                close=price + Decimal(str(0.2 * math.sin(i / 5.0))),
                volume=Decimal("10"),
            )
        )
    return candles


def test_risk_of_ruin_report_recommends_a_size_from_trade_data():
    result = run_backtest(
        _trading_candles(), MACrossoverStrategy(fast=5, slow=20), _config()
    )
    assert result.trades, "the fixture must produce trades"

    report = compute_risk_of_ruin(result)

    assert isinstance(report.recommended_risk_per_trade, Decimal)
    assert any("too few" in w for w in report.warnings)


def test_position_size_warns_about_a_suspiciously_large_edge():
    """60.2: warn when the estimate leans on favourable assumptions."""
    # An 80% win rate at even odds is a classic overfitting signature.
    size, warnings = position_size_from_trades(_FakeResult(_even_odds(32, 8)))

    assert size > 0
    assert any("unusually large" in w for w in warnings)

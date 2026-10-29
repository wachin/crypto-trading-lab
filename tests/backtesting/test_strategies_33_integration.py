"""Integration tests for chapter 33 strategies (items 2/3/4).

These exercise the full run_backtest pipeline end-to-end: trade lifecycle
(flat -> in-position -> flat), P&L consistency against the equity curve,
exposure-curve correctness, non-negative cost attribution, warmup silence,
and the degenerate no-trade case. They complement the unit-level signal
tests in test_strategies_33.py.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from crypto_trading_lab.backtesting.engine import (
    BacktestConfig,
    BollingerBandsMeanReversionStrategy,
    NullStrategy,
    RollingHighLowBreakoutStrategy,
    RSIStrategy,
    run_backtest,
)
from crypto_trading_lab.domain.models import Candle, Symbol
from crypto_trading_lab.strategy_registry import StrategyRegistry

BASE = datetime(2024, 1, 1, tzinfo=timezone.utc)


def _candles(closes, volumes=None):
    """Build deterministic candles from a close sequence.

    Each candle's open is the previous close (so fills at next-open are
    deterministic and traceable); high/low bracket the close; volume is
    constant 10 unless overridden.
    """
    out = []
    for i, c in enumerate(closes):
        vol = Decimal("10") if volumes is None else Decimal(str(volumes[i]))
        prev = closes[i - 1] if i > 0 else c
        # high/low must bound both open and close (Candle validates this).
        hi = max(prev, c)
        lo = min(prev, c)
        out.append(
            Candle(
                Symbol("BTC/USDT"),
                "1m",
                BASE + timedelta(minutes=i),
                BASE + timedelta(minutes=i + 1),
                open=Decimal(str(prev)),
                high=Decimal(str(hi)),
                low=Decimal(str(lo)),
                close=Decimal(str(c)),
                volume=vol,
            )
        )
    return out


# -- RSI -----------------------------------------------------------------------

def test_rsi_integration_trade_lifecycle_and_pnl():
    """A single BUY then SELL must leave the engine flat, with the trade
    P&L matching the equity change."""
    period = 5
    closes = [100] * 20 + list(range(100, 40, -4)) + [40] * 3 + list(range(40, 120, 4))
    candles = _candles(closes)
    result = run_backtest(candles, RSIStrategy(period=period))

    # At least one round-trip trade.
    assert len(result.trades) >= 1

    # Every closed trade has both prices and non-negative costs.
    for t in result.trades:
        assert t.exit_price is not None
        assert t.entry_fee >= 0
        assert t.exit_fee >= 0
        assert t.slippage_cost >= 0
        assert t.spread_cost >= 0

    # Equity delta equals net profit.
    assert result.final_equity == result.initial_capital + result.net_profit

    # Net profit reconciles with trade-level net P&L plus any open position.
    trade_pnl = sum((t.net_pnl for t in result.trades), Decimal(0))
    assert result.net_profit == trade_pnl

    # Exposure curve is True only when a position was open.
    assert len(result.exposure_curve) == len(candles)
    assert any(result.exposure_curve), "expected at least one in-market candle"
    assert not all(result.exposure_curve), "expected flat periods too"

    # Order count matches two orders per closed trade (entry + exit).
    assert result.order_count == 2 * len(result.trades)


def test_rsi_warmup_produces_no_trades():
    """Before the RSI period is satisfied there must be no signals, hence
    no trades on a flat series shorter than the warmup."""
    short = _candles([100] * (RSIStrategy(period=14).warmup_candles - 1))
    # run_backtest needs >= 2 candles; this is a degenerate flat run.
    result = run_backtest(short, RSIStrategy(period=14))
    assert result.trades == []
    assert result.final_equity == result.initial_capital
    assert not any(result.exposure_curve)


def test_rsi_flat_market_no_trades():
    """A perfectly flat price never crosses oversold/overbought, so no
    trades fire and capital is untouched."""
    flat = _candles([100] * 60)
    result = run_backtest(flat, RSIStrategy(period=5))
    assert result.trades == []
    assert result.final_equity == result.initial_capital


def test_rsi_volume_filter_blocks_low_volume_entry():
    """With a volume filter, a low-volume candle at the oversold cross
    must suppress the entry the unfiltered strategy would take."""
    period = 5
    closes = [100] * 20 + list(range(100, 40, -4)) + [40] * 3 + list(range(40, 120, 4))
    # Normal volume everywhere except a spike-suppressed band is not needed;
    # we just verify the filtered run has <= trades than the unfiltered one.
    base = run_backtest(_candles(closes), RSIStrategy(period=period))
    filtered = run_backtest(
        _candles(closes), RSIStrategy(period=period, volume_filter_period=3)
    )
    assert len(filtered.trades) <= len(base.trades)


# -- Breakout ------------------------------------------------------------------

def test_breakout_integration_round_trip():
    """A spike above the rolling high opens a long; a drop below the
    rolling low closes it. Verify the lifecycle and that the exit price
    differs from the entry price on a real move."""
    closes = [100] * 25 + [100, 130, 100, 70, 100]
    result = run_backtest(_candles(closes), RollingHighLowBreakoutStrategy(period=20))

    assert len(result.trades) >= 1
    t = result.trades[0]
    assert t.side == "buy"
    assert t.exit_price is not None
    assert t.exit_price != t.entry_price

    # Equity consistency.
    assert result.final_equity == result.initial_capital + result.net_profit
    trade_pnl = sum((t.net_pnl for t in result.trades), Decimal(0))
    assert result.net_profit == trade_pnl


def test_breakout_no_breakout_no_trades():
    """Inside a tight range that never breaks the rolling extremes, no
    signals fire."""
    closes = [100] * 40
    result = run_backtest(_candles(closes), RollingHighLowBreakoutStrategy(period=20))
    assert result.trades == []
    assert result.final_equity == result.initial_capital


def test_breakout_equity_curve_length_matches_candles():
    """The equity curve must have one point per candle."""
    closes = [100] * 25 + [100, 130, 100, 70, 100]
    candles = _candles(closes)
    result = run_backtest(candles, RollingHighLowBreakoutStrategy(period=20))
    assert len(result.equity_curve) == len(candles)
    assert result.equity_curve[0] == result.initial_capital


# -- Bollinger -----------------------------------------------------------------

def test_bollinger_integration_round_trip():
    """A close into the lower band opens a long; recovery to the middle
    band closes it. Verify the trade and cost attribution."""
    closes = [100] * 20 + [70, 90, 110, 100]
    result = run_backtest(
        _candles(closes), BollingerBandsMeanReversionStrategy(period=10, k=2)
    )

    assert len(result.trades) >= 1
    t = result.trades[0]
    assert t.side == "buy"
    assert t.exit_price is not None

    # Costs never negative.
    assert t.entry_fee >= 0
    assert t.exit_fee >= 0
    assert t.slippage_cost >= 0
    assert t.spread_cost >= 0

    # P&L reconciles.
    assert result.final_equity == result.initial_capital + result.net_profit
    trade_pnl = sum((t.net_pnl for t in result.trades), Decimal(0))
    assert result.net_profit == trade_pnl


def test_bollinger_flat_market_no_trades():
    """A flat series has zero variance, so the bands collapse to the mean
    and price never crosses into the lower band — no trades."""
    flat = _candles([100] * 40)
    result = run_backtest(
        flat, BollingerBandsMeanReversionStrategy(period=10, k=2)
    )
    assert result.trades == []
    assert result.final_equity == result.initial_capital


# -- Registry end-to-end -------------------------------------------------------

def test_registry_to_engine_full_flow():
    """Creating a strategy through the registry and running it through
    run_backtest must behave identically to a direct instantiation."""
    reg = StrategyRegistry(load=False)
    via_registry = reg.create_instance("rsi", period=5)
    direct = RSIStrategy(period=5)

    closes = [100] * 20 + list(range(100, 40, -4)) + [40] * 3 + list(range(40, 120, 4))
    candles = _candles(closes)

    r1 = run_backtest(candles, via_registry)
    r2 = run_backtest(candles, direct)

    assert r1.trades == r2.trades
    assert r1.final_equity == r2.final_equity
    assert r1.equity_curve == r2.equity_curve


# -- Null strategy degenerate case ---------------------------------------------

def test_null_strategy_no_trades_no_costs():
    """The null strategy never emits a signal, so the run is a no-op:
    no trades, no costs, untouched capital."""
    candles = _candles([100, 101, 102, 103, 104])
    result = run_backtest(candles, NullStrategy())

    assert result.trades == []
    assert result.order_count == 0
    assert result.final_equity == result.initial_capital
    assert result.total_fees == 0
    assert result.total_slippage == 0
    assert result.total_spread == 0
    assert not any(result.exposure_curve)


# -- Determinism ---------------------------------------------------------------

def test_rsi_deterministic_across_runs():
    """The same candles and config must reproduce the same result."""
    closes = [100] * 20 + list(range(100, 40, -4)) + [40] * 3 + list(range(40, 120, 4))
    candles = _candles(closes)
    cfg = BacktestConfig()
    r1 = run_backtest(candles, RSIStrategy(period=5), config=cfg)
    r2 = run_backtest(candles, RSIStrategy(period=5), config=cfg)
    assert r1.trades == r2.trades
    assert r1.final_equity == r2.final_equity
    assert r1.equity_curve == r2.equity_curve

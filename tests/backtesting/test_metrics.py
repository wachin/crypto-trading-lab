"""Performance metrics tests (ROADMAP.md chapter 40).

Every scenario is small and hand-verifiable: exact Decimal arithmetic
for trade statistics, known drawdown series, explicit Sharpe values,
and the chapter 40.6 validity warnings.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from crypto_trading_lab.backtesting.engine import (
    BacktestConfig,
    BacktestResult,
    BuyAndHoldStrategy,
    CostModel,
    TradeRecord,
    run_backtest,
)
from crypto_trading_lab.backtesting.metrics import (
    DISCLAIMER,
    MetricConfig,
    compute_performance,
)
from crypto_trading_lab.domain.models import Candle, Symbol

BASE = datetime(2024, 1, 1, tzinfo=timezone.utc)
EPS = Decimal("0.0000000001")


def _trade(pnl: Decimal, hours: int = 1) -> TradeRecord:
    """A closed trade whose net pnl is exactly ``pnl`` (zero costs)."""
    entry = BASE
    exit_ = entry + timedelta(hours=hours)
    return TradeRecord(
        entry_time=entry.isoformat(),
        exit_time=exit_.isoformat(),
        side="buy",
        quantity=Decimal(1),
        entry_price=Decimal(100),
        exit_price=Decimal(100) + pnl,
        entry_fee=Decimal(0),
        exit_fee=Decimal(0),
        slippage_cost=Decimal(0),
        spread_cost=Decimal(0),
    )


def _result(
    equity: list[str],
    trades: list[TradeRecord] | None = None,
    capital: Decimal = Decimal("100"),
    order_count: int = 0,
    exposure: tuple[bool, ...] | None = None,
) -> BacktestResult:
    equity_curve = tuple(Decimal(e) for e in equity)
    return BacktestResult(
        strategy_name="manual",
        config_metadata={},
        trades=trades or [],
        final_equity=equity_curve[-1],
        initial_capital=capital,
        total_fees=Decimal(0),
        total_slippage=Decimal(0),
        total_spread=Decimal(0),
        equity_curve=equity_curve,
        candle_count=len(equity_curve),
        order_count=order_count,
        exposure_curve=exposure or tuple(False for _ in equity_curve),
    )


# --- 40.1 + 40.6: empty run -------------------------------------------------


def test_empty_run_reports_nothing_and_warns():
    report = compute_performance(_result(["100", "100", "100", "100"]))
    assert report.returns.net_profit == Decimal(0)
    assert report.returns.total_return == Decimal(0)
    assert report.trades.number_of_trades == 0
    assert report.trades.win_rate is None
    assert report.trades.average_trade is None
    assert report.trades.median_trade is None
    assert report.risk.max_drawdown == Decimal(0)
    assert report.risk.average_drawdown is None
    assert report.risk.volatility is None  # zero volatility → ratio off
    assert report.risk.sharpe_ratio is None
    assert report.returns.annualized_return is None
    text = " ".join(report.warnings)
    assert "no trades" in text
    assert "annualized return suppressed" in text
    assert "no benchmark" in text
    assert report.disclaimer == DISCLAIMER


# --- 40.2: hand-checked trade statistics -------------------------------------


def test_trade_statistics_are_hand_verified():
    trades = [_trade(Decimal("200")), _trade(Decimal("-100")),
              _trade(Decimal("150"))]
    report = compute_performance(
        _result(["100", "100", "100"], trades)
    )
    stats = report.trades
    assert stats.number_of_trades == 3
    assert stats.winning_trades == 2
    assert stats.losing_trades == 1
    assert stats.win_rate == Decimal(2) / Decimal(3)
    assert stats.average_winning_trade == Decimal("175")
    assert stats.average_losing_trade == Decimal("-100")
    assert stats.largest_winning_trade == Decimal("200")
    assert stats.largest_losing_trade == Decimal("-100")
    assert stats.average_trade == Decimal("250") / Decimal(3)
    assert stats.median_trade == Decimal("150")
    assert stats.profit_factor == Decimal("3.5")
    assert stats.expectancy == Decimal("250") / Decimal(3)
    assert stats.average_holding_seconds == Decimal("3600")
    assert report.returns.gross_profit == Decimal("350")
    assert report.returns.gross_loss == Decimal("-100")
    assert "very small sample" in " ".join(report.warnings)


def test_consecutive_streaks():
    trades = [_trade(Decimal("1")) for _ in range(3)] + [
        _trade(Decimal("-1")) for _ in range(2)
    ]
    report = compute_performance(_result(["100", "100"], trades))
    assert report.trades.max_consecutive_wins == 3
    assert report.trades.max_consecutive_losses == 2


# --- 40.3: drawdowns, exact decimals ------------------------------------------


def test_drawdown_series_hand_verified():
    # Peak 120 at index 1; below it at 90 (0.25), 100 (1/6), 110 (1/12);
    # new peak at 130. Max = 1/4, duration = 3 candles, mean = 1/6.
    report = compute_performance(
        _result(["100", "120", "90", "100", "110", "130"])
    )
    assert report.risk.max_drawdown == Decimal("0.25")
    assert report.risk.max_drawdown_duration == 3
    assert abs(report.risk.average_drawdown - Decimal(1) / 6) < EPS


def test_sharpe_exact_with_scaling_and_validity_flag():
    # Returns: 0.1, -0.1, 0.1 → mean 1/30, std sqrt(2)/15, so with a
    # zero risk-free rate and one period per year Sharpe = 1/(2*sqrt(2)).
    report = compute_performance(
        _result(["100", "110", "99", "108.9"]),
        config=MetricConfig(periods_per_year=Decimal(1)),
    )
    expected = Decimal(1) / (Decimal(2) * Decimal(2).sqrt())
    assert abs(report.risk.sharpe_ratio - expected) < EPS
    assert not report.risk.sharpe_is_valid  # 3 observations < 30
    assert "not statistically supported" in " ".join(report.warnings)

    report_ok = compute_performance(
        _result(["100", "110", "99", "108.9"]),
        config=MetricConfig(
            periods_per_year=Decimal(1), min_observations_ratio=3
        ),
    )
    assert report_ok.risk.sharpe_is_valid


def test_sortino_and_risk_adjusted():
    # Returns below zero exist, so downside deviation is defined.
    report = compute_performance(
        _result(["100", "110", "99", "108.9"]),
        config=MetricConfig(periods_per_year=Decimal(1),
                            min_observations_ratio=3),
    )
    assert report.risk.sortino_ratio is not None
    assert report.risk.sortino_is_valid
    # risk-adjusted return = total return / volatility
    assert report.risk.risk_adjusted_return == (
        report.returns.total_return / report.risk.volatility
    )


def test_annualization_and_calmar():
    # A one-year run that doubles: annualized return == total return.
    n = 365
    equity = [
        str(Decimal(100) + Decimal(100) * Decimal(i) / Decimal(n - 1))
        for i in range(n)
    ]
    report = compute_performance(_result(equity))
    assert report.returns.annualized_is_valid
    assert abs(report.returns.annualized_return - Decimal(1)) < EPS
    assert report.risk.calmar_ratio is None  # monotonic: no drawdown


# --- 40.4 + 40.5 --------------------------------------------------------------


def test_activity_metrics_from_trades():
    trades = [_trade(Decimal("5")), _trade(Decimal("-5"))]
    report = compute_performance(
        _result(["100", "100"], trades, order_count=4)
    )
    activity = report.activity
    # turnover = entry notional + exit notional of each trade:
    # (100 + 105) + (100 + 95) = 400
    assert activity.turnover == Decimal("400")
    assert activity.number_of_orders == 4
    assert activity.commissions == Decimal(0)
    assert activity.spread_cost == Decimal(0)


def test_compare_reports_relative_metrics():
    """Chapter 42.2: relative comparison is exact, Decimals."""
    from crypto_trading_lab.backtesting.metrics import compare_reports

    # Strategy: 100 → 115 (+15%), one winning trade, zero costs.
    strategy = compute_performance(
        _result(["100", "100", "115"], [_trade(Decimal("15"))])
    )
    # Benchmark: 100 → 110 (+10%), no trades.
    benchmark = compute_performance(_result(["100", "100", "110"]))
    view = compare_reports(strategy, benchmark, "Buy and hold")
    assert view.excess_return == Decimal("0.05")
    assert view.gross_excess_return == Decimal("0.05")  # no costs
    assert view.cost_drag == Decimal(0)
    assert view.beats_benchmark

    # Losing case: strategy +5% vs benchmark +10%.
    weaker = compute_performance(
        _result(["100", "100", "105"], [_trade(Decimal("5"))])
    )
    view = compare_reports(weaker, benchmark, "Buy and hold")
    assert view.excess_return == Decimal("-0.05")
    assert not view.beats_benchmark


def test_benchmark_comparison():
    strategy = _result(["100", "110"])  # +10%
    benchmark = _result(["100", "105"])  # +5%
    report = compute_performance(strategy, benchmark=benchmark)
    section = report.benchmark
    assert section is not None
    assert section.absolute_return == Decimal("0.1")
    assert section.benchmark_return == Decimal("0.05")
    assert section.excess_return == Decimal("0.05")


# --- 40.7: configuration is recorded ------------------------------------------


def test_metric_configuration_is_recorded():
    report = compute_performance(_result(["100", "101"]))
    for key in (
        "periodicity",
        "annualization_method",
        "risk_free_rate",
        "return_calculation_method",
        "missing_data_treatment",
        "zero_returns_treatment",
        "relevant_assumptions",
    ):
        assert key in report.metric_config


# --- engine integration --------------------------------------------------------


def _candles(closes):
    return [
        Candle(
            Symbol("BTC/USDT"),
            "1m",
            BASE + timedelta(minutes=i),
            BASE + timedelta(minutes=i + 1),
            open=Decimal(str(c)),
            high=Decimal(str(c + 1)),
            low=Decimal(str(c - 1)),
            close=Decimal(str(c)),
            volume=Decimal("10"),
        )
        for i, c in enumerate(closes)
    ]


def test_metrics_from_real_engine_run():
    flat = CostModel(
        maker_fee=Decimal(0),
        taker_fee=Decimal(0),
        slippage_fraction=Decimal(0),
        spread_fraction=Decimal(0),
    )
    result = run_backtest(
        _candles([100, 101, 102]),
        BuyAndHoldStrategy(),
        BacktestConfig(costs=flat),
    )
    report = compute_performance(result)
    # Entered at candle 1: exposure curve is [False, True, True].
    assert report.risk.market_exposure == Decimal(2) / Decimal(3)
    assert report.risk.long_exposure == report.risk.market_exposure
    assert report.activity.number_of_orders == 1  # buy; never closed
    assert report.returns.net_profit == result.net_profit

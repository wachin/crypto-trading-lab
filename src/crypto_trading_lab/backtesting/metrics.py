"""Performance metrics (ROADMAP.md chapter 40).

Computes the chapter 40 metric catalogue from a ``BacktestResult``
(chapter 37 engine). Everything is exact ``Decimal`` arithmetic; no
metric is ever presented as proof that a strategy is good, safe, or
profitable in the future.

Statistical validity (chapter 40.6) is enforced by construction:
metrics that are not meaningful for the available data become ``None``
and the report carries a ``warnings`` list that the UI must surface.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal

from crypto_trading_lab.backtesting.engine import BacktestResult

__all__ = [
    "DISCLAIMER",
    "MetricConfig",
    "ReturnMetrics",
    "TradeStatistics",
    "RiskMetrics",
    "ActivityMetrics",
    "BenchmarkComparison",
    "BenchmarkView",
    "PerformanceReport",
    "compute_performance",
    "compare_reports",
]

#: Mandatory report disclaimer (ROADMAP 40.8).
DISCLAIMER = (
    "No single metric proves that a strategy is good. Performance must be "
    "interpreted together with risk, drawdown, trading costs, number of "
    "trades, market conditions, out-of-sample performance and robustness "
    "tests. Past backtest results do not predict future returns."
)


@dataclass(frozen=True)
class MetricConfig:
    """Configuration and assumptions behind every metric (chapter 40.7)."""

    periods_per_year: Decimal = Decimal("365")  # daily crypto candles
    risk_free_rate: Decimal = Decimal("0")      # annual fraction
    min_trades_warning: int = 30     # below this, statistics are fragile
    min_observations_ratio: int = 30  # below this, no Sharpe/Sortino

    def metadata(self) -> dict[str, str]:
        return {
            "periodicity": (
                "one equity sample per candle; "
                f"{self.periods_per_year} periods assumed per year"
            ),
            "annualization_method": (
                "geometric compounding for returns; sqrt(time) scaling "
                "for volatility and ratios"
            ),
            "risk_free_rate": str(self.risk_free_rate),
            "return_calculation_method": (
                "simple per-period returns from the close-to-close "
                "equity curve"
            ),
            "missing_data_treatment": (
                "none needed: the engine produces a contiguous, regular "
                "equity curve (it rejects fewer than two candles)"
            ),
            "zero_returns_treatment": (
                "zero returns are kept; zero volatility or zero downside "
                "deviation disables the corresponding ratio (None)"
            ),
            "relevant_assumptions": (
                "long-only spot engine; all fills assumed complete "
                "(no rejections, no partial fills); no funding costs"
            ),
        }


@dataclass(frozen=True)
class ReturnMetrics:
    """Chapter 40.1."""

    initial_capital: Decimal
    final_equity: Decimal
    net_profit: Decimal
    gross_profit: Decimal
    gross_loss: Decimal
    total_return: Decimal                       # fraction
    annualized_return: Decimal | None           # None = not meaningful
    annualized_is_valid: bool


@dataclass(frozen=True)
class TradeStatistics:
    """Chapter 40.2."""

    number_of_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: Decimal | None
    average_winning_trade: Decimal | None
    average_losing_trade: Decimal | None
    largest_winning_trade: Decimal | None
    largest_losing_trade: Decimal | None
    average_trade: Decimal | None
    median_trade: Decimal | None
    profit_factor: Decimal | None
    expectancy: Decimal | None
    average_holding_seconds: Decimal | None     # entry→exit wall time
    max_consecutive_wins: int
    max_consecutive_losses: int


@dataclass(frozen=True)
class RiskMetrics:
    """Chapter 40.3. Ratios are ``None`` when not statistically meaningful."""

    max_drawdown: Decimal                       # fraction, ≥ 0
    max_drawdown_duration: int                  # candles below prior peak
    average_drawdown: Decimal | None            # mean of non-zero drawdowns
    volatility: Decimal | None                  # annualized
    downside_volatility: Decimal | None         # annualized
    sharpe_ratio: Decimal | None
    sharpe_is_valid: bool
    sortino_ratio: Decimal | None
    sortino_is_valid: bool
    calmar_ratio: Decimal | None
    risk_adjusted_return: Decimal | None        # total_return / volatility
    market_exposure: Decimal                    # fraction of candles in market
    long_exposure: Decimal                      # identical (long-only engine)


@dataclass(frozen=True)
class ActivityMetrics:
    """Chapter 40.4. Rejections, partial fills and funding are structurally
    zero in the chapter 37 engine (long-only spot, all-or-nothing fills,
    no funding); they stay pending in the roadmap until a paper-trading
    layer (chapter 57) can produce them."""

    turnover: Decimal                           # traded notional
    number_of_orders: int
    commissions: Decimal                        # per-trade view
    trading_fees: Decimal                       # aggregate view (same model)
    spread_cost: Decimal
    slippage_cost: Decimal


@dataclass(frozen=True)
class BenchmarkComparison:
    """Chapter 40.5."""

    benchmark_name: str
    absolute_return: Decimal
    benchmark_return: Decimal
    excess_return: Decimal                      # absolute minus benchmark


@dataclass(frozen=True)
class BenchmarkView:
    """Relative comparison against the benchmark (chapter 42.2).

    All fields are strategy minus benchmark. Positive excess_return
    means the active strategy beat the passive alternative net of
    costs; gross_excess_return shows the same comparison as if all
    costs had been zero (the cost drag is their difference).
    """

    benchmark_name: str
    excess_return: Decimal
    gross_excess_return: Decimal
    cost_drag: Decimal
    volatility_difference: Decimal | None
    max_drawdown_difference: Decimal | None
    sharpe_difference: Decimal | None
    sortino_difference: Decimal | None

    @property
    def beats_benchmark(self) -> bool:
        return self.excess_return > 0


def compare_reports(
    strategy: PerformanceReport,
    benchmark: PerformanceReport,
    benchmark_name: str,
) -> BenchmarkView:
    """Relative strategy-vs-benchmark comparison (chapter 42.2).

    Both reports must come from the same dataset period, initial
    capital and cost assumptions (chapter 42.1); the application layer
    guarantees this by running both on the same candles and config.
    """

    def gross_return(report: PerformanceReport) -> Decimal:
        capital = report.returns.initial_capital
        if capital == 0:
            return Decimal(0)
        activity = report.activity
        gross_net = (
            report.returns.net_profit
            + activity.trading_fees
            + activity.spread_cost
            + activity.slippage_cost
        )
        return gross_net / capital

    def difference(a, b):
        return None if a is None or b is None else a - b

    excess = (
        strategy.returns.total_return - benchmark.returns.total_return
    )
    gross_excess = gross_return(strategy) - gross_return(benchmark)
    return BenchmarkView(
        benchmark_name=benchmark_name,
        excess_return=excess,
        gross_excess_return=gross_excess,
        cost_drag=gross_excess - excess,
        volatility_difference=difference(
            strategy.risk.volatility, benchmark.risk.volatility
        ),
        max_drawdown_difference=difference(
            strategy.risk.max_drawdown, benchmark.risk.max_drawdown
        ),
        sharpe_difference=difference(
            strategy.risk.sharpe_ratio, benchmark.risk.sharpe_ratio
        ),
        sortino_difference=difference(
            strategy.risk.sortino_ratio, benchmark.risk.sortino_ratio
        ),
    )


@dataclass
class PerformanceReport:
    """The chapter 40 deliverable."""

    returns: ReturnMetrics
    trades: TradeStatistics
    risk: RiskMetrics
    activity: ActivityMetrics
    benchmark: BenchmarkComparison | None
    warnings: list[str] = field(default_factory=list)
    metric_config: dict[str, str] = field(default_factory=dict)
    disclaimer: str = DISCLAIMER


def _equity_returns(equity_curve: tuple[Decimal, ...]) -> list[Decimal]:
    """Simple per-period returns; periods after zero equity are skipped."""
    returns: list[Decimal] = []
    for previous, current in zip(equity_curve, equity_curve[1:]):
        if previous == 0:
            continue
        returns.append((current - previous) / previous)
    return returns


def _drawdowns(
    equity_curve: tuple[Decimal, ...],
) -> tuple[list[Decimal], int]:
    """Per-candle drawdown fractions and the longest below-peak streak."""
    peak = equity_curve[0]
    drawdowns: list[Decimal] = []
    streak = 0
    longest = 0
    for equity in equity_curve[1:]:
        if equity > peak:
            peak = equity
        if peak > 0 and equity < peak:
            drawdowns.append((peak - equity) / peak)
            streak += 1
            longest = max(longest, streak)
        else:
            streak = 0
    return drawdowns, longest


def _std(values: list[Decimal], mean: Decimal) -> Decimal:
    variance = sum((v - mean) ** 2 for v in values) / len(values)
    return variance.sqrt()


def _sqrt(value: Decimal) -> Decimal:
    return value.sqrt()


def _annualized_return(
    total_return: Decimal, periods: int, periods_per_year: Decimal
) -> Decimal:
    """Geometric compounding via Decimal ln/exp."""
    base = Decimal(1) + total_return
    exponent = periods_per_year / Decimal(periods)
    return (base.ln() * exponent).exp() - Decimal(1)


def _median(sorted_values: list[Decimal]) -> Decimal:
    n = len(sorted_values)
    middle = n // 2
    if n % 2 == 1:
        return sorted_values[middle]
    return (sorted_values[middle - 1] + sorted_values[middle]) / Decimal(2)


def _max_streak(signs: list[int], target: int) -> int:
    best = run = 0
    for sign in signs:
        run = run + 1 if sign == target else 0
        best = max(best, run)
    return best


def compute_performance(
    result: BacktestResult,
    benchmark: BacktestResult | None = None,
    config: MetricConfig | None = None,
) -> PerformanceReport:
    """Compute the chapter 40 metric catalogue for one backtest run."""
    config = config or MetricConfig()
    warnings: list[str] = []
    ppy = config.periods_per_year

    # --- 40.1 Return and profit metrics --------------------------------
    net_profit = result.net_profit
    trade_pnls = [t.net_pnl for t in result.trades]
    gross_profit = sum((p for p in trade_pnls if p > 0), Decimal(0))
    gross_loss = sum((p for p in trade_pnls if p < 0), Decimal(0))
    total_return = result.return_fraction
    periods = result.candle_count
    annualized_valid = periods >= int(ppy)
    annualized: Decimal | None = None
    if annualized_valid:
        annualized = _annualized_return(total_return, periods, ppy)
    else:
        warnings.append(
            f"annualized return suppressed: {periods} candles cover less "
            f"than one year ({int(ppy)} periods); extrapolating shorter "
            "periods is misleading"
        )
    returns = ReturnMetrics(
        initial_capital=result.initial_capital,
        final_equity=result.final_equity,
        net_profit=net_profit,
        gross_profit=gross_profit,
        gross_loss=gross_loss,
        total_return=total_return,
        annualized_return=annualized,
        annualized_is_valid=annualized_valid,
    )

    # --- 40.2 Trade statistics ------------------------------------------
    n_trades = len(result.trades)
    wins = [p for p in trade_pnls if p > 0]
    losses = [p for p in trade_pnls if p < 0]

    holding_periods: list[Decimal] = []
    for trade in result.trades:
        if trade.exit_time is None:
            continue
        entry = datetime.fromisoformat(trade.entry_time)
        exit_ = datetime.fromisoformat(trade.exit_time)
        # The engine fills at candle opens, so durations are exact
        # multiples of the candle interval; we report raw seconds.
        holding_periods.append(Decimal(str((exit_ - entry).total_seconds())))

    signs = [1 if p > 0 else (-1 if p < 0 else 0) for p in trade_pnls]
    sorted_pnls = sorted(trade_pnls)

    if n_trades == 0:
        warnings.append(
            "no trades: no trade statistics can be computed; the result "
            "says nothing about the strategy"
        )
    elif n_trades < config.min_trades_warning:
        warnings.append(
            f"very small sample: {n_trades} trades (< "
            f"{config.min_trades_warning}); trade statistics are "
            "descriptive only, not statistically supported"
        )

    trades = TradeStatistics(
        number_of_trades=n_trades,
        winning_trades=len(wins),
        losing_trades=len(losses),
        win_rate=(
            Decimal(len(wins)) / Decimal(n_trades) if n_trades else None
        ),
        average_winning_trade=(
            sum(wins) / Decimal(len(wins)) if wins else None
        ),
        average_losing_trade=(
            sum(losses) / Decimal(len(losses)) if losses else None
        ),
        largest_winning_trade=max(wins) if wins else None,
        largest_losing_trade=min(losses) if losses else None,
        average_trade=(
            sum(trade_pnls) / Decimal(n_trades) if n_trades else None
        ),
        median_trade=_median(sorted_pnls) if sorted_pnls else None,
        profit_factor=(
            gross_profit / abs(gross_loss) if gross_loss < 0 else None
        ),
        expectancy=(
            sum(trade_pnls) / Decimal(n_trades) if n_trades else None
        ),
        average_holding_seconds=(
            sum(holding_periods) / Decimal(len(holding_periods))
            if holding_periods
            else None
        ),
        max_consecutive_wins=_max_streak(signs, 1),
        max_consecutive_losses=_max_streak(signs, -1),
    )

    # --- 40.3 Risk metrics ----------------------------------------------
    period_returns = _equity_returns(result.equity_curve)
    drawdowns, max_dd_duration = _drawdowns(result.equity_curve)
    max_drawdown = max(drawdowns) if drawdowns else Decimal(0)
    average_drawdown = (
        sum(drawdowns) / Decimal(len(drawdowns)) if drawdowns else None
    )

    n_obs = len(period_returns)
    enough_observations = n_obs >= config.min_observations_ratio

    volatility: Decimal | None = None
    downside_vol: Decimal | None = None
    sharpe: Decimal | None = None
    sortino: Decimal | None = None
    sharpe_valid = False
    sortino_valid = False
    rf_per_period = config.risk_free_rate / ppy

    if n_obs >= 2:
        mean = sum(period_returns) / Decimal(n_obs)
        std = _std(period_returns, mean)
        downside = [min(r, Decimal(0)) for r in period_returns]
        downside_dev = (
            sum(d * d for d in downside) / Decimal(len(downside))
        ).sqrt()
        if std > 0:
            volatility = std * _sqrt(ppy)
            sharpe = (mean - rf_per_period) / std * _sqrt(ppy)
        if downside_dev > 0:
            downside_vol = downside_dev * _sqrt(ppy)
            sortino = (mean - rf_per_period) / downside_dev * _sqrt(ppy)
    else:
        warnings.append(
            f"not enough return observations ({n_obs}) to compute "
            "volatility-based metrics"
        )

    if sharpe is not None and enough_observations:
        sharpe_valid = True
    if sortino is not None and enough_observations:
        sortino_valid = True
    if (sharpe is not None or sortino is not None) and not enough_observations:
        warnings.append(
            f"Sharpe/Sortino computed from only {n_obs} return "
            f"observations (< {config.min_observations_ratio}); they are "
            "descriptive, not statistically supported conclusions"
        )
    if sharpe is not None and volatility is not None and sharpe == 0:
        pass  # nothing special; zero is a legitimate value

    calmar: Decimal | None = None
    if annualized is not None and max_drawdown > 0:
        calmar = annualized / max_drawdown
    risk_adjusted: Decimal | None = None
    if volatility is not None and volatility > 0:
        risk_adjusted = total_return / volatility

    in_market = (
        sum(1 for flag in result.exposure_curve if flag)
        if result.exposure_curve
        else 0
    )
    exposure = (
        Decimal(in_market) / Decimal(result.candle_count)
        if result.candle_count and result.exposure_curve
        else Decimal(0)
    )

    risk = RiskMetrics(
        max_drawdown=max_drawdown,
        max_drawdown_duration=max_dd_duration,
        average_drawdown=average_drawdown,
        volatility=volatility,
        downside_volatility=downside_vol,
        sharpe_ratio=sharpe,
        sharpe_is_valid=sharpe_valid,
        sortino_ratio=sortino,
        sortino_is_valid=sortino_valid,
        calmar_ratio=calmar,
        risk_adjusted_return=risk_adjusted,
        market_exposure=exposure,
        long_exposure=exposure,
    )

    # --- 40.4 Trading activity ------------------------------------------
    turnover = sum(
        (t.quantity * t.entry_price for t in result.trades), Decimal(0)
    ) + sum(
        (t.quantity * (t.exit_price or Decimal(0)) for t in result.trades),
        Decimal(0),
    )
    activity = ActivityMetrics(
        turnover=turnover,
        number_of_orders=result.order_count,
        commissions=result.total_fees,
        trading_fees=result.total_fees,
        spread_cost=result.total_spread,
        slippage_cost=result.total_slippage,
    )

    # --- 40.5 Benchmark comparison ---------------------------------------
    benchmark_section: BenchmarkComparison | None = None
    if benchmark is not None:
        benchmark_section = BenchmarkComparison(
            benchmark_name=benchmark.strategy_name,
            absolute_return=total_return,
            benchmark_return=benchmark.return_fraction,
            excess_return=total_return - benchmark.return_fraction,
        )
    else:
        warnings.append(
            "no benchmark supplied: absolute performance cannot be judged "
            "against any reference (chapter 40.5)"
        )

    return PerformanceReport(
        returns=returns,
        trades=trades,
        risk=risk,
        activity=activity,
        benchmark=benchmark_section,
        warnings=warnings,
        metric_config=config.metadata(),
    )

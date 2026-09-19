"""Benchmarking (ROADMAP.md chapter 42).

Provides standard benchmarks for strategy comparison and evaluation.
Implements common benchmarks like buy-and-hold, market indices, and risk-free rate.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Sequence, Optional

from crypto_trading_lab.domain.models import Candle


@dataclass(frozen=True)
class BenchmarkResult:
    """Result of a benchmark calculation."""
    name: str
    total_return: Decimal
    annualized_return: Decimal
    volatility: Decimal
    sharpe_ratio: Decimal
    max_drawdown: Decimal
    n_periods: int


def buy_and_hold_benchmark(
    candles: Sequence[Candle],
    initial_capital: Decimal = Decimal("10000"),
) -> BenchmarkResult:
    """
    Calculate buy-and-hold benchmark (42.1).

    Assumes buying at the first close and holding until the last close.
    """
    if len(candles) < 2:
        return BenchmarkResult(
            name="buy_and_hold",
            total_return=Decimal(0),
            annualized_return=Decimal(0),
            volatility=Decimal(0),
            sharpe_ratio=Decimal(0),
            max_drawdown=Decimal(0),
            n_periods=0,
        )

    first_close = Decimal(str(candles[0].close))
    last_close = Decimal(str(candles[-1].close))

    total_return = (last_close - first_close) / first_close

    # Calculate returns for volatility and drawdown
    closes = [Decimal(str(c.close)) for c in candles]
    returns = []
    for i in range(1, len(closes)):
        if closes[i-1] != 0:
            ret = (closes[i] - closes[i-1]) / closes[i-1]
            returns.append(ret)

    # Annualized return (assume 252 trading days per year)
    n = len(returns)
    if n > 0:
        annualized_return = (Decimal(1) + total_return) ** (Decimal(252) / Decimal(n)) - Decimal(1)
    else:
        annualized_return = Decimal(0)

    # Volatility
    volatility = Decimal(0)
    if len(returns) > 1:
        import statistics
        mean_ret = statistics.mean(float(r) for r in returns)
        variance = sum((float(r) - mean_ret) ** 2 for r in returns) / (len(returns) - 1)
        volatility = Decimal(str(variance ** 0.5)) * Decimal(str(252 ** 0.5))

    # Sharpe ratio (risk-free rate = 0 for simplicity)
    sharpe_ratio = Decimal(0)
    if volatility > 0:
        sharpe_ratio = (annualized_return - Decimal(0)) / volatility

    # Max drawdown
    peak = closes[0]
    max_drawdown = Decimal(0)
    for close in closes:
        if close > peak:
            peak = close
        if peak > 0:
            dd = (peak - close) / peak
            if dd > max_drawdown:
                max_drawdown = dd

    return BenchmarkResult(
        name="buy_and_hold",
        total_return=total_return,
        annualized_return=annualized_return,
        volatility=volatility,
        sharpe_ratio=sharpe_ratio,
        max_drawdown=max_drawdown,
        n_periods=len(returns),
    )


def risk_free_benchmark(
    candles: Sequence[Candle],
    risk_free_rate: Decimal = Decimal("0.02"),  # 2% annual
) -> BenchmarkResult:
    """
    Calculate risk-free rate benchmark (42.2).

    Represents a risk-free investment (e.g., Treasury bills).
    """
    n = len(candles) - 1
    if n <= 0:
        return BenchmarkResult(
            name="risk_free",
            total_return=Decimal(0),
            annualized_return=Decimal(0),
            volatility=Decimal(0),
            sharpe_ratio=Decimal(0),
            max_drawdown=Decimal(0),
            n_periods=0,
        )

    # Daily risk-free rate (assuming 252 trading days)
    daily_rf = (Decimal(1) + risk_free_rate) ** (Decimal(1) / Decimal(252)) - Decimal(1)
    total_return = (Decimal(1) + daily_rf) ** Decimal(len(candles) - 1) - Decimal(1)
    annualized_return = risk_free_rate
    volatility = Decimal(0)
    sharpe_ratio = Decimal(0)  # By definition, risk-free has 0 Sharpe
    max_drawdown = Decimal(0)

    return BenchmarkResult(
        name="risk_free",
        total_return=total_return,
        annualized_return=annualized_return,
        volatility=volatility,
        sharpe_ratio=sharpe_ratio,
        max_drawdown=max_drawdown,
        n_periods=len(candles) - 1,
    )


def market_index_benchmark(
    candles: Sequence[Candle],
    index_candles: Sequence[Candle],
) -> BenchmarkResult:
    """
    Calculate market index benchmark (42.3).

    Compares strategy performance against a market index (e.g., BTCUSDT for crypto).
    """
    if len(index_candles) < 2:
        return BenchmarkResult(
            name="market_index",
            total_return=Decimal(0),
            annualized_return=Decimal(0),
            volatility=Decimal(0),
            sharpe_ratio=Decimal(0),
            max_drawdown=Decimal(0),
            n_periods=0,
        )

    # Align index candles with strategy candles by timestamp
    # For simplicity, assume they're aligned
    min_len = min(len(candles), len(index_candles))
    index_closes = [Decimal(str(c.close)) for c in index_candles[:min_len]]

    first_close = index_closes[0]
    last_close = index_closes[-1]
    total_return = (last_close - first_close) / first_close

    # Calculate returns
    returns = []
    for i in range(1, len(index_closes)):
        if index_closes[i-1] != 0:
            ret = (index_closes[i] - index_closes[i-1]) / index_closes[i-1]
            returns.append(ret)

    n = len(returns)
    annualized_return = Decimal(0)
    if n > 0:
        annualized_return = (Decimal(1) + total_return) ** (Decimal(252) / Decimal(n)) - Decimal(1)

    volatility = Decimal(0)
    if len(returns) > 1:
        import statistics
        mean_ret = statistics.mean(float(r) for r in returns)
        variance = sum((float(r) - mean_ret) ** 2 for r in returns) / (len(returns) - 1)
        volatility = Decimal(str(variance ** 0.5)) * Decimal(str(252 ** 0.5))

    sharpe_ratio = Decimal(0)
    if volatility > 0:
        sharpe_ratio = annualized_return / volatility

    # Max drawdown
    peak = index_closes[0]
    max_drawdown = Decimal(0)
    for close in index_closes:
        if close > peak:
            peak = close
        if peak > 0:
            dd = (peak - close) / peak
            if dd > max_drawdown:
                max_drawdown = dd

    return BenchmarkResult(
        name="market_index",
        total_return=total_return,
        annualized_return=annualized_return,
        volatility=volatility,
        sharpe_ratio=sharpe_ratio,
        max_drawdown=max_drawdown,
        n_periods=len(returns),
    )


def compare_against_benchmarks(
    strategy_return: Decimal,
    strategy_sharpe: Decimal,
    strategy_dd: Decimal,
    benchmarks: list[BenchmarkResult],
) -> dict[str, dict]:
    """
    Compare strategy against multiple benchmarks (42.4).

    Returns a dictionary with comparison results.
    """
    results = {}
    for bench in benchmarks:
        return_diff = strategy_return - bench.total_return
        sharpe_diff = strategy_sharpe - bench.sharpe_ratio
        dd_diff = strategy_dd - bench.max_drawdown

        results[bench.name] = {
            "return_diff": return_diff,
            "sharpe_diff": sharpe_diff,
            "drawdown_diff": dd_diff,
            "outperforms_return": return_diff > 0,
            "outperforms_sharpe": sharpe_diff > 0,
            "lower_drawdown": dd_diff < 0,
        }
    return results


BENCHMARKING_WARNING = (
    "Benchmarks are reference points, not targets. "
    "Outperforming a benchmark in-sample does not guarantee future outperformance. "
    "Benchmarks must be chosen appropriately for the strategy's asset class and style."
)


__all__ = [
    "BenchmarkResult",
    "buy_and_hold_benchmark",
    "risk_free_benchmark",
    "market_index_benchmark",
    "compare_against_benchmarks",
    "BENCHMARKING_WARNING",
]

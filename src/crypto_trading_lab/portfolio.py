"""Portfolio construction and correlations (ROADMAP.md chapter 51).

This module provides basic correlation analysis and portfolio-level metrics.
It is a research capability for multi-asset and multi-strategy analysis.
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass
from decimal import Decimal
from typing import Sequence


@dataclass(frozen=True)
class ReturnsSeries:
    """Time series of returns for one asset or strategy."""
    name: str
    returns: list[Decimal]


@dataclass(frozen=True)
class Correlation:
    """Correlation between two series."""
    name_a: str
    name_b: str
    value: Decimal  # -1 to 1
    n_observations: int


@dataclass(frozen=True)
class PortfolioMetrics:
    """Portfolio-level performance metrics (51.3)."""
    total_return: Decimal
    total_drawdown: Decimal
    annualized_return: Decimal
    volatility: Decimal
    sharpe_ratio: Decimal
    n_periods: int


def compute_correlation(
    series_a: ReturnsSeries,
    series_b: ReturnsSeries,
) -> Correlation:
    """
    Compute Pearson correlation between two return series (51.2).
    """
    if len(series_a.returns) != len(series_b.returns):
        raise ValueError("Series must have same length")
    
    if len(series_a.returns) < 2:
        raise ValueError("Need at least 2 observations")
    
    a = [float(r) for r in series_a.returns]
    b = [float(r) for r in series_b.returns]
    
    mean_a = statistics.mean(a)
    mean_b = statistics.mean(b)
    
    # Compute covariance and standard deviations
    cov = sum((a[i] - mean_a) * (b[i] - mean_b) for i in range(len(a))) / len(a)
    std_a = (sum((x - mean_a) ** 2 for x in a) / len(a)) ** 0.5
    std_b = (sum((x - mean_b) ** 2 for x in b) / len(b)) ** 0.5
    
    if std_a == 0 or std_b == 0:
        value = Decimal(0)
    else:
        value = Decimal(str(cov / (std_a * std_b)))
    
    return Correlation(
        name_a=series_a.name,
        name_b=series_b.name,
        value=value,
        n_observations=len(a),
    )


def compute_portfolio_returns(
    series_list: Sequence[ReturnsSeries],
    weights: Sequence[Decimal] | None = None,
) -> ReturnsSeries:
    """
    Compute weighted portfolio returns (51.1).
    """
    if not series_list:
        raise ValueError("Need at least one series")
    
    if weights is None:
        weights = [Decimal(1) / Decimal(len(series_list))] * len(series_list)
    
    if len(weights) != len(series_list):
        raise ValueError("Weights length must match series count")
    
    n = len(series_list[0].returns)
    portfolio_returns = []
    
    for i in range(n):
        weighted_sum = sum(
            series.returns[i] * w for series, w in zip(series_list, weights)
        )
        portfolio_returns.append(weighted_sum)
    
    return ReturnsSeries(
        name="portfolio",
        returns=portfolio_returns,
    )


def compute_portfolio_metrics(
    portfolio_returns: ReturnsSeries,
    risk_free_rate: Decimal = Decimal(0),
    *,
    periods_per_year: int = 365,
) -> PortfolioMetrics:
    """
    Compute portfolio-level metrics (51.3).

    ``periods_per_year`` is the frequency of the return series. The
    default is 365 because crypto trades every day; pass 12 for monthly
    returns or 8760 for hourly ones. The old code assumed 252 equity
    trading days for every series, which understated a daily crypto
    Sharpe by ``sqrt(365/252)``.

    Returns compound: ``total_return`` is ``prod(1 + r) - 1``, not the
    sum of the returns, and the drawdown is measured on the compounded
    equity curve. It used to be measured on the return values themselves,
    so a series of 1% returns reported a 50% drawdown.

    There is no one-year guard here, unlike ``backtesting.metrics``: four
    periods annualize to an absurd number. A caller that shows this
    number must decide whether the series is long enough to deserve it.
    """
    if not portfolio_returns.returns:
        raise ValueError("Need return series")
    if periods_per_year <= 0:
        raise ValueError("periods_per_year must be positive")

    n = len(portfolio_returns.returns)
    returns = [float(r) for r in portfolio_returns.returns]

    # Compounded equity curve: the basis for total return and drawdown.
    curve = [Decimal(1)]
    for ret in portfolio_returns.returns:
        curve.append(curve[-1] * (Decimal(1) + ret))
    total_return = curve[-1] - Decimal(1)

    max_drawdown = Decimal(0)
    peak = curve[0]
    for value in curve:
        peak = max(peak, value)
        if peak > 0:
            max_drawdown = max(max_drawdown, (peak - value) / peak)

    # Geometric annualization; a total loss stays at -100%.
    growth = Decimal(1) + total_return
    if growth > 0:
        exponent = Decimal(periods_per_year) / Decimal(n)
        annualized_return = (growth.ln() * exponent).exp() - Decimal(1)
    else:
        annualized_return = Decimal(-1)

    if n > 1:
        variance = sum(
            (r - statistics.mean(returns)) ** 2 for r in returns
        ) / (n - 1)
        volatility = (
            Decimal(str(variance**0.5)) * Decimal(periods_per_year).sqrt()
        )
    else:
        volatility = Decimal(0)

    if volatility > 0:
        sharpe = (annualized_return - risk_free_rate) / volatility
    else:
        sharpe = Decimal(0)
    
    return PortfolioMetrics(
        total_return=total_return,
        total_drawdown=max_drawdown,
        annualized_return=annualized_return,
        volatility=volatility,
        sharpe_ratio=sharpe,
        n_periods=n,
    )


def warn_instability(
    correlations: Sequence[Correlation],
    threshold: Decimal = Decimal("0.5"),
) -> list[str]:
    """
    Warn about high correlations that may indicate concentration (51.2).
    """
    warnings = []
    for corr in correlations:
        if abs(corr.value) > threshold:
            warnings.append(
                f"High correlation ({abs(corr.value):.1%}) between "
                f"{corr.name_a} and {corr.name_b}. May indicate concentration."
            )
    return warnings


PORTFOLIO_WARNING = (
    "Portfolio metrics assume static weights. Real portfolio construction "
    "should consider transaction costs, rebalancing, and risk limits "
    "(Chapter 58). Correlations can change over time."
)

"""Feature engineering (ROADMAP.md chapter 47).

This module provides a catalog of features for machine learning and statistical
studies. Features are computed WITHOUT look-ahead bias - each feature value
is only computable from data available up to that point in time.

Important: Feature engineering is a research activity. Features must be
validated, documented, and tested for leakage before use.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Callable, Sequence


@dataclass(frozen=True)
class FeatureMetadata:
    """Complete documentation for a feature (Chapter 47.1)."""
    name: str
    formula: str
    source_data: str
    parameters: dict[str, str]
    version: str
    warmup_period: int
    interpretation: str
    limitations: str


@dataclass(frozen=True)
class Feature:
    """A computed feature with its metadata."""
    metadata: FeatureMetadata
    values: list[Decimal]


def compute_returns(closes: Sequence[Decimal], period: int = 1) -> list[Decimal]:
    """
    Compute returns (simple or log, Chapter 47.2).

    Each return is computed using only data available up to that point
    - no look-ahead bias.
    """
    if len(closes) < period + 1:
        return []

    returns = [Decimal(0)] * period  # Padding for warmup
    for i in range(period, len(closes)):
        if closes[i - period] == 0:
            returns.append(Decimal(0))
        else:
            ret = (closes[i] - closes[i - period]) / closes[i - period]
            returns.append(ret)

    return returns


def compute_volatility(closes: Sequence[Decimal], window: int = 20) -> list[Decimal]:
    """
    Compute rolling volatility (Chapter 47.2).

    Uses standard deviation of returns over a rolling window.
    No look-ahead: only uses data available up to each point.
    """
    if len(closes) < window + 1:
        return []

    returns = compute_returns(closes)
    if len(returns) < window:
        return [Decimal(0)] * len(returns)

    vol = [Decimal(0)] * window  # Padding
    for i in range(window, len(returns)):
        # Simple volatility: sqrt of variance
        window_returns = returns[i - window:i]
        mean_ret = sum(window_returns) / len(window_returns)
        variance = sum((r - mean_ret) ** 2 for r in window_returns) / len(window_returns)
        vol.append(variance.sqrt())

    return vol


def compute_momentum(closes: Sequence[Decimal], lookback: int = 10) -> list[Decimal]:
    """
    Compute momentum (price change over lookback period, Chapter 47.2).

    No look-ahead bias: uses only data up to each point.
    """
    if len(closes) < lookback + 1:
        return []

    momentum = [Decimal(0)] * lookback  # Padding
    for i in range(lookback, len(closes)):
        if closes[i - lookback] == 0:
            momentum.append(Decimal(0))
        else:
            mom = (closes[i] - closes[i - lookback]) / closes[i - lookback]
            momentum.append(mom)

    return momentum


def compute_rsi(closes: Sequence[Decimal], period: int = 14) -> list[Decimal]:
    """
    Compute Relative Strength Index (RSI, Chapter 47.2).

    Uses Welles Wilder's method. No look-ahead bias.
    """
    if len(closes) < period + 1:
        return []

    # Compute price changes
    changes = [closes[i] - closes[i - 1] for i in range(1, len(closes))]

    # Separate gains and losses
    gains = [max(c, 0) for c in changes]
    losses = [max(-c, 0) for c in changes]

    # Initial averages (first 'period' changes)
    if len(gains) < period:
        return [Decimal(0)] * len(closes)

    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period

    rsi = [Decimal(0)] * period  # Padding

    for i in range(period, len(changes)):
        # Smoothed average (Wilder's method)
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period

        if avg_loss == 0:
            rsi.append(Decimal(100))
        else:
            rs = avg_gain / avg_loss
            rsi.append(Decimal(100) - (Decimal(100) / (Decimal(1) + rs)))

    return rsi


def compute_ema(closes: Sequence[Decimal], period: int = 20) -> list[Decimal]:
    """
    Compute Exponential Moving Average (EMA, Chapter 47.2).

    Uses only past data - no look-ahead bias.
    """
    if not closes:
        return []

    multiplier = Decimal(2) / (period + 1)
    ema = [closes[0]]

    for i in range(1, len(closes)):
        new_ema = (closes[i] - ema[-1]) * multiplier + ema[-1]
        ema.append(new_ema)

    return ema


def compute_zscore(values: Sequence[Decimal], window: int = 20) -> list[Decimal]:
    """
    Compute rolling Z-score (Chapter 47.2).

    Measures how many standard deviations current value is from the rolling mean.
    """
    if len(values) < window:
        return [Decimal(0)] * len(values)

    zscores = [Decimal(0)] * (window - 1)  # Padding
    for i in range(window - 1, len(values)):
        window_values = values[i - window + 1:i + 1]
        mean_val = sum(window_values) / len(window_values)
        variance = sum((v - mean_val) ** 2 for v in window_values) / len(window_values)
        std = variance.sqrt() if variance > 0 else Decimal(1)
        zscore = (values[i] - mean_val) / std
        zscores.append(zscore)

    return zscores


# Feature catalog (47.1)
FEATURE_CATALOG: list[FeatureMetadata] = [
    FeatureMetadata(
        name="returns",
        formula="(close_t - close_{t-period}) / close_{t-period}",
        source_data="candle close prices",
        parameters={"period": "1"},
        version="1.0.0",
        warmup_period=1,
        interpretation="Percentage price change over the period",
        limitations="Sensitive to outliers; may have fat tails",
    ),
    FeatureMetadata(
        name="volatility",
        formula="std(returns_{t-window:t})",
        source_data="computed returns",
        parameters={"window": "20"},
        version="1.0.0",
        warmup_period=20,
        interpretation="Recent price variability",
        limitations="Assumes stationary volatility; may lag during regime changes",
    ),
    FeatureMetadata(
        name="momentum",
        formula="(close_t - close_{t-lookback}) / close_{t-lookback}",
        source_data="candle close prices",
        parameters={"lookback": "10"},
        version="1.0.0",
        warmup_period=10,
        interpretation="Price trend strength",
        limitations="May reverse quickly; not regime-adjusted",
    ),
    FeatureMetadata(
        name="rsi",
        formula="100 - 100/(1 + avg_gain/avg_loss)",
        source_data="candle close prices",
        parameters={"period": "14"},
        version="1.0.0",
        warmup_period=14,
        interpretation="Oscillator indicating overbought/oversold conditions",
        limitations="Can stay extreme in strong trends; false signals in ranging markets",
    ),
    FeatureMetadata(
        name="ema",
        formula="ema_{t-1} + multiplier * (close_t - ema_{t-1})",
        source_data="candle close prices",
        parameters={"period": "20"},
        version="1.0.0",
        warmup_period=20,
        interpretation="Smoothed price with exponential weighting",
        limitations="Lagging indicator; may miss sharp reversals",
    ),
    FeatureMetadata(
        name="zscore",
        formula="(value_t - mean_{t-window:t}) / std_{t-window:t}",
        source_data="any numeric series",
        parameters={"window": "20"},
        version="1.0.0",
        warmup_period=19,
        interpretation="Standardized distance from recent average",
        limitations="Assumes stationarity; breaks during structural changes",
    ),
]


FEATURE_REGISTRY: dict[str, Callable] = {
    "returns": compute_returns,
    "volatility": compute_volatility,
    "momentum": compute_momentum,
    "rsi": compute_rsi,
    "ema": compute_ema,
    "zscore": compute_zscore,
}


def get_feature_metadata(name: str) -> FeatureMetadata | None:
    """Get metadata for a feature by name (47.1)."""
    for m in FEATURE_CATALOG:
        if m.name == name:
            return m
    return None


def get_feature_function(name: str) -> Callable | None:
    """Get the computation function for a feature (47.2)."""
    return FEATURE_REGISTRY.get(name)


FEATURE_LEAKAGE_WARNING = (
    "All features in this module are computed without look-ahead bias. "
    "Each value uses only data available up to that point in time. "
    "However, when using features for machine learning, ensure proper "
    "time-series validation (Chapter 48.3) to avoid data leakage."
)
#: Portfolio-level backtesting (Chapter 51.1).
def portfolio_backtest(strategies, candles, initial_capital=Decimal("1000"), backtest_config=None):
    """Run backtest on a portfolio of strategies.
    Returns portfolio-level metrics and individual strategy results.
    """
    from crypto_trading_lab.backtesting.engine import run_backtest
    from crypto_trading_lab.backtesting.metrics import compute_performance
    
    results = []
    portfolio_metrics = {"total_return": Decimal(0), "trades": 0}
    
    for strategy in strategies:
        result = run_backtest(candles, strategy, backtest_config)
        perf = compute_performance(result)
        results.append({
            "strategy_name": strategy.name,
            "return_fraction": perf.return_fraction,
            "num_trades": len(result.trades),
            "sharpe_ratio": float(perf.risk.sharpe_ratio) if perf.risk.sharpe_ratio else None,
            "max_drawdown": float(perf.risk.max_drawdown),
        })
        portfolio_metrics["total_return"] += perf.return_fraction
        portfolio_metrics["trades"] += len(result.trades)
    
    portfolio_metrics["total_return"] /= len(strategies)
    return results, portfolio_metrics

#: Correlation calculation (Chapter 51.2).
def compute_asset_correlations(returns_list):
    """Calculate correlation matrix between multiple strategies/assets.
    (Chapter 51.2)
    """
    import scipy.stats
    n = len(returns_list)
    if n < 2:
        return {}
    
    # Convert each series to float for computation
    float_returns = [[float(r) for r in series] for series in returns_list]
    matrix = {}
    
    for i in range(n):
        for j in range(i + 1, n):
            try:
                r, _ = scipy.stats.pearsonr(float_returns[i], float_returns[j])
                matrix[(i, j)] = r
                matrix[(j, i)] = r
            except:
                matrix[(i, j)] = Decimal(0)
                matrix[(j, i)] = Decimal(0)
    
    return matrix

#: Portfolio metrics computation (Chapter 51.3).
def compute_portfolio_metrics(returns, risk_free_rate=Decimal("0")):
    """Compute portfolio-level metrics (Chapter 51.3).
    """
    from decimal import Decimal
    n = len(returns)
    if n == 0:
        return {"total_return": Decimal(0), "volatility": Decimal(0), 
                "sharpe_ratio": Decimal(0), "sortino_ratio": Decimal(0), 
                "max_drawdown": Decimal(0)}
    n = len(returns)
    total_return = sum(returns) / n
    
    if len(returns) > 1:
        mean_ret = sum(returns) / n
        variance = sum((r - mean_ret) ** 2 for r in returns) / (len(returns) - 1)
        volatility = Decimal(variance).sqrt()
    else:
        volatility = Decimal(0)
    
    excess_return = sum(returns) - risk_free_rate * n
    sharpe_ratio = Decimal(0)
    if volatility > Decimal(0):
        sharpe_ratio = excess_return / (volatility * Decimal(252).sqrt() / n)
    
    downside_returns = [r for r in returns if r < Decimal(0)]
    downside_dev = Decimal(0)
    if downside_returns:
        dd_sum = sum((r - Decimal(0)) ** 2 for r in downside_returns)
        downside_dev = (dd_sum / len(downside_returns)).sqrt()
    sortino_ratio = Decimal(0)
    if downside_dev > Decimal(0):
        excess_return = sum(returns) - risk_free_rate * n
        sortino_ratio = excess_return / downside_dev
    
    peak = returns[0]
    max_drawdown = Decimal(0)
    for r in returns:
        if r < peak:
            max_drawdown = min(max_drawdown, r - peak) if max_drawdown < Decimal(0) else r - peak
        peak = max(peak, r)
    
    return {
        "total_return": total_return,
        "volatility": volatility,
        "sharpe_ratio": sharpe_ratio,
        "sortino_ratio": sortino_ratio,
        "max_drawdown": max_drawdown,
    }

#: Correlation instability warning (Chapter 51.2).
WARN_CORRELATION_INSTABILITY = (
    "Correlation values may change over time. Correlations calculated "
    "on a limited window may not reflect the true long-term relationship. "
    "Always verify correlations over multiple windows and market regimes."
)

#: Portfolio concentration warning.
WARN_CONCENTRATION = (
    "High correlation between strategies or assets indicates "
    "concentration risk. A portfolio of correlated strategies/assets "
    "may suffer significant losses during market stress events."
)

#: Portfolio position sizing warning.
WARN_POSITION_SIZING = (
    "Position sizing must pass through the risk manager (Chapter 58). "
    "Never bypass risk limits per asset or per strategy."
)


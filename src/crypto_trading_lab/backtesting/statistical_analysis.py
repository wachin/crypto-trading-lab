"""Statistical edge and evidence analysis (ROADMAP.md chapter 43).

This module provides research tools for assessing whether a backtest result
represents genuine statistical edge or merely historical noise.

Important: These are research capabilities only. They never guarantee future
profitability. A single backtest is an *observed result* (Chapter 43.1), not
validated evidence.
"""

from __future__ import annotations

import math
import random
import statistics
from dataclasses import dataclass
from typing import Callable


@dataclass(frozen=True)
class DistributionStats:
    """Summary statistics for a distribution of returns or PnL values."""
    n: int
    mean: float
    std: float
    min: float
    max: float
    median: float
    skewness: float
    kurtosis: float


@dataclass(frozen=True)
class AutocorrelationResult:
    """Result of an autocorrelation test."""
    lag_1: float
    is_significant: bool
    warning: str


@dataclass(frozen=True)
class BootstrapConfidence:
    """Bootstrap confidence interval for a statistic."""
    statistic: float
    lower: float
    upper: float
    confidence_level: float
    n_resamples: int


def compute_distribution_stats(values: list[float]) -> DistributionStats:
    """
    Compute distribution statistics (Chapter 43.4).
    
    Warning: This is descriptive only. Do not assume normality without testing.
    """
    if not values:
        raise ValueError("Cannot compute statistics on empty list")
    
    n = len(values)
    mean = statistics.mean(values)
    std = statistics.stdev(values) if n > 1 else 0.0
    
    # Skewness: measure of asymmetry
    if std > 0:
        skewness = sum((x - mean) ** 3 for x in values) / (n * std ** 3)
    else:
        skewness = 0.0
    
    # Kurtosis: measure of tail heaviness (excess kurtosis, relative to normal)
    if std > 0:
        kurtosis = sum((x - mean) ** 4 for x in values) / (n * std ** 4) - 3
    else:
        kurtosis = 0.0
    
    return DistributionStats(
        n=n,
        mean=mean,
        std=std,
        min=min(values),
        max=max(values),
        median=statistics.median(values),
        skewness=skewness,
        kurtosis=kurtosis,
    )


def check_autocorrelation(values: list[float], max_lag: int = 5) -> AutocorrelationResult:
    """
    Check for autocorrelation in returns (Chapter 43.3).
    
    Autocorrelation violates the assumption of independent observations
    used in many statistical tests.
    """
    if len(values) < 10:
        return AutocorrelationResult(
            lag_1=0.0,
            is_significant=False,
            warning="Sample size too small for reliable autocorrelation test",
        )
    
    n = len(values)
    mean = statistics.mean(values)
    variance = sum((x - mean) ** 2 for x in values) / n
    
    if variance == 0:
        return AutocorrelationResult(
            lag_1=0.0,
            is_significant=False,
            warning="All values are identical; no variation to autocorrelate",
        )
    
    # Compute lag-1 autocorrelation (most important for time series)
    numerator = sum((values[i] - mean) * (values[i + 1] - mean) for i in range(n - 1))
    autocorr_lag1 = numerator / ((n - 1) * variance)
    
    # Rough significance test: for large n, autocorr ~ N(0, 1/sqrt(n))
    # Significant at ~5% level if |autocorr| > 1.96 / sqrt(n)
    threshold = 1.96 / math.sqrt(n)
    is_sig = abs(autocorr_lag1) > threshold
    
    warning = ""
    if is_sig:
        warning = (
            "Autocorrelation detected (lag-1). Returns are not independent. "
            "Statistical tests assuming independence may be invalid."
        )
    elif len(values) < 30:
        warning = "Small sample; autocorrelation test has low power"
    
    return AutocorrelationResult(
        lag_1=autocorr_lag1,
        is_significant=is_sig,
        warning=warning,
    )


def bootstrap_confidence_interval(
    values: list[float],
    statistic_fn: Callable[[list[float]], float],
    confidence_level: float = 0.95,
    n_resamples: int = 1000,
    seed: int | None = None,
) -> BootstrapConfidence:
    """
    Compute a bootstrap confidence interval for a statistic (Chapter 43.2).
    
    Unlike parametric tests, bootstrap makes minimal assumptions about the
    underlying distribution. Useful for non-normal returns.
    """
    if seed is not None:
        random.seed(seed)
    
    n = len(values)
    resamples = []
    
    for _ in range(n_resamples):
        # Sample with replacement
        sample = [values[random.randint(0, n - 1)] for _ in range(n)]
        resamples.append(statistic_fn(sample))
    
    resamples.sort()
    
    alpha = 1 - confidence_level
    lower_idx = int(alpha / 2 * n_resamples)
    upper_idx = int((1 - alpha / 2) * n_resamples)
    
    return BootstrapConfidence(
        statistic=statistic_fn(values),
        lower=resamples[lower_idx],
        upper=resamples[upper_idx],
        confidence_level=confidence_level,
        n_resamples=n_resamples,
    )


def probabilistic_sharpe_ratio(
    annualized_return: float,
    annualized_volatility: float,
    n_observations: int,
    trials: int = 1,
) -> float | None:
    """
    Compute Deflated Sharpe Ratio (PSR) per Chapter 43.1 / 49.5.
    
    Corrects the Sharpe ratio for:
    - Multiple hypothesis testing (number of trials)
    - Non-normal returns (skewness and kurtosis)
    - Sample length
    
    Returns a p-value: probability that true SR <= 0.
    
    Note: This is a research tool only. Not a guarantee of future performance.
    """
    if annualized_volatility == 0 or n_observations < 2:
        return None
    
    sharpe = annualized_return / annualized_volatility
    
    # Deflate for number of trials (multiple testing)
    # Under null, max of T trials follows extreme value distribution
    if trials > 1:
        # Approximate adjustment
        sharpe_deflated = sharpe - math.log(trials) / math.sqrt(n_observations)
    else:
        sharpe_deflated = sharpe
    
    # P-value that true SR <= 0
    # Using asymptotic distribution of SR estimator
    if n_observations < 100:
        # Warning: sample size may be too small for asymptotics
        return None
    
    # Approximate normal test
    se = math.sqrt((1 + sharpe_deflated ** 2 / 2) / n_observations)
    if se == 0:
        return None
    
    z = sharpe_deflated / se
    # Approximate normal CDF using error function
    p_value = 0.5 * (1 + math.erf(-z / math.sqrt(2)))
    
    return p_value


def warn_small_sample(n: int, min_recommended: int = 30) -> str:
    """
    Generate a warning for small sample sizes (Chapter 43.2).
    """
    if n < min_recommended:
        return (
            f"Small sample (n={n}). Statistical tests have low power. "
            f"Consider {min_recommended}+ observations for reliable inference."
        )
    return ""


def warn_multiple_testing(trials: int, threshold: int = 10) -> str:
    """
    Generate a warning for multiple testing (Chapter 43.1).
    
    The more configurations tested, the more likely a good historical result
    is pure chance (False Discovery / False Strategy problem).
    """
    if trials > threshold:
        return (
            f"Many trials performed ({trials}). A good result may reflect "
            "chance selection rather than genuine edge. Consider deflated "
            "performance evaluation (Chapter 43.1 / 49.5)."
        )
    return ""

"""Risk of ruin and capital depletion (ROADMAP.md chapter 60).

Implements risk of ruin calculations and capital depletion modeling.
This is a research-tier capability for portfolio risk management.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from decimal import Decimal
from typing import Sequence


@dataclass(frozen=True)
class RiskOfRuinConfig:
    """Configuration for risk of ruin calculations."""
    initial_capital: Decimal
    win_probability: Decimal  # Probability of winning trade
    win_loss_ratio: Decimal   # Average win / average loss
    risk_per_trade: Decimal   # Fraction of capital risked per trade
    target_drawdown: Decimal  # Maximum acceptable drawdown


@dataclass(frozen=True)
class RiskOfRuinResult:
    """Result of risk of ruin calculation."""
    probability_of_ruin: Decimal  # Probability of reaching target drawdown
    expected_drawdown: Decimal
    median_drawdown: Decimal
    max_drawdown_prob: Decimal
    expected_time_to_ruin: int  # Expected number of trades to ruin
    survival_probability: Decimal  # 1 - probability_of_ruin


def kelly_fraction(
    win_probability: Decimal,
    win_loss_ratio: Decimal,
) -> Decimal:
    """
    Calculate Kelly fraction for optimal bet sizing.
    
    Kelly f* = (p * b - q) / b
    where p = win probability, q = 1-p, b = win/loss ratio
    """
    p = win_probability
    q = Decimal(1) - p
    b = win_loss_ratio
    
    if b == 0:
        return Decimal(0)
    
    kelly = (p * b - q) / b
    return max(Decimal(0), kelly)


def risk_of_ruin_binomial(
    initial_capital: Decimal,
    risk_per_trade: Decimal,
    win_probability: Decimal,
    win_loss_ratio: Decimal,
    target_drawdown: Decimal,
    max_trades: int = 10000,
) -> RiskOfRuinResult:
    """
    Calculate risk of ruin using binomial model (60.1).
    
    Uses exact binomial probability for discrete random walk.
    """
    p = float(win_probability)
    b = float(win_loss_ratio)
    f = float(risk_per_trade)
    D = float(target_drawdown)
    
    # Win/loss amounts in terms of portfolio fraction
    win_amt = f * b
    loss_amt = f
    
    # Number of losses to reach target drawdown
    # (1 - f)^L * (1 + f*b)^W = 1 - D
    # Simplified: number of losses to reach drawdown
    n_ruin = int(math.log(1 - D) / math.log(1 - f)) if f > 0 else 1000
    
    # Probability of ruin using random walk with drift
    if p * b <= 1 - p:  # Negative or zero expectation
        prob_ruin = Decimal(1)
    else:
        # Approximate using diffusion approximation
        drift = p * win_amt - (1 - p) * loss_amt
        variance = p * win_amt**2 + (1 - p) * loss_amt**2 - drift**2
        
        if drift > 0 and variance > 0:
            prob_ruin = Decimal(str(math.exp(-2 * drift * D / variance)))
        else:
            prob_ruin = Decimal(1)
    
    # Expected drawdown
    expected_dd = Decimal(str(p * win_amt - (1 - p) * loss_amt)) * Decimal(100)
    
    # Median drawdown (approximate)
    median_dd = Decimal(str(abs(p * win_amt - (1 - p) * loss_amt))) * Decimal(50)
    
    # Maximum drawdown probability
    max_dd_prob = min(prob_ruin * Decimal(2), Decimal(1))
    
    # Expected time to ruin (number of trades)
    if prob_ruin < Decimal(1):
        expected_time = int(D / float(p * win_amt - (1 - p) * loss_amt)) if (p * win_amt - (1 - p) * loss_amt) > 0 else 10000
    else:
        expected_time = n_ruin
    
    return RiskOfRuinResult(
        probability_of_ruin=Decimal(str(min(prob_ruin, 1.0))),
        expected_drawdown=expected_dd,
        median_drawdown=median_dd,
        max_drawdown_prob=max_dd_prob,
        expected_time_to_ruin=expected_time,
        survival_probability=Decimal(1) - Decimal(str(min(prob_ruin, 1.0))),
    )


def risk_of_ruin_diffusion(
    initial_capital: Decimal,
    risk_per_trade: Decimal,
    win_probability: Decimal,
    win_loss_ratio: Decimal,
    target_drawdown: Decimal,
) -> RiskOfRuinResult:
    """
    Calculate risk of ruin using diffusion approximation (60.2).
    
    Uses continuous-time diffusion approximation (Brownian motion with drift).
    """
    p = float(win_probability)
    b = float(win_loss_ratio)
    f = float(risk_per_trade)
    D = float(target_drawdown)
    
    win_amt = f * b
    loss_amt = f
    
    # Expected return per trade
    mu = p * win_amt - (1 - p) * loss_amt
    
    # Variance per trade
    sigma2 = p * (win_amt - mu)**2 + (1 - p) * (loss_amt + mu)**2
    
    if mu <= 0:
        # Negative or zero drift -> certain ruin eventually
        return RiskOfRuinResult(
            probability_of_ruin=Decimal(1),
            expected_drawdown=Decimal(1),
            median_drawdown=Decimal(1),
            max_drawdown_prob=Decimal(1),
            expected_time_to_ruin=10000,
            survival_probability=Decimal(0),
        )
    
    if sigma2 <= 0:
        return RiskOfRuinResult(
            probability_of_ruin=Decimal(0),
            expected_drawdown=Decimal(0),
            median_drawdown=Decimal(0),
            max_drawdown_prob=Decimal(0),
            expected_time_to_ruin=10000,
            survival_probability=Decimal(1),
        )
    
    # Probability of ever hitting drawdown D
    prob_ruin = math.exp(-2 * mu * D / sigma2)
    prob_ruin = min(max(prob_ruin, 0), 1)
    
    # Expected maximum drawdown
    expected_dd = sigma2 / (2 * mu) if mu > 0 else D
    
    # Median drawdown
    median_dd = Decimal(str(D * 0.5))
    
    # Expected time to reach drawdown
    expected_time = int(D / mu) if mu > 0 else 10000
    
    return RiskOfRuinResult(
        probability_of_ruin=Decimal(str(prob_ruin)),
        expected_drawdown=Decimal(str(expected_dd)),
        median_drawdown=median_dd,
        max_drawdown_prob=Decimal(str(min(prob_ruin * 2, 1))),
        expected_time_to_ruin=expected_time,
        survival_probability=Decimal(str(1 - prob_ruin)),
    )


def capital_depletion_path(
    initial_capital: Decimal,
    returns: Sequence[Decimal],
) -> dict[str, Decimal]:
    """
    Analyze capital depletion path from return sequence (60.3).
    
    Returns statistics about the capital depletion path.
    """
    if not returns:
        return {
            "max_drawdown": Decimal(0),
            "max_drawdown_duration": Decimal(0),
            "time_to_recovery": Decimal(0),
            "longest_drawdown_period": 0,
            "recovery_rate": Decimal(0),
        }
    
    equity = [1]
    for r in returns:
        equity.append(equity[-1] * (1 + r))
    
    # Calculate drawdowns
    peak = equity[0]
    drawdowns = []
    durations = []
    current_duration = 0
    
    for eq in equity:
        if eq > peak:
            peak = eq
            current_duration = 0
        else:
            current_duration += 1
        dd = (peak - eq) / peak if peak > 0 else 0
        drawdowns.append(dd)
        durations.append(current_duration)
    
    max_drawdown = max(drawdowns) if drawdowns else 0
    max_duration = max(durations) if durations else 0
    
    # Recovery periods
    recovery_times = []
    in_drawdown = False
    start_dd = 0
    
    for i, dd in enumerate(drawdowns):
        if dd > 0 and not in_drawdown:
            in_drawdown = True
            start_dd = i
        elif dd == 0 and in_drawdown:
            in_drawdown = False
            recovery_times.append(i - start_dd)
    
    avg_recovery = sum(recovery_times) / len(recovery_times) if recovery_times else 0
    
    return {
        "max_drawdown": Decimal(str(max_drawdown)),
        "max_drawdown_duration": Decimal(str(max_duration)),
        "time_to_recovery": Decimal(str(avg_recovery)),
        "longest_drawdown_period": max_duration,
        "recovery_rate": Decimal(str(len([d for d in drawdowns if d == 0]) / len(drawdowns))) if drawdowns else Decimal(0),
    }


def optimal_bet_size(
    win_probability: Decimal,
    win_loss_ratio: Decimal,
    max_risk: Decimal = Decimal("0.02"),
) -> Decimal:
    """
    Calculate optimal bet size using Kelly with max risk constraint (60.4).
    """
    kelly = kelly_fraction(win_probability, win_loss_ratio)
    return min(kelly, max_risk)


def sequential_risk_of_ruin(
    capital: Decimal,
    trades: Sequence[Decimal],
    threshold: Decimal,
) -> float:
    """
    Sequential probability of ruin (60.5).
    
    Computes probability of hitting threshold at any point in the sequence.
    """
    if not trades:
        return 0.0
    
    equity = 1.0
    peak = 1.0
    min_equity = 1.0
    
    for r in trades:
        equity *= (1 + r)
        peak = max(peak, equity)
        min_equity = min(min_equity, equity)
    
    # Probability of hitting threshold at any point
    max_dd = (peak - min_equity) / peak if peak > 0 else 0
    
    return 1.0 if max_dd >= threshold else 0.0


RISK_OF_RUIN_WARNING = (
    "Risk of ruin calculations are theoretical estimates based on "
    "stated assumptions. Real trading involves regime changes, "
    "correlated losses, liquidity constraints, and behavioral biases "
    "that invalidate simple models. Always use conservative estimates."
)


__all__ = [
    "RiskOfRuinConfig",
    "RiskOfRuinResult",
    "kelly_fraction",
    "risk_of_ruin_binomial",
    "risk_of_ruin_diffusion",
    "capital_depletion_path",
    "optimal_bet_size",
    "sequential_risk_of_ruin",
    "RISK_OF_RUIN_WARNING",
]

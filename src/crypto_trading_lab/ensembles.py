"""Ensemble methods (ROADMAP.md chapter 50).

Ensembles combine multiple strategy signals to improve robustness.
This is a research capability, not an MVP requirement.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from typing import Callable, Sequence


class CombinationMethod(Enum):
    """How to combine strategy signals (50.1)."""
    MAJORITY_VOTE = "majority_vote"
    AVERAGE = "average"
    WEIGHTED = "weighted"


@dataclass(frozen=True)
class StrategySignal:
    """Signal from a single strategy."""
    strategy_name: str
    strategy_version: str
    signal: int  # +1 = buy, -1 = sell, 0 = neutral
    confidence: Decimal  # 0 to 1
    parameters: dict[str, str]


@dataclass(frozen=True)
class EnsembleSignal:
    """Combined signal from multiple strategies."""
    method: CombinationMethod
    members: list[str]
    signal: int
    confidence: Decimal
    member_signals: list[StrategySignal]
    warnings: list[str]


def combine_signals_majORITY(
    signals: Sequence[StrategySignal],
    min_members: int = 2,
) -> EnsembleSignal:
    """
    Combine signals by majority vote (50.1).
    """
    warnings = []
    if len(signals) < min_members:
        warnings.append(
            f"Few members ({len(signals)}). Ensemble may not be robust."
        )

    buy_count = sum(1 for s in signals if s.signal == 1)
    sell_count = sum(1 for s in signals if s.signal == -1)
    neutral_count = len(signals) - buy_count - sell_count

    if buy_count > sell_count:
        signal = 1
    elif sell_count > buy_count:
        signal = -1
    else:
        signal = 0

    confidence = max(buy_count, sell_count) / Decimal(len(signals)) if signals else Decimal(0)

    member_names = [s.strategy_name for s in signals]

    return EnsembleSignal(
        method=CombinationMethod.MAJORITY_VOTE,
        members=member_names,
        signal=signal,
        confidence=confidence,
        member_signals=list(signals),
        warnings=warnings,
    )


def combine_signals_average(
    signals: Sequence[StrategySignal],
) -> EnsembleSignal:
    """
    Combine signals by averaging (50.1).
    """
    if not signals:
        return EnsembleSignal(
            method=CombinationMethod.AVERAGE,
            members=[],
            signal=0,
            confidence=Decimal(0),
            member_signals=[],
            warnings=["No signals to combine."],
        )

    avg_signal = sum(s.signal for s in signals) / Decimal(len(signals))
    signal = round(avg_signal)
    confidence = abs(avg_signal)

    member_names = [s.strategy_name for s in signals]

    return EnsembleSignal(
        method=CombinationMethod.AVERAGE,
        members=member_names,
        signal=signal,
        confidence=confidence,
        member_signals=list(signals),
        warnings=[],
    )


def combine_signals_weighted(
    signals: Sequence[StrategySignal],
    weights: Sequence[Decimal] | None = None,
) -> EnsembleSignal:
    """
    Combine signals by weighted average (50.1).
    """
    if not signals:
        return EnsembleSignal(
            method=CombinationMethod.WEIGHTED,
            members=[],
            signal=0,
            confidence=Decimal(0),
            member_signals=[],
            warnings=["No signals to combine."],
        )

    if weights is None:
        weights = [Decimal(1)] * len(signals)
    
    if len(weights) != len(signals):
        raise ValueError("Weights length must match signals length")

    total_weight = sum(weights)
    if total_weight == 0:
        total_weight = Decimal(1)

    weighted_sum = sum(
        Decimal(s.signal) * w for s, w in zip(signals, weights)
    )
    avg_signal = weighted_sum / total_weight
    signal = round(avg_signal)

    confidence = abs(avg_signal)

    member_names = [s.strategy_name for s in signals]

    return EnsembleSignal(
        method=CombinationMethod.WEIGHTED,
        members=member_names,
        signal=signal,
        confidence=confidence,
        member_signals=list(signals),
        warnings=[],
    )


ENSEMBLE_WARNING = (
    "Ensembles combine multiple strategy signals. They may improve "
    "robustness but add complexity. Always compare against the best "
    "member and validate out-of-sample."
)

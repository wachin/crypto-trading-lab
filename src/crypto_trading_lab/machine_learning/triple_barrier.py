"""Triple-barrier labeling (ROADMAP.md chapter 49.2).

Triple-barrier labeling assigns labels based on which "barrier" is hit first:
- Upward barrier (take-profit)
- Downward barrier (stop-loss)
- Time barrier (maximum holding period)

This is a research-tier capability for supervised ML label generation.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Sequence


@dataclass(frozen=True)
class TripleBarrierConfig:
    """Configuration for triple-barrier labeling (49.2)."""
    vertical_barrier: int  # Number of candles
    take_profit: Decimal  # Percentage
    stop_loss: Decimal  # Percentage (absolute value)


@dataclass(frozen=True)
class TripleBarrierLabel:
    """Result of triple-barrier labeling."""
    label: int  # +1 = take-profit hit, -1 = stop-loss hit, 0 = time barrier
    return_value: Decimal  # Actual return at barrier
    barrier_hit: int  # +1 (up), -1 (down), 0 (time)
    holding_period: int  # Candles held


def apply_triple_barrier(
    candles: Sequence[dict],  # {open, high, low, close, timestamp}
    config: TripleBarrierConfig,
    start_idx: int = 0,
) -> list[TripleBarrierLabel]:
    """
    Apply triple-barrier labeling to a sequence of candles (49.2).
    
    For each starting point, track returns until one of the barriers is hit.
    No look-ahead: only uses data from start_idx onwards.
    
    Returns: List of labels for each starting point.
    """
    labels = []
    
    for i in range(start_idx, len(candles)):
        start_price = candles[i]["close"]
        if start_price == 0:
            labels.append(TripleBarrierLabel(
                label=0,
                return_value=Decimal(0),
                barrier_hit=0,
                holding_period=config.vertical_barrier,
            ))
            continue
        
        # Track return at each step
        best_label = None
        best_return = Decimal(0)
        best_barrier = 0
        holding = 0
        
        for t in range(i + 1, min(i + config.vertical_barrier + 1, len(candles))):
            # Check high/low paths for early exit (can exit before close)
            current_high = candles[t]["high"]
            current_low = candles[t]["low"]
            holding = t - i
            
            # Check take-profit (high path)
            if current_high >= start_price * (Decimal(1) + config.take_profit):
                best_label = 1
                best_return = (current_high - start_price) / start_price
                best_barrier = 1
                break
            
            # Check stop-loss (low path)
            if current_low <= start_price * (Decimal(1) - config.stop_loss):
                best_label = -1
                best_return = (current_low - start_price) / start_price
                best_barrier = -1
                break
        
            # If no barrier hit, use vertical (time) barrier
            if best_label is None:
                best_label = 0
                if i + config.vertical_barrier < len(candles):
                    best_return = (candles[i + config.vertical_barrier]["close"] - start_price) / start_price
                else:
                    best_return = Decimal(0)
                best_barrier = 0
                holding = config.vertical_barrier
        
        labels.append(TripleBarrierLabel(
            label=best_label,
            return_value=best_return,
            barrier_hit=best_barrier,
            holding_period=holding,
        ))
    
    return labels


def compute_label_statistics(
    labels: Sequence[TripleBarrierLabel],
) -> dict[str, Decimal]:
    """
    Compute statistics for triple-barrier labels (49.2).
    """
    if not labels:
        return {
            "total": Decimal(0),
            "take_profit": Decimal(0),
            "stop_loss": Decimal(0),
            "time_barrier": Decimal(0),
            "avg_return": Decimal(0),
            "avg_holding_period": Decimal(0),
        }
    
    n = len(labels)
    take_profit = sum(1 for l in labels if l.barrier_hit == 1)
    stop_loss = sum(1 for l in labels if l.barrier_hit == -1)
    time_barrier = n - take_profit - stop_loss
    
    avg_return = sum(l.return_value for l in labels) / Decimal(n)
    avg_holding = sum(l.holding_period for l in labels) / Decimal(n)
    
    return {
        "total": Decimal(n),
        "take_profit": Decimal(take_profit),
        "stop_loss": Decimal(stop_loss),
        "time_barrier": Decimal(time_barrier),
        "avg_return": avg_return,
        "avg_holding_period": avg_holding,
    }


TRIPLE_BARRIER_WARNING = (
    "Triple-barrier labeling is a research capability. Labels are computed "
    "without look-ahead, but feature computation for training must still "
    "avoid future information. See Chapter 49.2 for full specifications."
)

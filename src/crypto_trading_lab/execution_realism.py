"""Execution realism (ROADMAP.md chapter 56).

Models realistic execution effects: latency, slippage, partial fills,
market impact, and order book dynamics. This is a research-tier capability.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from typing import Sequence


class OrderType(Enum):
    """Order type enumeration."""
    MARKET = "market"
    LIMIT = "limit"
    STOP_MARKET = "stop_market"
    STOP_LIMIT = "stop_limit"


class FillType(Enum):
    """Fill type enumeration."""
    FULL = "full"
    PARTIAL = "partial"
    REJECTED = "rejected"


@dataclass(frozen=True)
class OrderBookLevel:
    """Single order book level."""
    price: Decimal
    quantity: Decimal


@dataclass(frozen=True)
class OrderBookSnapshot:
    """Order book snapshot at a point in time."""
    timestamp: int
    bids: Sequence[OrderBookLevel]
    asks: Sequence[OrderBookLevel]
    
    def spread(self) -> Decimal:
        """Current bid-ask spread."""
        if not self.bids or not self.asks:
            return Decimal(0)
        return self.asks[0].price - self.bids[0].price
    
    def mid_price(self) -> Decimal:
        """Mid price."""
        if not self.bids or not self.asks:
            return Decimal(0)
        return (self.bids[0].price + self.asks[0].price) / Decimal(2)
    
    def volume_at_price(self, price: Decimal, side: str) -> Decimal:
        """Get volume available at a specific price."""
        levels = self.bids if side == "buy" else self.asks
        for level in levels:
            if level.price == price:
                return level.quantity
        return Decimal(0)


@dataclass(frozen=True)
class ExecutionConfig:
    """Execution realism configuration."""
    # Latency
    base_latency_ms: int = 50  # Base network/exchange latency
    latency_std_ms: int = 10   # Latency standard deviation
    
    # Slippage
    base_slippage_bps: int = 5  # Base slippage in basis points
    slippage_factor: Decimal = Decimal("1.0")  # Volatility multiplier
    
    # Market impact
    impact_factor: Decimal = Decimal("0.1")  # Price impact per 1% ADV
    adv_window: int = 20  # Average daily volume window
    
    # Partial fills
    min_fill_rate: Decimal = Decimal("0.1")  # Minimum fill rate
    max_order_size_frac: Decimal = Decimal("0.1")  # Max order as fraction of ADV
    
    # Queue position for limit orders
    queue_position_penalty: Decimal = Decimal("0.01")  # Price penalty per queue position


@dataclass(frozen=True)
class ExecutionResult:
    """Result of order execution simulation."""
    fill_type: FillType
    filled_quantity: Decimal
    average_price: Decimal
    slippage_bps: Decimal
    latency_ms: int
    market_impact_bps: Decimal
    fees: Decimal
    partial_fills: list[tuple[Decimal, Decimal]]  # (quantity, price)


def simulate_latency(config: ExecutionConfig) -> int:
    """Simulate network/exchange latency (56.1)."""
    base = config.base_latency_ms
    std = config.latency_std_ms
    latency = max(1, int(random.gauss(base, std)))
    return latency


def calculate_slippage(
    order_quantity: Decimal,
    order_side: str,
    order_book: OrderBookSnapshot,
    config: ExecutionConfig,
    adv: Decimal,
) -> tuple[Decimal, Decimal]:
    """
    Calculate expected slippage (56.2).
    
    Returns: (average_price, slippage_bps)
    """
    # Base slippage from bid-ask spread
    spread = order_book.spread()
    mid = order_book.mid_price()
    if mid == 0:
        return Decimal(0), Decimal(0)
    
    spread_bps = (spread / mid) * Decimal(10000)
    
    # Volume-based slippage (market impact)
    if adv > 0:
        participation_rate = order_quantity / adv
        impact_bps = config.impact_factor * Decimal(str(participation_rate)) * Decimal(10000)
    else:
        impact_bps = Decimal(0)
    
    # Random component
    random_bps = Decimal(random.uniform(-config.base_slippage_bps, config.base_slippage_bps))
    
    total_slippage = spread_bps / 2 + impact_bps + random_bps
    
    # Adjust price based on side
    if order_side == "buy":
        execution_price = mid * (Decimal(1) + total_slippage / Decimal(10000))
    else:
        execution_price = mid * (Decimal(1) - total_slippage / Decimal(10000))
    
    return execution_price, max(total_slippage, Decimal(0))


def calculate_market_impact(
    order_quantity: Decimal,
    adv: Decimal,
    config: ExecutionConfig,
) -> Decimal:
    """Calculate market impact in basis points (56.3)."""
    if adv <= 0:
        return Decimal(0)
    participation = order_quantity / adv
    return config.impact_factor * Decimal(str(participation)) * Decimal(10000)


def simulate_partial_fill(
    order_quantity: Decimal,
    order_side: str,
    order_book: OrderBookSnapshot,
    config: ExecutionConfig,
) -> tuple[FillType, Decimal, list[tuple[Decimal, Decimal]]]:
    """
    Simulate partial fills based on order book depth (56.4).
    
    Returns: (fill_type, filled_quantity, fills_list)
    """
    # Check available liquidity
    if order_side == "buy":
        available = sum(level.quantity for level in order_book.asks)
    else:
        available = sum(level.quantity for level in order_book.bids)
    
    if available <= 0:
        return FillType.REJECTED, Decimal(0), []
    
    fillable = min(order_quantity, available)
    
    # Check if fully fillable
    min_fill = order_quantity * config.min_fill_rate
    if fillable < min_fill:
        return FillType.REJECTED, Decimal(0), []
    
    # Simulate partial fills at different price levels
    fills = []
    remaining = fillable
    
    if order_side == "buy":
        levels = order_book.asks
    else:
        levels = order_book.bids
    
    for level in levels:
        if remaining <= 0:
            break
        fill_qty = min(remaining, level.quantity)
        fills.append((fill_qty, level.price))
        remaining -= fill_qty
    
    filled = sum(q for q, _ in fills)
    
    if filled >= order_quantity * Decimal("0.99"):
        fill_type = FillType.FULL
    elif filled >= order_quantity * config.min_fill_rate:
        fill_type = FillType.PARTIAL
    else:
        fill_type = FillType.REJECTED
    
    return fill_type, filled, fills


def simulate_execution(
    order_quantity: Decimal,
    order_side: str,
    order_type: OrderType,
    order_price: Decimal | None,
    order_book: OrderBookSnapshot,
    config: ExecutionConfig,
    adv: Decimal,
    fees_bps: Decimal = Decimal("10"),  # 10 bps default fee
) -> ExecutionResult:
    """
    Simulate full order execution with realism (56).
    
    Args:
        order_quantity: Order quantity
        order_side: "buy" or "sell"
        order_type: Order type
        order_price: Limit price (for limit orders)
        order_book: Current order book snapshot
        config: Execution configuration
        adv: Average daily volume
        fees_bps: Fee in basis points
    
    Returns:
        ExecutionResult with fill details
    """
    # Simulate latency
    latency = simulate_latency(config)
    
    # Handle limit orders - check if price is reachable
    if order_type in (OrderType.LIMIT, OrderType.STOP_LIMIT) and order_price:
        mid = order_book.mid_price()
        if order_side == "buy" and order_price < order_book.asks[0].price:
            # Limit buy below ask - may not fill
            return ExecutionResult(
                fill_type=FillType.REJECTED,
                filled_quantity=Decimal(0),
                average_price=Decimal(0),
                slippage_bps=Decimal(0),
                latency_ms=latency,
                market_impact_bps=Decimal(0),
                fees=Decimal(0),
                partial_fills=[],
            )
        elif order_side == "sell" and order_price > order_book.bids[0].price:
            # Limit sell above bid - may not fill
            return ExecutionResult(
                fill_type=FillType.REJECTED,
                filled_quantity=Decimal(0),
                average_price=Decimal(0),
                slippage_bps=Decimal(0),
                latency_ms=latency,
                market_impact_bps=Decimal(0),
                fees=Decimal(0),
                partial_fills=[],
            )
    
    # Calculate slippage
    exec_price, slippage = calculate_slippage(
        order_quantity, "buy" if order_side == "buy" else "sell",
        order_book, config, adv
    )
    
    # Market impact
    market_impact = calculate_market_impact(order_quantity, adv, config)
    
    # Simulate partial fills
    fill_type, filled_qty, partial_fills = simulate_partial_fill(
        order_quantity, "buy" if order_side == "buy" else "sell", 
        order_book, config
    )
    
    if fill_type == FillType.REJECTED:
        return ExecutionResult(
            fill_type=FillType.REJECTED,
            filled_quantity=Decimal(0),
            average_price=Decimal(0),
            slippage_bps=Decimal(0),
            latency_ms=latency,
            market_impact_bps=Decimal(0),
            fees=Decimal(0),
            partial_fills=[],
        )
    
    # Calculate average price from partial fills
    if partial_fills:
        total_value = sum(q * p for q, p in partial_fills)
        avg_price = total_value / sum(q for q, _ in partial_fills)
    else:
        avg_price = order_book.mid_price()
    
    # Calculate fees
    fees = (sum(q * p for q, p in partial_fills) * fees_bps / Decimal(10000))
    
    return ExecutionResult(
        fill_type=fill_type,
        filled_quantity=sum(q for q, _ in partial_fills),
        average_price=avg_price,
        slippage_bps=Decimal(str(market_impact)) if market_impact > 0 else Decimal(0),
        latency_ms=latency,
        market_impact_bps=market_impact,
        fees=fees,
        partial_fills=partial_fills,
    )


EXECUTION_REALISM_WARNING = (
    "Execution simulation is a model, not reality. "
    "Real execution involves: adverse selection, HFT competition, "
    "queue position uncertainty, exchange matching engine specifics, "
    "and regulatory constraints. Always validate with live data."
)


__all__ = [
    "OrderType",
    "FillType",
    "OrderBookLevel",
    "OrderBookSnapshot",
    "ExecutionConfig",
    "ExecutionResult",
    "simulate_latency",
    "calculate_slippage",
    "calculate_market_impact",
    "simulate_partial_fill",
    "simulate_execution",
    "EXECUTION_REALISM_WARNING",
]

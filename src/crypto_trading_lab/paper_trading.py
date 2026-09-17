"""Paper trading simulation (ROADMAP.md chapter 57).

Paper trading simulates the complete trading workflow with simulated money
while using real or replayed market data.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
from typing import Optional


class OrderSide(Enum):
    BUY = "buy"
    SELL = "sell"


class OrderStatus(Enum):
    PENDING = "pending"
    FILLED = "filled"
    PARTIALLY_FILLED = "partially_filled"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


@dataclass
class PaperAccount:
    """Simulated trading account (57.1)."""
    initial_balance: Decimal
    balances: dict[str, Decimal] = field(default_factory=dict)
    positions: dict[str, Decimal] = field(default_factory=dict)
    history: list[dict] = field(default_factory=list)
    realized_pnl: Decimal = Decimal(0)
    unrealized_pnl: Decimal = Decimal(0)
    total_fees: Decimal = Decimal(0)
    total_slippage: Decimal = Decimal(0)
    
    def __post_init__(self):
        if not self.balances:
            self.balances["USDT"] = self.initial_balance
    
    def get_balance(self, asset: str) -> Decimal:
        return self.balances.get(asset, Decimal(0))
    
    def get_position(self, symbol: str) -> Decimal:
        return self.positions.get(symbol, Decimal(0))
    
    def update_balance(self, asset: str, delta: Decimal) -> None:
        current = self.balances.get(asset, Decimal(0))
        self.balances[asset] = current + delta
        self.history.append({
            "type": "balance_change",
            "asset": asset,
            "delta": str(delta),
            "balance": str(self.balances[asset]),
        })
    
    def update_position(self, symbol: str, delta: Decimal) -> None:
        current = self.positions.get(symbol, Decimal(0))
        self.positions[symbol] = current + delta
        self.history.append({
            "type": "position_change",
            "symbol": symbol,
            "delta": str(delta),
            "position": str(self.positions[symbol]),
        })
    
    def record_pnl(self, realized: Decimal, unrealized: Decimal) -> None:
        self.realized_pnl += realized
        self.unrealized_pnl += unrealized


@dataclass
class PaperOrder:
    """Simulated order (57.2)."""
    order_id: str
    symbol: str
    side: OrderSide
    quantity: Decimal
    price: Optional[Decimal]
    status: OrderStatus = OrderStatus.PENDING
    filled_quantity: Decimal = Decimal(0)
    fill_price: Optional[Decimal] = None
    reject_reason: Optional[str] = None
    latency_ms: int = 0


class PaperExecutionSimulator:
    """Simulates order execution with latency and slippage (57.2)."""
    
    def __init__(
        self,
        latency_ms: int = 100,
        slippage_fraction: Decimal = Decimal("0.0005"),
    ):
        self.latency_ms = latency_ms
        self.slippage_fraction = slippage_fraction
        self._order_counter = 0
    
    def simulate_order(
        self,
        order: PaperOrder,
        current_price: Decimal,
    ) -> PaperOrder:
        """
        Simulate order execution with latency and slippage.
        """
        self._order_counter += 1
        
        # Simulate latency
        order.latency_ms = self.latency_ms
        
        # Apply slippage
        if order.price is None:
            # Market order: execution at current price with slippage
            if order.side == OrderSide.BUY:
                execution_price = current_price * (Decimal(1) + self.slippage_fraction)
            else:
                execution_price = current_price * (Decimal(1) - self.slippage_fraction)
        else:
            # Limit order: check if price condition is met
            if order.side == OrderSide.BUY and current_price > order.price:
                order.status = OrderStatus.REJECTED
                order.reject_reason = "Price above limit"
                return order
            elif order.side == OrderSide.SELL and current_price < order.price:
                order.status = OrderStatus.REJECTED
                order.reject_reason = "Price below limit"
                return order
            execution_price = current_price
        
        # Fill the order
        order.status = OrderStatus.FILLED
        order.filled_quantity = order.quantity
        order.fill_price = execution_price
        
        return order


class PaperTradingEngine:
    """
    Main paper trading engine (57.3).
    
    Reuses the same components as backtesting for consistency.
    """
    
    def __init__(
        self,
        account: PaperAccount,
        execution: PaperExecutionSimulator | None = None,
    ):
        self.account = account
        self.execution = execution or PaperExecutionSimulator()
    
    def execute_order(
        self,
        order: PaperOrder,
        current_price: Decimal,
    ) -> tuple[PaperOrder, Decimal]:
        """
        Execute an order in the paper account.
        
        Returns: (modified order, fee charged)
        """
        # Simulate execution
        order = self.execution.simulate_order(order, current_price)
        
        if order.status != OrderStatus.FILLED:
            return order, Decimal(0)
        
        # Calculate fee
        order_value = order.filled_quantity * (order.fill_price or Decimal(0))
        fee = order_value * Decimal("0.001")  # 0.1% fee
        
        # Update account
        symbol_parts = order.symbol.split("/")
        base = symbol_parts[0] if len(symbol_parts) >= 1 else "BTC"
        quote = symbol_parts[1] if len(symbol_parts) >= 2 else "USDT"
        
        if order.side == OrderSide.BUY:
            # Pay quote currency, receive base currency
            self.account.update_balance(quote, -order_value - fee)
            self.account.update_position(base, order.filled_quantity)
        else:
            # Receive quote currency, pay base currency
            self.account.update_balance(quote, order_value - fee)
            self.account.update_position(base, -order.filled_quantity)
        
        # Record slippage cost
        if order.fill_price and order.price is None:
            spread_cost = abs(order.fill_price - current_price) * order.filled_quantity
            self.account.total_slippage += spread_cost
        
        self.account.total_fees += fee
        
        self.account.history.append({
            "type": "order_filled",
            "order_id": order.order_id,
            "symbol": order.symbol,
            "side": order.side.value,
            "quantity": str(order.filled_quantity),
            "price": str(order.fill_price),
            "fee": str(fee),
        })
        
        return order, fee

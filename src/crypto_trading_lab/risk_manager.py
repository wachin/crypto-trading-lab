"""Risk manager (ROADMAP.md chapter 58).

The RiskManager operates independently from strategies and rejects/modifies
proposed orders before execution. This is a research-tier capability.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from typing import Optional


class RiskDecision(Enum):
    """Decision from the risk manager (58.7)."""
    APPROVE = "approve"
    REJECT = "reject"
    MODIFY = "modify"


@dataclass(frozen=True)
class RiskLimits:
    """Risk limits configuration (58.1)."""
    max_risk_per_trade: Decimal  # As fraction of portfolio
    max_position_size: Decimal  # As fraction of portfolio
    max_total_exposure: Decimal  # Sum of absolute positions
    max_long_exposure: Decimal
    max_short_exposure: Decimal


@dataclass(frozen=True)
class LossLimits:
    """Loss limits configuration (58.2)."""
    max_daily_loss: Decimal
    max_weekly_loss: Decimal
    max_drawdown: Decimal
    max_consecutive_losses: int


@dataclass(frozen=True)
class OperationalLimits:
    """Operational limits configuration (58.3)."""
    max_trades_per_day: int
    max_open_orders: int
    max_order_frequency_per_minute: int


@dataclass(frozen=True)
class PortfolioState:
    """Current portfolio state for risk checks."""
    total_value: Decimal
    long_exposure: Decimal
    short_exposure: Decimal
    daily_pnl: Decimal
    weekly_pnl: Decimal
    current_drawdown: Decimal
    consecutive_losses: int


@dataclass(frozen=True)
class OrderRequest:
    """Proposed order to evaluate."""
    strategy_name: str
    symbol: str
    side: str  # "buy" or "sell"
    quantity: Decimal
    price: Decimal
    timestamp: str


@dataclass(frozen=True)
class RiskDecisionResult:
    """Result of risk evaluation."""
    decision: RiskDecision
    reason: str
    modified_order: Optional[OrderRequest]


class RiskManager:
    """Central risk manager service (58.7)."""
    
    def __init__(
        self,
        limits: RiskLimits,
        loss_limits: LossLimits | None = None,
        operational_limits: OperationalLimits | None = None,
    ):
        self.limits = limits
        self.loss_limits = loss_limits or LossLimits(
            max_daily_loss=Decimal("0.02"),
            max_weekly_loss=Decimal("0.05"),
            max_drawdown=Decimal("0.20"),
            max_consecutive_losses=5,
        )
        self.operational_limits = operational_limits or OperationalLimits(
            max_trades_per_day=50,
            max_open_orders=10,
            max_order_frequency_per_minute=10,
        )
        self._trades_today = 0
    
    def evaluate(
        self,
        order: OrderRequest,
        portfolio: PortfolioState,
    ) -> RiskDecisionResult:
        """
        Evaluate an order against risk limits.
        """
        # Check position limits
        result = self._check_position_limits(order, portfolio)
        if result.decision != RiskDecision.APPROVE:
            return result
        
        # Check loss limits
        result = self._check_loss_limits(portfolio)
        if result.decision != RiskDecision.APPROVE:
            return result
        
        # Check operational limits
        result = self._check_operational_limits(order)
        if result.decision != RiskDecision.APPROVE:
            return result
        
        return RiskDecisionResult(
            decision=RiskDecision.APPROVE,
            reason="Order passes all risk checks",
            modified_order=None,
        )
    
    def _check_position_limits(
        self,
        order: OrderRequest,
        portfolio: PortfolioState,
    ) -> RiskDecisionResult:
        """Check position and exposure limits."""
        order_value = order.quantity * order.price
        
        # Check max position size
        if order_value > portfolio.total_value * self.limits.max_position_size:
            return RiskDecisionResult(
                decision=RiskDecision.REJECT,
                reason="Order exceeds maximum position size",
                modified_order=None,
            )
        
        # Check max total exposure
        new_exposure = (
            portfolio.long_exposure + portfolio.short_exposure + order_value
        )
        if new_exposure > portfolio.total_value * self.limits.max_total_exposure:
            return RiskDecisionResult(
                decision=RiskDecision.REJECT,
                reason="Order exceeds maximum total exposure",
                modified_order=None,
            )
        
        # Check long exposure
        if order.side == "buy":
            if portfolio.long_exposure + order_value > portfolio.total_value * self.limits.max_long_exposure:
                return RiskDecisionResult(
                    decision=RiskDecision.REJECT,
                    reason="Order exceeds maximum long exposure",
                    modified_order=None,
                )
        
        # Check short exposure
        if order.side == "sell":
            if portfolio.short_exposure + order_value > portfolio.total_value * self.limits.max_short_exposure:
                return RiskDecisionResult(
                    decision=RiskDecision.REJECT,
                    reason="Order exceeds maximum short exposure",
                    modified_order=None,
                )
        
        return RiskDecisionResult(
            decision=RiskDecision.APPROVE,
            reason="Position limits satisfied",
            modified_order=None,
        )
    
    def _check_loss_limits(
        self,
        portfolio: PortfolioState,
    ) -> RiskDecisionResult:
        """Check loss limits."""
        # Check max daily loss
        if portfolio.daily_pnl < -portfolio.total_value * self.loss_limits.max_daily_loss:
            return RiskDecisionResult(
                decision=RiskDecision.REJECT,
                reason="Daily loss limit exceeded",
                modified_order=None,
            )
        
        # Check max weekly loss
        if portfolio.weekly_pnl < -portfolio.total_value * self.loss_limits.max_weekly_loss:
            return RiskDecisionResult(
                decision=RiskDecision.REJECT,
                reason="Weekly loss limit exceeded",
                modified_order=None,
            )
        
        # Check max drawdown
        if portfolio.current_drawdown > self.loss_limits.max_drawdown:
            return RiskDecisionResult(
                decision=RiskDecision.REJECT,
                reason="Maximum drawdown exceeded",
                modified_order=None,
            )
        
        # Check consecutive losses
        if portfolio.consecutive_losses >= self.loss_limits.max_consecutive_losses:
            return RiskDecisionResult(
                decision=RiskDecision.REJECT,
                reason="Maximum consecutive losses reached",
                modified_order=None,
            )
        
        return RiskDecisionResult(
            decision=RiskDecision.APPROVE,
            reason="Loss limits satisfied",
            modified_order=None,
        )
    
    def _check_operational_limits(
        self,
        order: OrderRequest,
    ) -> RiskDecisionResult:
        """Check operational limits."""
        if self._trades_today >= self.operational_limits.max_trades_per_day:
            return RiskDecisionResult(
                decision=RiskDecision.REJECT,
                reason="Maximum trades per day reached",
                modified_order=None,
            )
        
        return RiskDecisionResult(
            decision=RiskDecision.APPROVE,
            reason="Operational limits satisfied",
            modified_order=None,
        )
    
    def record_trade(self) -> None:
        """Record a trade for operational limits."""
        self._trades_today += 1
    
    def reset_daily(self) -> None:
        """Reset daily counters."""
        self._trades_today = 0

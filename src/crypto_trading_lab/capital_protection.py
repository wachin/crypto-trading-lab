"""Capital protection (ROADMAP.md chapter 61).

Implements capital protection mechanisms: drawdown controls,
position sizing limits, and portfolio-level risk constraints.
This is a core safety feature.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Optional, Sequence


class ProtectionLevel(Enum):
    """Capital protection level."""
    NONE = "none"
    WARNING = "warning"      # Alert only
    REDUCE = "reduce"        # Reduce position sizes
    HALT = "halt"            # Halt new positions
    LIQUIDATE = "liquidate"  # Liquidate all positions


class DrawdownType(Enum):
    """Type of drawdown calculation."""
    ABSOLUTE = "absolute"      # From peak equity
    RELATIVE = "relative"      # From initial capital
    TRAILING = "trailing"      # Trailing from recent peak


@dataclass(frozen=True)
class CapitalLimits:
    """Capital protection limits (61.1)."""
    # Drawdown limits
    max_daily_loss: Decimal = Decimal("0.03")      # 3% daily max loss
    max_weekly_loss: Decimal = Decimal("0.05")     # 5% weekly max loss
    max_monthly_loss: Decimal = Decimal("0.10")    # 10% monthly max loss
    max_total_drawdown: Decimal = Decimal("0.20")  # 20% max total drawdown
    
    # Position limits
    max_position_size: Decimal = Decimal("0.10")   # 10% max per position
    max_sector_exposure: Decimal = Decimal("0.30") # 30% max per sector
    max_total_exposure: Decimal = Decimal("0.80")  # 80% max total exposure
    
    # Loss limits
    max_consecutive_losses: int = 5
    max_daily_trades: int = 50
    
    # Recovery requirements
    recovery_factor: Decimal = Decimal("0.5")      # Need 50% recovery before new positions


@dataclass
class CapitalState:
    """Current capital state for protection checks."""
    initial_capital: Decimal
    current_equity: Decimal
    peak_equity: Decimal
    daily_pnl: Decimal = Decimal(0)
    weekly_pnl: Decimal = Decimal(0)
    monthly_pnl: Decimal = Decimal(0)
    consecutive_losses: int = 0
    daily_trades: int = 0
    current_positions: dict[str, Decimal] = field(default_factory=dict)
    sector_exposure: dict[str, Decimal] = field(default_factory=dict)
    last_reset_daily: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_reset_weekly: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_reset_monthly: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass(frozen=True)
class ProtectionAction:
    """Action required by capital protection."""
    level: ProtectionLevel
    reason: str
    required_action: str
    affected_positions: list[str] = field(default_factory=list)
    new_limits: dict[str, Decimal] = field(default_factory=dict)


class CapitalProtection:
    """
    Capital protection system (Chapter 61).
    
    Monitors portfolio state and enforces capital protection rules.
    Integrates with risk manager and kill switch.
    """
    
    def __init__(self, limits: CapitalLimits | None = None):
        self.limits = limits or CapitalLimits()
        self.state = CapitalState(
            initial_capital=Decimal("10000"),
            current_equity=Decimal("10000"),
            peak_equity=Decimal("10000"),
        )
        self._actions: list[ProtectionAction] = []
    
    def update_equity(self, new_equity: Decimal) -> list[ProtectionAction]:
        """Update equity and check protection rules."""
        actions = []
        
        # Update equity and peak
        self.state.current_equity = new_equity
        if new_equity > self.state.peak_equity:
            self.state.peak_equity = new_equity
        
        # Check all protection rules
        actions.extend(self._check_drawdown_limits())
        actions.extend(self._check_position_limits())
        actions.extend(self._check_loss_limits())
        actions.extend(self._check_consecutive_losses())
        
        self._actions.extend(actions)
        return actions
    
    def _check_drawdown_limits(self) -> list[ProtectionAction]:
        """Check drawdown-based protection rules."""
        actions = []
        
        # Daily loss
        daily_loss = (self.state.initial_capital - self.state.current_equity) / self.state.initial_capital
        if abs(self.state.daily_pnl) >= self.limits.max_daily_loss * self.state.initial_capital:
            actions.append(ProtectionAction(
                level=ProtectionLevel.HALT,
                reason=f"Daily loss limit exceeded: {abs(self.state.daily_pnl):.2%}",
                required_action="Halt new positions for today",
            ))
        elif abs(self.state.daily_pnl) >= self.limits.max_daily_loss * self.state.initial_capital * Decimal("0.8"):
            actions.append(ProtectionAction(
                level=ProtectionLevel.WARNING,
                reason=f"Daily loss approaching limit: {abs(self.state.daily_pnl):.2%}",
                required_action="Monitor closely, consider reducing position sizes",
            ))
        
        # Weekly loss
        if abs(self.state.weekly_pnl) >= self.limits.max_weekly_loss * self.state.initial_capital:
            actions.append(ProtectionAction(
                level=ProtectionLevel.HALT,
                reason=f"Weekly loss limit exceeded: {abs(self.state.weekly_pnl):.2%}",
                required_action="Halt new positions for the week",
            ))
        
        # Monthly loss
        if abs(self.state.monthly_pnl) >= self.limits.max_monthly_loss * self.state.initial_capital:
            actions.append(ProtectionAction(
                level=ProtectionLevel.LIQUIDATE,
                reason=f"Monthly loss limit exceeded: {abs(self.state.monthly_pnl):.2%}",
                required_action="Liquidate all positions immediately",
            ))
        
        # Total drawdown from peak
        if self.state.peak_equity > 0:
            total_dd = (self.state.peak_equity - self.state.current_equity) / self.state.peak_equity
            if total_dd >= self.limits.max_total_drawdown:
                actions.append(ProtectionAction(
                    level=ProtectionLevel.LIQUIDATE,
                    reason=f"Maximum total drawdown exceeded: {total_dd:.2%}",
                    required_action="Liquidate all positions immediately",
                ))
            elif total_dd >= self.limits.max_total_drawdown * Decimal("0.8"):
                actions.append(ProtectionAction(
                    level=ProtectionLevel.REDUCE,
                    reason=f"Approaching maximum drawdown: {total_dd:.2%}",
                    required_action="Reduce position sizes by 50%",
                ))
        
        return actions
    
    def _check_position_limits(self) -> list[ProtectionAction]:
        """Check position size limits."""
        actions = []
        total_exposure = sum(abs(v) for v in self.state.current_positions.values())
        
        # Check individual position sizes
        for symbol, size in self.state.current_positions.items():
            if abs(size) > self.limits.max_position_size * self.state.current_equity:
                actions.append(ProtectionAction(
                    level=ProtectionLevel.REDUCE,
                    reason=f"Position {symbol} exceeds size limit: {abs(size):.2%}",
                    required_action=f"Reduce {symbol} position to max {self.limits.max_position_size:.0%}",
                    affected_positions=[symbol],
                    new_limits={symbol: self.limits.max_position_size * self.state.current_equity},
                ))
        
        # Total exposure
        if total_exposure > self.limits.max_total_exposure * self.state.current_equity:
            actions.append(ProtectionAction(
                level=ProtectionLevel.HALT,
                reason=f"Total exposure exceeds limit: {total_exposure:.2%} > {self.limits.max_total_exposure:.0%}",
                required_action="Halt new positions, reduce existing positions",
            ))
        
        return actions
    
    def _check_loss_limits(self) -> list[ProtectionAction]:
        """Check consecutive losses and trade frequency."""
        actions = []
        
        if self.state.consecutive_losses >= self.limits.max_consecutive_losses:
            actions.append(ProtectionAction(
                level=ProtectionLevel.HALT,
                reason=f"Consecutive losses limit reached: {self.state.consecutive_losses}",
                required_action="Halt trading, review strategy",
            ))
        
        if self.state.daily_trades >= self.limits.max_daily_trades:
            actions.append(ProtectionAction(
                level=ProtectionLevel.HALT,
                reason=f"Daily trade limit reached: {self.state.daily_trades}",
                required_action="No more trades today",
            ))
        
        return actions
    
    def _check_consecutive_losses(self) -> list[ProtectionAction]:
        """Check consecutive losses and apply recovery rules."""
        actions = []
        
        if self.state.consecutive_losses > 0:
            # Check if recovery factor is met before allowing new positions
            required_recovery = self.limits.recovery_factor * Decimal(str(self.state.consecutive_losses))
            current_drawdown = (self.state.peak_equity - self.state.current_equity) / self.state.peak_equity if self.state.peak_equity > 0 else Decimal(0)
            
            if current_drawdown < self.limits.recovery_factor:
                actions.append(ProtectionAction(
                    level=ProtectionLevel.REDUCE,
                    reason=f"Insufficient recovery after {self.state.consecutive_losses} losses",
                    required_action=f"Wait for {self.limits.recovery_factor:.0%} recovery before new positions",
                ))
        
        return actions
    
    def record_trade(self, pnl: Decimal, symbol: str, size: Decimal) -> None:
        """Record a trade result and update state."""
        self.state.daily_trades += 1
        
        if pnl >= 0:
            self.state.consecutive_losses = 0
        else:
            self.state.consecutive_losses += 1
        
        self.state.daily_pnl += pnl
        self.state.weekly_pnl += pnl
        self.state.monthly_pnl += pnl
        
        # Update position
        if symbol in self.state.current_positions:
            self.state.current_positions[symbol] += size
            if self.state.current_positions[symbol] == 0:
                del self.state.current_positions[symbol]
        else:
            self.state.current_positions[symbol] = size
    
    def reset_daily(self) -> None:
        """Reset daily counters."""
        self.state.daily_pnl = Decimal(0)
        self.state.daily_trades = 0
        self.state.last_reset_daily = datetime.now(timezone.utc)
    
    def reset_weekly(self) -> None:
        """Reset weekly counters."""
        self.state.weekly_pnl = Decimal(0)
        self.state.last_reset_weekly = datetime.now(timezone.utc)
    
    def reset_monthly(self) -> None:
        """Reset monthly counters."""
        self.state.monthly_pnl = Decimal(0)
        self.state.last_reset_monthly = datetime.now(timezone.utc)
    
    def get_protection_status(self) -> dict:
        """Get current protection status."""
        total_dd = (self.state.peak_equity - self.state.current_equity) / self.state.peak_equity if self.state.peak_equity > 0 else Decimal(0)
        daily_loss_pct = abs(self.state.daily_pnl) / self.state.initial_capital if self.state.initial_capital > 0 else Decimal(0)
        weekly_loss_pct = abs(self.state.weekly_pnl) / self.state.initial_capital if self.state.initial_capital > 0 else Decimal(0)
        
        return {
            "current_equity": float(self.state.current_equity),
            "peak_equity": float(self.state.peak_equity),
            "total_drawdown": float(total_dd),
            "daily_loss_pct": float(daily_loss_pct),
            "weekly_loss_pct": float(weekly_loss_pct),
            "consecutive_losses": self.state.consecutive_losses,
            "daily_trades": self.state.daily_trades,
            "total_exposure": float(sum(abs(v) for v in self.state.current_positions.values())),
            "protection_level": self._get_current_level().value,
            "active_alerts": len([a for a in self._actions if a.level in (ProtectionLevel.HALT, ProtectionLevel.LIQUIDATE)]),
        }
    
    def _get_current_level(self) -> ProtectionLevel:
        """Determine current protection level."""
        for action in reversed(self._actions):
            return action.level
        return ProtectionLevel.NONE


CAPITAL_PROTECTION_WARNING = (
    "Capital protection rules are safety mechanisms, not profit guarantees. "
    "They reduce but cannot eliminate risk of loss. Market gaps, "
    "liquidity crises, and systemic events can cause losses beyond limits. "
    "Never risk money you cannot afford to lose."
)


__all__ = [
    "ProtectionLevel",
    "DrawdownType",
    "CapitalLimits",
    "CapitalState",
    "ProtectionAction",
    "CapitalProtection",
    "CAPITAL_PROTECTION_WARNING",
]

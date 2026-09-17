"""Safety gates (ROADMAP.md chapter 67).

Safety gates are the executable protection layer between the application
and a real exchange. Capital preservation takes priority over strategy execution.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum


class GateStatus(Enum):
    """Status of a safety gate."""
    PASS = "pass"
    FAIL = "fail"
    WARNING = "warning"


class GateType(Enum):
    """Type of safety gate."""
    DATA_FRESHNESS = "data_freshness"
    CONNECTION_STATE = "connection_state"
    BALANCE_VERIFICATION = "balance_verification"
    RISK_LIMIT_CHECK = "risk_limit_check"
    KILL_SWITCH = "kill_switch"
    MARKET_CONDITIONS = "market_conditions"


@dataclass(frozen=True)
class GateResult:
    """Result of one safety gate check."""
    gate_type: GateType
    status: GateStatus
    message: str
    timestamp: datetime


@dataclass
class SafetyGates:
    """
    Safety gates check layer (Chapter 67).
    
    Checks all protection conditions before real orders reach the exchange.
    """
    data_freshness_seconds: int = 60
    min_balance_verification: Decimal = Decimal("1")
    max_daily_loss_fraction: Decimal = Decimal("0.05")
    
    _gate_history: list[GateResult] = field(default_factory=list)
    daily_pnl: Decimal = Decimal(0)
    
    def check_data_freshness(self, last_data_timestamp: datetime) -> GateResult:
        """Check if market data is fresh."""
        now = datetime.now(timezone.utc)
        age = (now - last_data_timestamp).total_seconds()
        
        if age <= self.data_freshness_seconds:
            self._record(GateResult(
                gate_type=GateType.DATA_FRESHNESS,
                status=GateStatus.PASS,
                message=f"Data is {age:.0f}s old",
                timestamp=now,
            ))
            return GateResult(
                gate_type=GateType.DATA_FRESHNESS,
                status=GateStatus.PASS,
                message=f"Data is {age:.0f}s old (threshold: {self.data_freshness_seconds}s)",
                timestamp=now,
            )
        else:
            self._record(GateResult(
                gate_type=GateType.DATA_FRESHNESS,
                status=GateStatus.FAIL,
                message=f"Data is {age:.0f}s old (threshold: {self.data_freshness_seconds}s)",
                timestamp=now,
            ))
            return GateResult(
                gate_type=GateType.DATA_FRESHNESS,
                status=GateStatus.FAIL,
                message=f"Data too old: {age:.0f}s",
                timestamp=now,
            )
    
    def check_connection_state(self, is_connected: bool) -> GateResult:
        """Check exchange connection state."""
        if is_connected:
            self._record(GateResult(
                gate_type=GateType.CONNECTION_STATE,
                status=GateStatus.PASS,
                message="Connection active",
                timestamp=datetime.now(timezone.utc),
            ))
            return GateResult(
                gate_type=GateType.CONNECTION_STATE,
                status=GateStatus.PASS,
                message="Connection active",
                timestamp=datetime.now(timezone.utc),
            )
        else:
            self._record(GateResult(
                gate_type=GateType.CONNECTION_STATE,
                status=GateStatus.FAIL,
                message="No connection to exchange",
                timestamp=datetime.now(timezone.utc),
            ))
            return GateResult(
                gate_type=GateType.CONNECTION_STATE,
                status=GateStatus.FAIL,
                message="No connection to exchange",
                timestamp=datetime.now(timezone.utc),
            )
    
    def check_balance_verification(
        self, 
        balance: Decimal,
        balance_asset: str = "USDT",
    ) -> GateResult:
        """Verify account balance exists."""
        if balance >= self.min_balance_verification:
            self._record(GateResult(
                gate_type=GateType.BALANCE_VERIFICATION,
                status=GateStatus.PASS,
                message=f"Balance {balance} {balance_asset} verified",
                timestamp=datetime.now(timezone.utc),
            ))
            return GateResult(
                gate_type=GateType.BALANCE_VERIFICATION,
                status=GateStatus.PASS,
                message=f"Balance {balance} {balance_asset} verified",
                timestamp=datetime.now(timezone.utc),
            )
        else:
            self._record(GateResult(
                gate_type=GateType.BALANCE_VERIFICATION,
                status=GateStatus.FAIL,
                message=f"Balance {balance} too low (min: {self.min_balance_verification})",
                timestamp=datetime.now(timezone.utc),
            ))
            return GateResult(
                gate_type=GateType.BALANCE_VERIFICATION,
                status=GateStatus.FAIL,
                message=f"Insufficient balance: {balance}",
                timestamp=datetime.now(timezone.utc),
            )
    
    def check_risk_limit(self, order_risk: Decimal, max_risk: Decimal) -> GateResult:
        """Check if order exceeds risk limits."""
        if order_risk <= max_risk:
            self._record(GateResult(
                gate_type=GateType.RISK_LIMIT_CHECK,
                status=GateStatus.PASS,
                message=f"Order risk {order_risk:.1%} within limits",
                timestamp=datetime.now(timezone.utc),
            ))
            return GateResult(
                gate_type=GateType.RISK_LIMIT_CHECK,
                status=GateStatus.PASS,
                message=f"Order risk within limits",
                timestamp=datetime.now(timezone.utc),
            )
        else:
            self._record(GateResult(
                gate_type=GateType.RISK_LIMIT_CHECK,
                status=GateStatus.FAIL,
                message=f"Order risk {order_risk:.1%} exceeds limit {max_risk:.1%}",
                timestamp=datetime.now(timezone.utc),
            ))
            return GateResult(
                gate_type=GateType.RISK_LIMIT_CHECK,
                status=GateStatus.FAIL,
                message=f"Order risk exceeds limit",
                timestamp=datetime.now(timezone.utc),
            )
    
    def check_kill_switch(self, is_active: bool) -> GateResult:
        """Check if kill switch is active."""
        if not is_active:
            self._record(GateResult(
                gate_type=GateType.KILL_SWITCH,
                status=GateStatus.PASS,
                message="Kill switch inactive",
                timestamp=datetime.now(timezone.utc),
            ))
            return GateResult(
                gate_type=GateType.KILL_SWITCH,
                status=GateStatus.PASS,
                message="Kill switch inactive",
                timestamp=datetime.now(timezone.utc),
            )
        else:
            self._record(GateResult(
                gate_type=GateType.KILL_SWITCH,
                status=GateStatus.FAIL,
                message="Kill switch ACTIVE - trading blocked",
                timestamp=datetime.now(timezone.utc),
            ))
            return GateResult(
                gate_type=GateType.KILL_SWITCH,
                status=GateStatus.FAIL,
                message="KILL SWITCH ACTIVE - trading blocked",
                timestamp=datetime.now(timezone.utc),
            )
    
    def check_daily_loss(self, current_pnl: Decimal) -> GateResult:
        """Check if daily loss limit is exceeded."""
        if current_pnl >= -self.daily_pnl * self.max_daily_loss_fraction:
            self._record(GateResult(
                gate_type=GateType.RISK_LIMIT_CHECK,
                status=GateStatus.PASS,
                message=f"Daily PnL {current_pnl:.2f} within limits",
                timestamp=datetime.now(timezone.utc),
            ))
            return GateResult(
                gate_type=GateType.RISK_LIMIT_CHECK,
                status=GateStatus.PASS,
                message="Daily loss limit not exceeded",
                timestamp=datetime.now(timezone.utc),
            )
        else:
            self._record(GateResult(
                gate_type=GateType.RISK_LIMIT_CHECK,
                status=GateStatus.FAIL,
                message=f"Daily loss limit exceeded: {current_pnl:.2f}",
                timestamp=datetime.now(timezone.utc),
            ))
            return GateResult(
                gate_type=GateType.RISK_LIMIT_CHECK,
                status=GateStatus.FAIL,
                message="Daily loss limit exceeded",
                timestamp=datetime.now(timezone.utc),
            )
    
    def record_pnl(self, pnl: Decimal) -> None:
        """Record PnL for daily limit tracking."""
        self.daily_pnl += pnl
    
    def _record(self, result: GateResult) -> None:
        """Record gate result in history."""
        self._gate_history.append(result)
    
    def get_history(self) -> list[GateResult]:
        """Get gate check history."""
        return self._gate_history.copy()
    
    def check_all(
        self,
        data_timestamp: datetime,
        is_connected: bool,
        balance: Decimal,
        order_risk: Decimal,
        max_risk: Decimal,
        is_kill_switch_active: bool,
    ) -> tuple[bool, list[GateResult]]:
        """
        Run all safety checks.
        
        Returns: (all_passed, list_of_results)
        """
        results = [
            self.check_data_freshness(data_timestamp),
            self.check_connection_state(is_connected),
            self.check_balance_verification(balance),
            self.check_risk_limit(order_risk, max_risk),
            self.check_kill_switch(is_kill_switch_active),
        ]
        
        all_passed = all(r.status == GateStatus.PASS for r in results)
        return all_passed, results


SAFETY_GATES_WARNING = (
    "Safety gates protect capital before orders reach real exchanges. "
    "All checks must pass. Failure in any gate blocks the order. "
    "Gates are non-bypassable - no component can disable them."
)

"""Emergency kill switch (ROADMAP.md chapter 59).

The kill switch provides an emergency stop mechanism for trading operations.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum


class KillSwitchState(Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"


@dataclass
class KillSwitch:
    """
    Emergency kill switch (59.1).
    
    When active, it blocks all trading operations.
    """
    state: KillSwitchState = KillSwitchState.INACTIVE
    activated_at: datetime | None = None
    activated_by: str | None = None
    reason: str | None = None
    
    def activate(self, by: str = "manual", reason: str = "") -> None:
        """Activate the kill switch."""
        self.state = KillSwitchState.ACTIVE
        self.activated_at = datetime.now(timezone.utc)
        self.activated_by = by
        self.reason = reason
    
    def deactivate(self) -> None:
        """Deactivate the kill switch."""
        self.state = KillSwitchState.INACTIVE
        self.activated_at = None
        self.activated_by = None
        self.reason = None
    
    def is_active(self) -> bool:
        """Check if kill switch is active."""
        return self.state == KillSwitchState.ACTIVE
    
    def get_state(self) -> dict:
        """Get current state as dict."""
        return {
            "state": self.state.value,
            "activated_at": str(self.activated_at) if self.activated_at else None,
            "activated_by": self.activated_by,
            "reason": self.reason,
        }


class KillSwitchManager:
    """
    Manages kill switch activation sources (59.3).
    """
    
    def __init__(self, kill_switch: KillSwitch):
        self._kill_switch = kill_switch
    
    def activate_on_emergency(self, reason: str = "emergency") -> None:
        """Activate on emergency signal."""
        if not self._kill_switch.is_active():
            self._kill_switch.activate(by="emergency", reason=reason)
    
    def activate_on_manual(self, reason: str = "") -> None:
        """Activate on manual request."""
        if not self._kill_switch.is_active():
            self._kill_switch.activate(by="manual", reason=reason)
    
    def activate_on_error(self, error: str) -> None:
        """Activate on system error."""
        if not self._kill_switch.is_active():
            self._kill_switch.activate(by="system_error", reason=error)
    
    def check_allowed(self, operation: str) -> bool:
        """Check if operation is allowed."""
        return not self._kill_switch.is_active()
    
    def get_switch(self) -> KillSwitch:
        """Get the kill switch."""
        return self._kill_switch


KILL_SWITCH_WARNING = (
    "Kill switch activated. All trading operations are blocked. "
    "Contact support or check system logs for details."
)

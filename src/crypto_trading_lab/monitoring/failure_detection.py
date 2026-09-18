"""Strategy failure detection (ROADMAP.md chapter 64).

This module monitors strategy performance and detects when a strategy is
underperforming relative to expectations. It supports early warning systems
for paper and live trading.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum


class FailureMode(Enum):
    """Types of strategy failure (64.1)."""
    RETURN_DEGRADATION = "return_degradation"
    DRAWDOWN_EXCEEDED = "drawdown_exceeded"
    LOW_FILL_RATE = "low_fill_rate"
    LOW_WIN_RATE = "low_win_rate"
    STRATEGY_DRIFT = "strategy_drift"


@dataclass(frozen=True)
class FailureAlert:
    """Alert when strategy shows signs of failure."""
    alert_id: str
    timestamp: datetime
    strategy_name: str
    failure_mode: FailureMode
    current_value: Decimal
    threshold: Decimal
    severity: str  # "warning" or "critical"
    message: str


@dataclass
class PerformanceTracker:
    """
    Track strategy performance over time and detect failures (64.1).
    
    Monitors return degradation, drawdown, fill rate, and win rate.
    """
    strategy_name: str
    expected_return: Decimal
    max_drawdown: Decimal
    expected_fill_rate: Decimal
    expected_win_rate: Decimal
    
    _alerts: list[FailureAlert] = field(default_factory=list)
    _performance_history: list[dict] = field(default_factory=list)
    
    def record_performance(
        self,
        actual_return: Decimal,
        actual_drawdown: Decimal,
        actual_fill_rate: Decimal,
        actual_win_rate: Decimal,
    ) -> list[FailureAlert]:
        """Record performance metrics and check for failures."""
        alerts = []
        now = datetime.now(timezone.utc)
        
        # Record in history
        self._performance_history.append({
            "timestamp": now.isoformat(),
            "return": str(actual_return),
            "drawdown": str(actual_drawdown),
            "fill_rate": str(actual_fill_rate),
            "win_rate": str(actual_win_rate),
        })
        
        # Check return degradation
        if actual_return < self.expected_return * Decimal("0.5"):
            alert = self._create_alert(
                now,
                FailureMode.RETURN_DEGRADATION,
                actual_return,
                self.expected_return,
                "Return below 50% of expected",
            )
            alerts.append(alert)
        
        # Check drawdown exceeded
        if actual_drawdown > self.max_drawdown:
            alert = self._create_alert(
                now,
                FailureMode.DRAWDOWN_EXCEEDED,
                actual_drawdown,
                self.max_drawdown,
                "Drawdown exceeds maximum",
            )
            alerts.append(alert)
        
        # Check fill rate
        if actual_fill_rate < self.expected_fill_rate * Decimal("0.8"):
            alert = self._create_alert(
                now,
                FailureMode.LOW_FILL_RATE,
                actual_fill_rate,
                self.expected_fill_rate,
                "Fill rate below 80% of expected",
            )
            alerts.append(alert)
        
        # Check win rate
        if actual_win_rate < self.expected_win_rate * Decimal("0.8"):
            alert = self._create_alert(
                now,
                FailureMode.LOW_WIN_RATE,
                actual_win_rate,
                self.expected_win_rate,
                "Win rate below 80% of expected",
            )
            alerts.append(alert)
        
        self._alerts.extend(alerts)
        return alerts
    
    def _create_alert(
        self,
        timestamp: datetime,
        mode: FailureMode,
        current: Decimal,
        threshold: Decimal,
        message: str,
    ) -> FailureAlert:
        """Create a failure alert."""
        severity = "critical" if current < threshold * Decimal("0.5") else "warning"
        
        return FailureAlert(
            alert_id=f"alert-{timestamp.timestamp()}",
            timestamp=timestamp,
            strategy_name=self.strategy_name,
            failure_mode=mode,
            current_value=current,
            threshold=threshold,
            severity=severity,
            message=message,
        )
    
    def get_alerts(self) -> list[FailureAlert]:
        """Get all alerts for this strategy."""
        return self._alerts.copy()
    
    def get_recent_alerts(self, count: int = 5) -> list[FailureAlert]:
        """Get the most recent alerts."""
        return self._alerts[-count:]
    
    def get_performance_history(self) -> list[dict]:
        """Get performance history."""
        return self._performance_history.copy()
    
    def is_failing(self) -> bool:
        """Check if strategy has any critical alerts."""
        return any(alert.severity == "critical" for alert in self._alerts)


FAILURE_DETECTION_WARNING = (
    "Failure detection is an early warning system, not a guarantee of "
    "strategy failure. Market conditions change and some degradation is "
    "normal. Review alerts before making decisions."
)

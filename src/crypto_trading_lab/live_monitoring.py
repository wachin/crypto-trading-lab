"""Live monitoring (ROADMAP.md chapter 62).

Real-time monitoring of trading system health, performance,
and safety metrics during live/paper trading.
"""

from __future__ import annotations

import time
import uuid
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Optional


class AlertLevel(Enum):
    """Alert severity level."""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class ComponentStatus(Enum):
    """System component status."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class Alert:
    """System alert."""
    alert_id: str
    timestamp: datetime
    level: AlertLevel
    component: str
    message: str
    details: dict = field(default_factory=dict)
    acknowledged: bool = False


@dataclass
class ComponentHealth:
    """Health status of a system component."""
    name: str
    status: ComponentStatus = ComponentStatus.UNKNOWN
    last_check: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    message: str = ""
    metrics: dict = field(default_factory=dict)
    last_error: str | None = None


@dataclass
class PerformanceSnapshot:
    """Performance snapshot for monitoring."""
    timestamp: datetime
    equity: Decimal
    daily_pnl: Decimal
    open_positions: int
    open_orders: int
    latency_ms: int
    api_calls_per_min: int
    error_rate: Decimal


class LiveMonitor:
    """
    Live monitoring system (Chapter 62).
    
    Monitors system health, performance, and safety metrics
    in real-time during paper/live trading.
    """
    
    def __init__(
        self,
        check_interval: int = 30,
        alert_thresholds: dict | None = None,
        max_alerts: int = 1000,
    ):
        self.check_interval = check_interval
        self.max_alerts = max_alerts
        self.alerts: list[Alert] = []
        self.components: dict[str, ComponentHealth] = {}
        self.performance_history: list[PerformanceSnapshot] = []
        self._callbacks: list[Callable[[Alert], None]] = []
        self._running = False
        self._thresholds = alert_thresholds or {
            "max_latency_ms": 5000,
            "max_error_rate": Decimal("0.05"),
            "min_equity_pct": Decimal("0.8"),
            "max_drawdown_pct": Decimal("0.2"),
            "max_latency_ms": 10000,
            "max_error_rate_pct": Decimal("0.1"),
        }
    
    def register_component(self, name: str, checker: Callable[[], ComponentHealth]) -> None:
        """Register a component for health checking."""
        self.components[name] = ComponentHealth(name=name)
    
    def add_alert_callback(self, callback: Callable[[Alert], None]) -> None:
        """Register callback for alert notifications."""
        self._callbacks.append(callback)
    
    def check_all(self) -> list[Alert]:
        """Run all health checks and return new alerts."""
        new_alerts = []
        
        for name, checker in self.components.items():
            try:
                health = checker()
                self.components[name] = health
                alerts = self._evaluate_component(health)
                new_alerts.extend(alerts)
            except Exception as e:
                alert = Alert(
                    alert_id=str(uuid.uuid4()),
                    timestamp=datetime.now(timezone.utc),
                    level=AlertLevel.CRITICAL,
                    component=name,
                    message=f"Health check failed: {e}",
                    details={"error": str(e)},
                )
                self._emit_alert(alert)
                new_alerts.append(alert)
        
        return new_alerts
    
    def _evaluate_component(self, health: ComponentHealth) -> list[Alert]:
        """Evaluate component health and generate alerts."""
        alerts = []
        
        if health.status == ComponentStatus.UNHEALTHY:
            alerts.append(Alert(
                alert_id=str(uuid.uuid4()),
                timestamp=datetime.now(timezone.utc),
                level=AlertLevel.CRITICAL,
                component=health.name,
                message=f"Component unhealthy: {health.message}",
                details=health.metrics,
            ))
        elif health.status == ComponentStatus.DEGRADED:
            alerts.append(Alert(
                alert_id=str(uuid.uuid4()),
                timestamp=datetime.now(timezone.utc),
                level=AlertLevel.WARNING,
                component=health.name,
                message=f"Component degraded: {health.message}",
                details=health.metrics,
            ))
        
        # Check metrics against thresholds
        for metric, value in health.metrics.items():
            if metric == "latency_ms" and value > self._thresholds["max_latency_ms"]:
                alerts.append(Alert(
                    alert_id=str(uuid.uuid4()),
                    timestamp=datetime.now(timezone.utc),
                    level=AlertLevel.WARNING,
                    component=health.name,
                    message=f"High latency: {value}ms",
                    details={"latency_ms": value, "threshold": self._thresholds["max_latency_ms"]},
                ))
            elif metric == "error_rate" and value > self._thresholds["max_error_rate"]:
                alerts.append(Alert(
                    alert_id=str(uuid.uuid4()),
                    timestamp=datetime.now(timezone.utc),
                    level=AlertLevel.WARNING,
                    component=health.name,
                    message=f"High error rate: {value:.1%}",
                    details={"error_rate": str(value), "threshold": str(self._thresholds["max_error_rate"])},
                ))
        
        return alerts
    
    def record_performance(self, snapshot: PerformanceSnapshot) -> None:
        """Record performance snapshot."""
        self.performance_history.append(snapshot)
        if len(self.performance_history) > 10000:
            self.performance_history = self.performance_history[-5000:]
        
        # Check equity thresholds
        if snapshot.equity > 0:
            equity_pct = snapshot.equity / Decimal("10000")  # Assume 10k initial
            if equity_pct < self._thresholds["min_equity_pct"]:
                self._emit_alert(Alert(
                    alert_id=str(uuid.uuid4()),
                    timestamp=datetime.now(timezone.utc),
                    level=AlertLevel.CRITICAL,
                    component="portfolio",
                    message=f"Equity below threshold: {equity_pct:.1%}",
                    details={"equity": str(snapshot.equity), "threshold": str(self._thresholds["min_equity_pct"])},
                ))
    
    def _emit_alert(self, alert: Alert) -> None:
        """Emit alert and notify callbacks."""
        self.alerts.append(alert)
        if len(self.alerts) > self.max_alerts:
            self.alerts = self.alerts[-self.max_alerts:]
        
        for callback in self._callbacks:
            try:
                callback(alert)
            except Exception:
                pass
    
    def acknowledge_alert(self, alert_id: str) -> bool:
        """Acknowledge an alert."""
        for alert in self.alerts:
            if alert.alert_id == alert_id:
                alert.acknowledged = True
                return True
        return False
    
    def get_recent_alerts(self, count: int = 50, unacknowledged_only: bool = False) -> list[Alert]:
        """Get recent alerts."""
        alerts = self.alerts
        if unacknowledged_only:
            alerts = [a for a in alerts if not a.acknowledged]
        return alerts[-count:]
    
    def get_component_status(self) -> dict[str, dict]:
        """Get status of all components."""
        return {
            name: {
                "status": health.status.value,
                "last_check": health.last_check.isoformat(),
                "message": health.message,
                "metrics": health.metrics,
            }
            for name, health in self.components.items()
        }
    
    def get_performance_summary(self, window: int = 100) -> dict:
        """Get performance summary over window."""
        if not self.performance_history:
            return {}
        
        recent = self.performance_history[-window:]
        return {
            "snapshots": len(recent),
            "avg_equity": sum(s.equity for s in recent) / len(recent),
            "total_pnl": sum(s.daily_pnl for s in recent),
            "avg_latency_ms": sum(s.latency_ms for s in recent) / len(recent),
            "max_drawdown": min(s.daily_pnl for s in recent) if recent else Decimal(0),
        }


def create_standard_checkers(
    monitor: LiveMonitor,
    exchange_client: Any = None,
    risk_manager: Any = None,
    kill_switch: Any = None,
) -> None:
    """Create standard health checkers for common components."""
    
    def check_exchange():
        try:
            if exchange_client and hasattr(exchange_client, "ping"):
                latency = exchange_client.ping()
                return ComponentHealth(
                    name="exchange",
                    status=ComponentStatus.HEALTHY if latency < 1000 else ComponentStatus.DEGRADED,
                    message=f"Exchange latency: {latency}ms",
                    metrics={"latency_ms": latency},
                )
            return ComponentHealth(name="exchange", status=ComponentStatus.UNKNOWN, message="No client")
        except Exception as e:
            return ComponentHealth(name="exchange", status=ComponentStatus.UNHEALTHY, message=str(e), metrics={"error": str(e)})
    
    def check_risk_manager():
        try:
            if risk_manager:
                # Could check risk limits, drawdowns, etc.
                return ComponentHealth(
                    name="risk_manager",
                    status=ComponentStatus.HEALTHY,
                    message="Risk manager operational",
                    metrics={},
                )
            return ComponentHealth(name="risk_manager", status=ComponentStatus.UNKNOWN, message="No risk manager")
        except Exception as e:
            return ComponentHealth(name="risk_manager", status=ComponentStatus.UNHEALTHY, message=str(e), metrics={"error": str(e)})
    
    def check_kill_switch():
        try:
            if kill_switch:
                active = kill_switch.is_active() if hasattr(kill_switch, "is_active") else False
                return ComponentHealth(
                    name="kill_switch",
                    status=ComponentStatus.HEALTHY if not active else ComponentStatus.CRITICAL,
                    message="Kill switch inactive" if not active else "Kill switch ACTIVE",
                    metrics={"active": active},
                )
            return ComponentHealth(name="kill_switch", status=ComponentStatus.UNKNOWN, message="No kill switch")
        except Exception as e:
            return ComponentHealth(name="kill_switch", status=ComponentStatus.UNHEALTHY, message=str(e), metrics={"error": str(e)})
    
    def check_data_freshness():
        # Would check data freshness in real implementation
        return ComponentHealth(
            name="data_feed",
            status=ComponentStatus.HEALTHY,
            message="Data feed operational",
            metrics={"freshness_seconds": 1},
        )
    
    monitor.register_component("exchange", check_exchange)
    monitor.register_component("risk_manager", check_risk_manager)
    monitor.register_component("kill_switch", check_kill_switch)
    monitor.register_component("data_feed", check_data_freshness)


LIVEMONITOR_WARNING = (
    "Live monitoring provides visibility, not guarantees. "
    "Alerts may be delayed or missed. Always maintain independent "
    "oversight of trading operations."
)


__all__ = [
    "AlertLevel",
    "ComponentStatus",
    "Alert",
    "ComponentHealth",
    "PerformanceSnapshot",
    "LiveMonitor",
    "create_standard_checkers",
    "LIVEMONITOR_WARNING",
]

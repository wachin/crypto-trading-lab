"""Strategy failure detection (ROADMAP.md chapter 64).

This module monitors a strategy live/paper performance and detects when it
stops behaving as it did historically, then recommends an evidence-based
action. Recommendations are advisory: they never place or cancel orders and
never bypass the risk manager (chapter 58), which remains the enforcement
layer.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Callable, Optional


class FailureMode(Enum):
    RETURN_DEGRADATION = "return_degradation"
    DRAWDOWN_EXCEEDED = "drawdown_exceeded"
    LOW_FILL_RATE = "low_fill_rate"
    LOW_WIN_RATE = "low_win_rate"
    STRATEGY_DRIFT = "strategy_drift"
    VOLATILITY_CHANGE = "volatility_change"
    TRADE_DISTRIBUTION_CHANGE = "trade_distribution_change"
    REGIME_CHANGE = "regime_change"
    DATA_QUALITY = "data_quality"


class RecommendationAction(Enum):
    CONTINUE = "continue"
    MONITOR = "monitor"
    REDUCE_EXPOSURE = "reduce_exposure"
    PAUSE = "pause"
    RETIRE = "retire"


@dataclass(frozen=True)
class FailureAlert:
    alert_id: str
    timestamp: datetime
    strategy_name: str
    failure_mode: FailureMode
    current_value: Decimal
    threshold: Decimal
    severity: str
    message: str


@dataclass(frozen=True)
class Recommendation:
    strategy_name: str
    action: RecommendationAction
    reasons: list[str]
    evidence: dict
    advisory: bool = True


@dataclass
class PerformanceTracker:
    """Track strategy performance over time and detect failures (64.1)."""

    strategy_name: str
    expected_return: Decimal
    max_drawdown: Decimal
    expected_fill_rate: Decimal
    expected_win_rate: Decimal
    expected_volatility: Optional[Decimal] = None
    expected_regime: Optional[str] = None
    expected_avg_trade_duration: Optional[Decimal] = None

    _alerts: list[FailureAlert] = field(default_factory=list)
    _performance_history: list[dict] = field(default_factory=list)

    def record_performance(
        self,
        actual_return: Decimal,
        actual_drawdown: Decimal,
        actual_fill_rate: Decimal,
        actual_win_rate: Decimal,
        actual_volatility: Optional[Decimal] = None,
        actual_regime: Optional[str] = None,
        actual_avg_trade_duration: Optional[Decimal] = None,
        data_quality_ok: bool = True,
    ) -> list[FailureAlert]:
        alerts: list[FailureAlert] = []
        now = datetime.now(timezone.utc)
        self._performance_history.append(
            {
                "timestamp": now.isoformat(),
                "return": str(actual_return),
                "drawdown": str(actual_drawdown),
                "fill_rate": str(actual_fill_rate),
                "win_rate": str(actual_win_rate),
                "volatility": str(actual_volatility),
                "regime": actual_regime,
                "avg_trade_duration": str(actual_avg_trade_duration),
                "data_quality_ok": data_quality_ok,
            }
        )
        if actual_return < self.expected_return * Decimal("0.5"):
            alerts.append(self._alert(now, FailureMode.RETURN_DEGRADATION,
                                      actual_return, self.expected_return,
                                      "Return below 50% of expected"))
        if actual_drawdown > self.max_drawdown:
            alerts.append(self._alert(now, FailureMode.DRAWDOWN_EXCEEDED,
                                      actual_drawdown, self.max_drawdown,
                                      "Drawdown exceeds maximum"))
        if actual_fill_rate < self.expected_fill_rate * Decimal("0.8"):
            alerts.append(self._alert(now, FailureMode.LOW_FILL_RATE,
                                      actual_fill_rate, self.expected_fill_rate,
                                      "Fill rate below 80% of expected"))
        if actual_win_rate < self.expected_win_rate * Decimal("0.8"):
            alerts.append(self._alert(now, FailureMode.LOW_WIN_RATE,
                                      actual_win_rate, self.expected_win_rate,
                                      "Win rate below 80% of expected"))
        if (self.expected_volatility is not None and actual_volatility is not None
                and actual_volatility > self.expected_volatility * Decimal("1.5")):
            alerts.append(self._alert(now, FailureMode.VOLATILITY_CHANGE,
                                      actual_volatility, self.expected_volatility,
                                      "Volatility more than 50% above expected"))
        if (self.expected_avg_trade_duration is not None
                and actual_avg_trade_duration is not None
                and self.expected_avg_trade_duration > 0
                and abs(actual_avg_trade_duration - self.expected_avg_trade_duration)
                / self.expected_avg_trade_duration > Decimal("0.5")):
            alerts.append(self._alert(now, FailureMode.TRADE_DISTRIBUTION_CHANGE,
                                      actual_avg_trade_duration,
                                      self.expected_avg_trade_duration,
                                      "Avg trade duration shifted >50% from expected"))
        if (self.expected_regime is not None and actual_regime is not None
                and actual_regime != self.expected_regime):
            alerts.append(self._alert(now, FailureMode.REGIME_CHANGE,
                                      Decimal("1"), Decimal("1"),
                                      "Regime changed from "
                                      + str(self.expected_regime)
                                      + " to " + str(actual_regime)))
        if not data_quality_ok:
            alerts.append(self._alert(now, FailureMode.DATA_QUALITY,
                                      Decimal("0"), Decimal("1"),
                                      "Data-quality problems detected"))
        self._alerts.extend(alerts)
        return alerts

    def _alert(self, now, mode, current, threshold, message) -> FailureAlert:
        severity = "critical" if current < threshold * Decimal("0.5") else "warning"
        if mode in (FailureMode.DRAWDOWN_EXCEEDED, FailureMode.DATA_QUALITY):
            severity = "critical"
        return FailureAlert(
            alert_id="alert-" + str(now.timestamp()) + "-" + mode.value,
            timestamp=now,
            strategy_name=self.strategy_name,
            failure_mode=mode,
            current_value=current,
            threshold=threshold,
            severity=severity,
            message=message,
        )

    def get_alerts(self) -> list[FailureAlert]:
        return self._alerts.copy()

    def get_recent_alerts(self, count: int = 5) -> list[FailureAlert]:
        return self._alerts[-count:]

    def get_performance_history(self) -> list[dict]:
        return self._performance_history.copy()


    def is_failing(self) -> bool:
        return any(a.severity == "critical" for a in self._alerts)

    def recommend(self, on_retire: Optional[Callable[[str], None]] = None) -> Recommendation:
        """Produce an evidence-based recommendation (64.2).

        Derived only from recorded alerts: never guesses, never hides its
        reasons, never executes an order or bypasses the risk manager. A
        Retire recommendation can update the strategy registry via the
        optional on_retire callback.
        """
        critical = [a for a in self._alerts if a.severity == "critical"]
        warnings = [a for a in self._alerts if a.severity == "warning"]
        reasons = [a.failure_mode.value + ": " + a.message for a in self._alerts]
        evidence = {}
        for a in self._alerts:
            evidence[a.failure_mode.value] = {
                "current": str(a.current_value),
                "threshold": str(a.threshold),
                "severity": a.severity,
            }
        if critical:
            retire = any(a.failure_mode == FailureMode.DRAWDOWN_EXCEEDED for a in critical) and any(
                a.failure_mode == FailureMode.RETURN_DEGRADATION for a in critical
            )
            action = RecommendationAction.RETIRE if retire else RecommendationAction.PAUSE
            if action is RecommendationAction.RETIRE and on_retire is not None:
                on_retire(self.strategy_name)
        elif warnings:
            action = (
                RecommendationAction.REDUCE_EXPOSURE
                if len(warnings) >= 2
                else RecommendationAction.MONITOR
            )
        else:
            action = RecommendationAction.CONTINUE
        if not reasons:
            reasons = ["No failure signals recorded."]
        return Recommendation(
            strategy_name=self.strategy_name,
            action=action,
            reasons=reasons,
            evidence=evidence,
        )


FAILURE_DETECTION_WARNING = (
    "Failure detection is an early warning system, not a guarantee of "
    "strategy failure. Market conditions change and some degradation is "
    "normal. Review alerts and recommendations before deciding, and never "
    "let a recommendation bypass the risk manager."
)

FAILURE_EDUCATION = [
    "Strategies degrade over time because markets are non-stationary: regimes, "
    "volatility and liquidity shift, so a historical edge decays.",
    "Past performance does not guarantee continued performance; a backtest is a "
    "hypothesis about the future, not a promise.",
    "Normal variability (noise) is not failure. Distinguish a genuine, sustained "
    "breakdown from an ordinary losing streak before acting.",
]

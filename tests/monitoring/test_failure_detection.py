"""Tests for strategy failure detection (ROADMAP.md chapter 64)."""

from __future__ import annotations

from decimal import Decimal

from crypto_trading_lab.monitoring.failure_detection import (
    FailureMode,
    PerformanceTracker,
)


def test_performance_tracker_init():
    """Should create performance tracker."""
    tracker = PerformanceTracker(
        strategy_name="Test",
        expected_return=Decimal("0.10"),
        max_drawdown=Decimal("0.20"),
        expected_fill_rate=Decimal("0.95"),
        expected_win_rate=Decimal("0.55"),
    )
    
    assert tracker.strategy_name == "Test"


def test_record_performance_no_alerts():
    """Should not alert when performance is normal."""
    tracker = PerformanceTracker(
        strategy_name="Test",
        expected_return=Decimal("0.10"),
        max_drawdown=Decimal("0.20"),
        expected_fill_rate=Decimal("0.95"),
        expected_win_rate=Decimal("0.55"),
    )
    
    alerts = tracker.record_performance(
        actual_return=Decimal("0.12"),
        actual_drawdown=Decimal("0.10"),
        actual_fill_rate=Decimal("0.98"),
        actual_win_rate=Decimal("0.60"),
    )
    
    assert len(alerts) == 0


def test_record_performance_return_alert():
    """Should alert when return is low."""
    tracker = PerformanceTracker(
        strategy_name="Test",
        expected_return=Decimal("0.10"),
        max_drawdown=Decimal("0.20"),
        expected_fill_rate=Decimal("0.95"),
        expected_win_rate=Decimal("0.55"),
    )
    
    alerts = tracker.record_performance(
        actual_return=Decimal("0.03"),  # Below 50% of expected
        actual_drawdown=Decimal("0.10"),
        actual_fill_rate=Decimal("0.98"),
        actual_win_rate=Decimal("0.60"),
    )
    
    assert len(alerts) == 1
    assert alerts[0].failure_mode == FailureMode.RETURN_DEGRADATION


def test_record_performance_drawdown_alert():
    """Should alert when drawdown is too high."""
    tracker = PerformanceTracker(
        strategy_name="Test",
        expected_return=Decimal("0.10"),
        max_drawdown=Decimal("0.20"),
        expected_fill_rate=Decimal("0.95"),
        expected_win_rate=Decimal("0.55"),
    )
    
    alerts = tracker.record_performance(
        actual_return=Decimal("0.12"),
        actual_drawdown=Decimal("0.25"),  # Exceeds max
        actual_fill_rate=Decimal("0.98"),
        actual_win_rate=Decimal("0.60"),
    )
    
    assert len(alerts) == 1
    assert alerts[0].failure_mode == FailureMode.DRAWDOWN_EXCEEDED


def test_record_performance_fill_rate_alert():
    """Should alert when fill rate is low."""
    tracker = PerformanceTracker(
        strategy_name="Test",
        expected_return=Decimal("0.10"),
        max_drawdown=Decimal("0.20"),
        expected_fill_rate=Decimal("0.95"),
        expected_win_rate=Decimal("0.55"),
    )
    
    alerts = tracker.record_performance(
        actual_return=Decimal("0.12"),
        actual_drawdown=Decimal("0.10"),
        actual_fill_rate=Decimal("0.70"),  # Below 80% of expected
        actual_win_rate=Decimal("0.60"),
    )
    
    assert len(alerts) == 1
    assert alerts[0].failure_mode == FailureMode.LOW_FILL_RATE


def test_get_alerts():
    """Should retrieve alerts."""
    tracker = PerformanceTracker(
        strategy_name="Test",
        expected_return=Decimal("0.10"),
        max_drawdown=Decimal("0.20"),
        expected_fill_rate=Decimal("0.95"),
        expected_win_rate=Decimal("0.55"),
    )
    
    tracker.record_performance(
        actual_return=Decimal("0.03"),
        actual_drawdown=Decimal("0.10"),
        actual_fill_rate=Decimal("0.98"),
        actual_win_rate=Decimal("0.60"),
    )
    
    alerts = tracker.get_alerts()
    assert len(alerts) == 1


def test_performance_history_recorded():
    """Should record performance history."""
    tracker = PerformanceTracker(
        strategy_name="Test",
        expected_return=Decimal("0.10"),
        max_drawdown=Decimal("0.20"),
        expected_fill_rate=Decimal("0.95"),
        expected_win_rate=Decimal("0.55"),
    )
    
    tracker.record_performance(
        actual_return=Decimal("0.12"),
        actual_drawdown=Decimal("0.10"),
        actual_fill_rate=Decimal("0.98"),
        actual_win_rate=Decimal("0.60"),
    )
    
    history = tracker.get_performance_history()
    assert len(history) == 1


def test_is_failing():
    """Should return true when critical alert exists."""
    tracker = PerformanceTracker(
        strategy_name="Test",
        expected_return=Decimal("0.10"),
        max_drawdown=Decimal("0.20"),
        expected_fill_rate=Decimal("0.95"),
        expected_win_rate=Decimal("0.55"),
    )
    
    # Create critical alert (below 50% of threshold)
    alerts = tracker.record_performance(
        actual_return=Decimal("0.03"),
        actual_drawdown=Decimal("0.10"),
        actual_fill_rate=Decimal("0.98"),
        actual_win_rate=Decimal("0.60"),
    )
    
    assert alerts[0].severity == "critical"
    assert tracker.is_failing()


from crypto_trading_lab.monitoring.failure_detection import (
    PerformanceTracker,
    FailureMode,
    RecommendationAction,
    FAILURE_EDUCATION,
)


def _tracker(**kw):
    return PerformanceTracker(
        strategy_name="s",
        expected_return=Decimal("1.0"),
        max_drawdown=Decimal("0.20"),
        expected_fill_rate=Decimal("0.95"),
        expected_win_rate=Decimal("0.55"),
        **kw,
    )


def test_volatility_change_detected():
    t = _tracker(expected_volatility=Decimal("0.10"))
    alerts = t.record_performance(
        Decimal("1.0"), Decimal("0.05"), Decimal("0.95"), Decimal("0.55"),
        actual_volatility=Decimal("0.20"),
    )
    modes = [a.failure_mode for a in alerts]
    assert FailureMode.VOLATILITY_CHANGE in modes


def test_regime_change_detected():
    t = _tracker(expected_regime="trend")
    alerts = t.record_performance(
        Decimal("1.0"), Decimal("0.05"), Decimal("0.95"), Decimal("0.55"),
        actual_regime="range",
    )
    assert any(a.failure_mode == FailureMode.REGIME_CHANGE for a in alerts)


def test_trade_distribution_change_detected():
    t = _tracker(expected_avg_trade_duration=Decimal("10"))
    alerts = t.record_performance(
        Decimal("1.0"), Decimal("0.05"), Decimal("0.95"), Decimal("0.55"),
        actual_avg_trade_duration=Decimal("20"),
    )
    assert any(a.failure_mode == FailureMode.TRADE_DISTRIBUTION_CHANGE for a in alerts)


def test_data_quality_detected():
    t = _tracker()
    alerts = t.record_performance(
        Decimal("1.0"), Decimal("0.05"), Decimal("0.95"), Decimal("0.55"),
        data_quality_ok=False,
    )
    assert any(a.failure_mode == FailureMode.DATA_QUALITY for a in alerts)


def test_recommend_continue_when_no_alerts():
    t = _tracker()
    t.record_performance(Decimal("1.0"), Decimal("0.05"), Decimal("0.95"), Decimal("0.55"))
    rec = t.recommend()
    assert rec.action is RecommendationAction.CONTINUE
    assert rec.advisory is True


def test_recommend_monitor_on_single_warning():
    t = _tracker(expected_volatility=Decimal("0.10"))
    t.record_performance(
        Decimal("1.0"), Decimal("0.05"), Decimal("0.95"), Decimal("0.55"),
        actual_volatility=Decimal("0.20"),
    )
    assert t.recommend().action is RecommendationAction.MONITOR


def test_recommend_reduce_exposure_on_multiple_warnings():
    t = _tracker(expected_volatility=Decimal("0.10"), expected_regime="trend")
    t.record_performance(
        Decimal("1.0"), Decimal("0.05"), Decimal("0.95"), Decimal("0.55"),
        actual_volatility=Decimal("0.20"), actual_regime="range",
    )
    assert t.recommend().action is RecommendationAction.REDUCE_EXPOSURE


def test_recommend_pause_on_critical():
    t = _tracker()
    t.record_performance(Decimal("1.0"), Decimal("0.50"), Decimal("0.95"), Decimal("0.55"))
    assert t.recommend().action is RecommendationAction.PAUSE


def test_recommend_retire_on_drawdown_and_return_critical():
    t = _tracker()
    t.record_performance(Decimal("0.10"), Decimal("0.50"), Decimal("0.95"), Decimal("0.55"))
    assert t.recommend().action is RecommendationAction.RETIRE


def test_recommend_retire_calls_on_retire_callback():
    t = _tracker()
    retired = []
    t.record_performance(Decimal("0.10"), Decimal("0.50"), Decimal("0.95"), Decimal("0.55"))
    t.recommend(on_retire=retired.append)
    assert retired == ["s"]


def test_recommendation_reasons_and_evidence_present():
    t = _tracker()
    t.record_performance(Decimal("0.10"), Decimal("0.50"), Decimal("0.95"), Decimal("0.55"))
    rec = t.recommend()
    assert rec.reasons
    assert rec.evidence


def test_education_present():
    assert len(FAILURE_EDUCATION) == 3

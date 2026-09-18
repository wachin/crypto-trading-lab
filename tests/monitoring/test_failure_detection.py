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

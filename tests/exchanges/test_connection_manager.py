"""Tests for connection manager primitives (ROADMAP chapter 27)."""

from datetime import datetime, timezone, timedelta

import pytest

from crypto_trading_lab.exchanges.connection_manager import (
    CircuitBreaker,
    CircuitState,
    ReconnectionPolicy,
    StaleDataDetector,
)


class TestReconnectionPolicy:
    def test_next_delay_doubles(self):
        policy = ReconnectionPolicy(base_delay=1.0, max_delay=100.0, jitter=0.0)
        assert policy.next_delay(1) == pytest.approx(1.0)
        assert policy.next_delay(2) == pytest.approx(2.0)
        assert policy.next_delay(3) == pytest.approx(4.0)

    def test_max_delay_caps(self):
        policy = ReconnectionPolicy(base_delay=1.0, max_delay=5.0, jitter=0.0)
        assert policy.next_delay(4) == pytest.approx(5.0)

    def test_jitter_bounds(self):
        policy = ReconnectionPolicy(base_delay=1.0, max_delay=100.0, jitter=0.2)
        for _ in range(100):
            d = policy.next_delay(1)
            assert 0.8 <= d <= 1.2

    def test_max_retries_stops(self):
        policy = ReconnectionPolicy(base_delay=1.0, max_retries=3, jitter=0.0)
        assert policy.should_retry(1)
        assert policy.should_retry(3)
        assert not policy.should_retry(4)
        with pytest.raises(StopIteration):
            policy.next_delay(4)


class TestCircuitBreaker:
    def test_closed_allows_attempts(self):
        cb = CircuitBreaker(failure_threshold=2, reset_timeout=1.0)
        assert cb.state is CircuitState.CLOSED
        assert cb.can_attempt()

    def test_opens_after_threshold(self):
        cb = CircuitBreaker(failure_threshold=2, reset_timeout=1.0)
        cb.record_failure()
        assert cb.state is CircuitState.CLOSED
        cb.record_failure()
        assert cb.state is CircuitState.OPEN
        assert not cb.can_attempt()

    def test_success_resets(self):
        cb = CircuitBreaker(failure_threshold=2, reset_timeout=1.0)
        cb.record_failure()
        cb.record_failure()
        cb.record_success()
        assert cb.state is CircuitState.CLOSED
        assert cb.can_attempt()

    def test_half_open_after_timeout(self):
        cb = CircuitBreaker(failure_threshold=1, reset_timeout=0.01)
        cb.record_failure()
        assert cb.state is CircuitState.OPEN
        # wait for reset
        import time
        time.sleep(0.02)
        assert cb.can_attempt()
        assert cb.state is CircuitState.HALF_OPEN


class TestStaleDataDetector:
    def test_initially_stale(self):
        sd = StaleDataDetector(max_age_seconds=10)
        assert sd.is_stale()

    def test_fresh_data_not_stale(self):
        sd = StaleDataDetector(max_age_seconds=10)
        now = datetime.now(timezone.utc)
        sd.touch(now)
        assert not sd.is_stale(now)

    def test_old_data_is_stale(self):
        sd = StaleDataDetector(max_age_seconds=10)
        now = datetime.now(timezone.utc)
        old = now - timedelta(seconds=20)
        sd.touch(old)
        assert sd.is_stale(now)

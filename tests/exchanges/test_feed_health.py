"""Tests for persisted feed health metrics (ROADMAP chapters 26.2, 27)."""

from datetime import datetime, timezone, timedelta

import pytest

from crypto_trading_lab.domain.models import ConnectionState
from crypto_trading_lab.exchanges.feed_health import (
    FeedHealthRecord,
    FeedHealthStatus,
    FeedHealthStore,
)


@pytest.fixture
def store(tmp_path):
    return FeedHealthStore(tmp_path / "health.db")


class TestFeedHealthStatus:
    def test_healthy_state(self):
        record = FeedHealthRecord(
            timestamp=datetime.now(timezone.utc),
            state=ConnectionState.CONNECTED,
            stale=False,
            age_seconds=1.0,
            server_time_offset=0.0,
            subscriptions=["btcusdt@kline_1m"],
            message_count=10,
            reconnect_attempts=0,
            circuit_breaker_state="closed",
        )
        assert record.status == FeedHealthStatus.HEALTHY
        
    def test_degraded_state(self):
        record = FeedHealthRecord(
            timestamp=datetime.now(timezone.utc),
            state=ConnectionState.DEGRADED,
            stale=True,
            age_seconds=100.0,
            server_time_offset=0.0,
            subscriptions=["btcusdt@kline_1m"],
            message_count=5,
            reconnect_attempts=2,
            circuit_breaker_state="closed",
        )
        assert record.status == FeedHealthStatus.DEGRADED
        
    def test_error_state(self):
        record = FeedHealthRecord(
            timestamp=datetime.now(timezone.utc),
            state=ConnectionState.ERROR,
            stale=True,
            age_seconds=None,
            server_time_offset=0.0,
            subscriptions=[],
            message_count=0,
            reconnect_attempts=5,
            circuit_breaker_state="open",
        )
        assert record.status == FeedHealthStatus.ERROR


class TestFeedHealthStore:
    def test_record_and_latest(self, store):
        record = FeedHealthRecord(
            timestamp=datetime.now(timezone.utc),
            state=ConnectionState.CONNECTED,
            stale=False,
            age_seconds=1.0,
            server_time_offset=0.0,
            subscriptions=["btcusdt@kline_1m"],
            message_count=10,
            reconnect_attempts=0,
            circuit_breaker_state="closed",
        )
        store.record(record)
        
        latest = store.get_latest()
        assert latest is not None
        assert latest.state == ConnectionState.CONNECTED
        assert latest.status == FeedHealthStatus.HEALTHY
        
    def test_returns_none_when_empty(self, store):
        assert store.get_latest() is None
        
    def test_recent_records(self, store):
        for i in range(5):
            record = FeedHealthRecord(
                timestamp=datetime.now(timezone.utc) - timedelta(minutes=i),
                state=ConnectionState.CONNECTED,
                stale=False,
                age_seconds=1.0,
                server_time_offset=0.0,
                subscriptions=["btcusdt@kline_1m"],
                message_count=10,
                reconnect_attempts=0,
                circuit_breaker_state="closed",
            )
            store.record(record)
            
        recent = store.get_recent(limit=3)
        assert len(recent) == 3
        
    def test_health_summary(self, store):
        # Add healthy records
        for _ in range(8):
            store.record(FeedHealthRecord(
                timestamp=datetime.now(timezone.utc),
                state=ConnectionState.CONNECTED,
                stale=False,
                age_seconds=1.0,
                server_time_offset=0.0,
                subscriptions=[],
                message_count=10,
                reconnect_attempts=0,
                circuit_breaker_state="closed",
            ))
            
        # Add error records
        for _ in range(2):
            store.record(FeedHealthRecord(
                timestamp=datetime.now(timezone.utc),
                state=ConnectionState.ERROR,
                stale=True,
                age_seconds=None,
                server_time_offset=0.0,
                subscriptions=[],
                message_count=0,
                reconnect_attempts=5,
                circuit_breaker_state="open",
            ))
            
        summary = store.get_health_summary()
        assert summary["total"] == 10
        assert summary["healthy"] == 8
        assert summary["errors"] == 2
        assert summary["health_percentage"] == 80.0
        
    def test_empty_summary(self, store):
        assert store.get_health_summary() == {"total": 0}
"""Tests for Binance WebSocket client (ROADMAP chapters 26.2, 27)."""

import asyncio
import json
import time
from unittest.mock import AsyncMock, MagicMock

import pytest

from crypto_trading_lab.exchanges.binance.config import BINANCE_SPOT_TESTNET_ENDPOINTS
from crypto_trading_lab.exchanges.binance.websocket_client import BinanceWebSocketClient, MessageTracker
from crypto_trading_lab.domain.models import ConnectionState


class TestMessageTracker:
    def test_records_new_messages(self):
        tracker = MessageTracker()
        dup, oos = tracker.record(100)
        assert not dup and not oos
        
    def test_detects_duplicates(self):
        tracker = MessageTracker()
        tracker.record(100)
        dup, oos = tracker.record(100)
        assert dup
        
    def test_detects_out_of_order(self):
        tracker = MessageTracker()
        tracker.record(100)
        tracker.record(200)
        dup, oos = tracker.record(150)
        assert oos
        
    def test_accepts_increasing_sequence(self):
        tracker = MessageTracker()
        tracker.record(100)
        dup, oos = tracker.record(101)
        assert not dup and not oos


class TestBinanceWebSocketClient:
    @pytest.fixture
    def client(self):
        return BinanceWebSocketClient(BINANCE_SPOT_TESTNET_ENDPOINTS)
        
    def test_initial_state(self, client):
        assert client.state == ConnectionState.DISCONNECTED
        
    def test_subscription_management(self, client):
        client.subscribe("btcusdt@kline_1m")
        client.subscribe("ethusdt@trade")
        assert "btcusdt@kline_1m" in client._subscriptions
        assert "ethusdt@trade" in client._subscriptions
        
    def test_handler_registration(self, client):
        mock_handler = MagicMock()
        client.add_kline_handler(mock_handler)
        client.add_trade_handler(mock_handler)
        assert len(client._handlers['kline']) == 1
        assert len(client._handlers['trade']) == 1
        
    def test_time_sync_tracking(self, client):
        assert client.synchronize_time() == 0.0
        
    def test_health_metrics(self, client):
        metrics = client.get_health_metrics()
        assert 'state' in metrics
        assert 'state_explanation' in metrics
        assert 'stale' in metrics
        assert 'subscriptions' in metrics
        assert 'pending_subscriptions' in metrics
        
    def test_beginner_friendly_state_messages(self, client):
        # All states have beginner explanations
        for state in ConnectionState:
            msg = state.beginner_explanation
            assert len(msg) > 20
            assert isinstance(msg, str)


def test_client_state_transitions():
    """Test that client can transition through expected states."""
    from crypto_trading_lab.exchanges.connection_manager import ReconnectionPolicy
    
    client = BinanceWebSocketClient(
        BINANCE_SPOT_TESTNET_ENDPOINTS,
        policy=ReconnectionPolicy(base_delay=0.1, max_delay=1.0, jitter=0.0)
    )
    
    # Initial state
    assert client.state == ConnectionState.DISCONNECTED
    
    # After subscribing, should be able to start
    client.subscribe("test@kline_1m")
    assert len(client._subscriptions) == 1


def test_rate_limiter_integration():
    """Test that rate limiter is properly initialized."""
    from crypto_trading_lab.exchanges.rate_limiter import RateLimiter
    
    limiter = RateLimiter(max_weight=100, window_seconds=60)
    client = BinanceWebSocketClient(
        BINANCE_SPOT_TESTNET_ENDPOINTS,
        rate_limiter=limiter
    )
    
    assert client._rate_limiter is limiter
    assert client._rate_limiter.max_weight == 100


def test_subscription_recovery():
    """Test that subscriptions are tracked for recovery."""
    client = BinanceWebSocketClient(BINANCE_SPOT_TESTNET_ENDPOINTS)
    client.subscribe("btcusdt@kline_1m")
    client.subscribe("ethusdt@kline_5m")
    
    assert "btcusdt@kline_1m" in client._pending_subscriptions
    assert "ethusdt@kline_5m" in client._pending_subscriptions
    
    client.unsubscribe("btcusdt@kline_1m")
    assert "btcusdt@kline_1m" not in client._subscriptions


def test_warning_callbacks():
    """Test visible warnings can be registered."""
    client = BinanceWebSocketClient(BINANCE_SPOT_TESTNET_ENDPOINTS)
    warnings = []
    
    client.add_warning_callback(lambda state, msg: warnings.append((state, msg)))
    
    client._emit_warning("test_state", "test message")
    assert len(warnings) == 1
    assert warnings[0] == ("test_state", "test message")


def test_reconciliation_report():
    """Test reconciliation after reconnection."""
    client = BinanceWebSocketClient(BINANCE_SPOT_TESTNET_ENDPOINTS)
    
    # No last reconnect time
    report = client.reconcile_after_reconnect()
    assert report['has_gap'] is False
    
    # Simulate reconnection
    client._last_reconnect_time = time.time() - 10  # 10 seconds ago
    report = client.reconcile_after_reconnect()
    assert report['has_gap'] is True
    assert report['gap_seconds'] > 5

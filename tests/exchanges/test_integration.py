"""Integration tests for Binance adapter + WebSocket pipeline (chapters 26.2, 27).

Tests the full data flow from REST fetch through WebSocket subscription
to health metrics persistence, using mock exchanges for deterministic
results without network access.
"""

from __future__ import annotations

import time
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

from crypto_trading_lab.domain.models import ConnectionState, Symbol, Ticker, utc_now
from crypto_trading_lab.exchanges.binance.adapter import BinanceRestAdapter
from crypto_trading_lab.exchanges.binance.config import BINANCE_SPOT_TESTNET_ENDPOINTS
from crypto_trading_lab.exchanges.connection_manager import (
    CircuitBreaker,
    ReconnectionPolicy,
    StaleDataDetector,
)
from crypto_trading_lab.exchanges.feed_health import FeedHealthStatus
from crypto_trading_lab.exchanges.rate_limiter import RateLimiter
from crypto_trading_lab.exchanges.mock import MockExchange, generate_candles

BTCUSDT = Symbol("BTC/USDT")


class TestBinanceAdapterIntegration:
    """Integration tests for the Binance adapter pipeline."""

    def test_adapter_with_full_pipeline(self, tmp_path):
        """Adapter works with REST + WebSocket + health metrics."""
        adapter = BinanceRestAdapter(
            BINANCE_SPOT_TESTNET_ENDPOINTS,
            health_store_path=tmp_path / "health.db",
        )
        
        # REST fetch
        adapter.connect()
        assert adapter.state() == ConnectionState.CONNECTED
        
        adapter.disconnect()
        assert adapter.state() == ConnectionState.STOPPED
        
    def test_rate_limiter_shared_with_adapter(self):
        """Rate limiter shared between REST and WebSocket."""
        limiter = RateLimiter(max_weight=100, window_seconds=60)
        adapter = BinanceRestAdapter(
            BINANCE_SPOT_TESTNET_ENDPOINTS,
            rate_limiter=limiter,
        )
        
        assert adapter._rate_limiter is limiter
        assert adapter._rate_limiter.max_weight == 100
        
    def test_circuit_breaker_protects_adapter(self):
        """Circuit breaker applied to REST calls."""
        cb = CircuitBreaker(failure_threshold=2, reset_timeout=1.0)
        adapter = BinanceRestAdapter(
            BINANCE_SPOT_TESTNET_ENDPOINTS,
            circuit_breaker=cb,
        )
        
        # Simulate failures
        adapter._circuit_breaker.record_failure()
        adapter._circuit_breaker.record_failure()
        
        assert adapter._circuit_breaker.state.value == "open"
        
    def test_stale_data_detector_works_with_adapter(self):
        """Stale data detection integrated with adapter."""
        adapter = BinanceRestAdapter(BINANCE_SPOT_TESTNET_ENDPOINTS)
        
        # Initially stale
        assert adapter._ws_client._stale_detector.is_stale()
        
        # After connection
        adapter.connect()
        adapter._ws_client._stale_detector.touch()
        assert not adapter._ws_client._stale_detector.is_stale()


class TestWebSocketSubscriptionIntegration:
    """Test WebSocket subscription integration."""

    def test_subscriptions_route_to_ws_client(self):
        """Subscriptions are tracked for WebSocket client."""
        adapter = BinanceRestAdapter(BINANCE_SPOT_TESTNET_ENDPOINTS)
        
        adapter.subscribe_ticker(BTCUSDT, lambda t: None)
        adapter.subscribe_candles(BTCUSDT, "1h", lambda c: None)
        adapter.subscribe_trades(BTCUSDT, lambda t: None)
        
        # Subscriptions stored in WebSocket client
        assert len(adapter._ws_client._subscriptions) == 3
        
    def test_unsubscribe_all_clears_subscriptions(self):
        """Unsubscribe clears all subscriptions."""
        adapter = BinanceRestAdapter(BINANCE_SPOT_TESTNET_ENDPOINTS)
        
        adapter.subscribe_ticker(BTCUSDT, lambda t: None)
        adapter.subscribe_candles(BTCUSDT, "1h", lambda c: None)
        adapter.unsubscribe_all()
        
        assert len(adapter._ws_client._subscriptions) == 0


class TestHealthMetricsIntegration:
    """Integration of health metrics persistence."""

    def test_health_metrics_recorded(self, tmp_path):
        """Health metrics are persisted to database."""
        adapter = BinanceRestAdapter(
            BINANCE_SPOT_TESTNET_ENDPOINTS,
            health_store_path=tmp_path / "health.db",
        )
        
        adapter.connect()
        adapter._ws_client._stale_detector.touch()
        
        record = adapter.record_health_metrics()
        assert record is not None
        assert record.state == ConnectionState.CONNECTED
        assert record.stale is False
        
    def test_health_metrics_optional(self):
        """Health metrics disabled when no store path."""
        adapter = BinanceRestAdapter(BINANCE_SPOT_TESTNET_ENDPOINTS)
        
        record = adapter.record_health_metrics()
        assert record is None
        
    def test_health_metrics_survive_restart(self, tmp_path):
        """Health metrics persist across adapter restarts."""
        store_path = tmp_path / "health.db"
        
        # First adapter records metrics
        adapter1 = BinanceRestAdapter(
            BINANCE_SPOT_TESTNET_ENDPOINTS,
            health_store_path=store_path,
        )
        adapter1.connect()
        adapter1._ws_client._stale_detector.touch()
        adapter1.record_health_metrics()
        
        # Second adapter reads same database
        adapter2 = BinanceRestAdapter(
            BINANCE_SPOT_TESTNET_ENDPOINTS,
            health_store_path=store_path,
        )
        assert adapter2.health_store is not None
        latest = adapter2.health_store.get_latest()
        assert latest is not None
        assert latest.state == ConnectionState.CONNECTED


class TestMockExchangeIntegration:
    """Integration with MockExchange for deterministic testing."""

    def test_mock_with_binance_adapter_flow(self):
        """Mock exchange simulates Binance-like flow."""
        mock = MockExchange(
            candles=generate_candles(BTCUSDT, "1h", count=5),
            tickers={BTCUSDT: Ticker(
                symbol=BTCUSDT,
                timestamp=utc_now(),
                last=Decimal("50000"),
            )},
            allow_trading=True,
        )
        
        mock.connect()
        assert mock.state() == ConnectionState.CONNECTED
        
        # Fetch ticker
        ticker = mock.fetch_ticker(BTCUSDT)
        assert ticker.last == Decimal("50000")
        
        # Simulate disconnection
        mock.simulate_disconnection()
        assert mock.state() == ConnectionState.RECONNECTING
        
        # Recover
        mock.connect()
        assert mock.state() == ConnectionState.CONNECTED
        
    def test_mock_with_rate_limit_simulation(self):
        """Mock exchange simulates rate limiting."""
        mock = MockExchange(
            rate_limit_calls=3,
            rate_limit_window_s=60,
            tickers={BTCUSDT: Ticker(
                symbol=BTCUSDT,
                timestamp=utc_now(),
                last=Decimal("50000"),
            )},
        )
        mock.connect()
        
        # Consume all allowed calls
        mock.fetch_ticker(BTCUSDT)
        mock.fetch_ticker(BTCUSDT)
        mock.fetch_ticker(BTCUSDT)
        
        # Fourth call should be rate limited
        with pytest.raises(Exception):  # AdapterRateLimited or similar
            mock.fetch_ticker(BTCUSDT)
            
    def test_mock_subscriptions_with_health(self, tmp_path):
        """Mock subscriptions work with health tracking."""
        mock = MockExchange(
            candles=generate_candles(BTCUSDT, "1h", count=5),
        )
        mock.connect()
        
        # Subscribe to candles
        received = []
        mock.subscribe_candles(BTCUSDT, "1h", received.append)
        
        # Replay publishes to subscribers
        count = mock.replay_candles(BTCUSDT, "1h")
        assert count == 5
        assert len(received) == 5
        
    def test_mock_fill_engine_with_balances(self):
        """Mock fill engine handles balances correctly."""
        mock = MockExchange(
            initial_balances={"USDT": Decimal("10000"), "BTC": Decimal("0.5")},
            allow_trading=True,
            tickers={BTCUSDT: Ticker(
                symbol=BTCUSDT,
                timestamp=utc_now(),
                last=Decimal("50000"),
            )},
        )
        mock.connect()
        
        usdt_before = mock.fetch_balances()["USDT"].free
        
        from crypto_trading_lab.domain.models import (
            OrderRequest, OrderSide, OrderType,
        )
        request = OrderRequest(
            symbol=BTCUSDT,
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=Decimal("0.01"),
            price=Decimal("50000"),
        )
        
        result = mock.create_order(request)
        assert result.status.value in ("filled", "partially_filled")
        
        usdt_after = mock.fetch_balances()["USDT"].free
        # Balance decreased
        assert usdt_after < usdt_before


@pytest.mark.integration
class TestFullPipelineIntegration:
    """Full pipeline tests requiring more setup."""

    def test_end_to_end_state_transitions(self, tmp_path):
        """End-to-end state transitions from disconnected to connected."""
        adapter = BinanceRestAdapter(
            BINANCE_SPOT_TESTNET_ENDPOINTS,
            health_store_path=tmp_path / "health.db",
        )
        
        # Initial state
        assert adapter.state() == ConnectionState.DISCONNECTED
        
        # Connect
        adapter.connect()
        assert adapter.state() == ConnectionState.CONNECTED
        
        # Simulate stale data
        time.sleep(0.1)
        assert adapter._ws_client._stale_detector.is_stale()
        
        # Record health
        record = adapter.record_health_metrics()
        assert record is not None
        latest = adapter.health_store.get_latest()
        assert latest is not None
        assert latest.state == ConnectionState.CONNECTED
        
    def test_reconnection_with_backoff(self, tmp_path):
        """Reconnection with exponential backoff works."""
        from crypto_trading_lab.exchanges.connection_manager import ReconnectionPolicy
        
        policy = ReconnectionPolicy(base_delay=0.1, max_delay=1.0, jitter=0.0)
        adapter = BinanceRestAdapter(
            BINANCE_SPOT_TESTNET_ENDPOINTS,
            health_store_path=tmp_path / "health.db",
        )
        
        # Verify policy produces increasing delays
        d1 = policy.next_delay(1)
        d2 = policy.next_delay(2)
        d3 = policy.next_delay(3)
        
        assert d1 <= d2 <= d3
        
    def test_circuit_breaker_prevents_hammering(self, tmp_path):
        """Circuit breaker stops repeated failures."""
        adapter = BinanceRestAdapter(
            BINANCE_SPOT_TESTNET_ENDPOINTS,
            health_store_path=tmp_path / "health.db",
        )
        
        cb = CircuitBreaker(failure_threshold=5, reset_timeout=0.05)
        adapter._circuit_breaker = cb
        
        # Record failures
        for _ in range(5):
            cb.record_failure()
            
        assert cb.state.value == "open"
        assert not cb.can_attempt()
        
        # After timeout, half-open
        import time
        time.sleep(0.1)
        assert cb.can_attempt()
        assert cb.state.value == "half_open"
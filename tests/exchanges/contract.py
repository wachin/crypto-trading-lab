"""Shared contract tests for exchange adapters (ROADMAP.md chapter 14.3).

Every adapter — mock, CCXT-backed, or future ones — must pass this
suite. Suites subclass :class:`AdapterContract` and provide:

- ``make_adapter()``: an adapter connected against deterministic data
  (BTC/USDT at 50,000 USDT, seeded candles, no pending scripts);
- ``cleanup()``: reset any global state;
- ``trigger_ticker(adapter)``: force the adapter to deliver one ticker
  update to subscribed handlers (the mechanical difference between
  polling/streaming adapters is hidden here).

The contract deliberately excludes account-simulator behaviour (balance
effects after fills, notional pre-checks): those are properties of the
paper-trading engine, not of every adapter.
"""

from __future__ import annotations

from collections.abc import Callable
from decimal import Decimal

import pytest

from crypto_trading_lab.domain.models import (
    ConnectionState,
    OrderRequest,
    OrderSide,
    OrderStatus,
    OrderType,
    Symbol,
)
from crypto_trading_lab.exchanges.base.adapter import Capability, ExchangeAdapter
from crypto_trading_lab.exchanges.errors import (
    AdapterError,
    AdapterNotSupported,
)

BTCUSDT = Symbol("BTC/USDT")
_TRADING = Capability.TRADING


def _limit_request(
    quantity: Decimal = Decimal("0.01"), price: Decimal = Decimal("50000")
) -> OrderRequest:
    return OrderRequest(
        symbol=BTCUSDT,
        side=OrderSide.BUY,
        order_type=OrderType.LIMIT,
        quantity=quantity,
        price=price,
    )


class AdapterContract:
    """Contract tests shared by all adapters (chapter 14.3)."""

    make_adapter: Callable[[], ExchangeAdapter]

    def cleanup(self) -> None:  # pragma: no cover - default no-op
        return None

    def trigger_ticker(self, adapter: ExchangeAdapter) -> None:
        raise NotImplementedError("suites must deliver one ticker update")

    # ------------------------------------------------------------------
    # Lifecycle and states (chapter 27)
    # ------------------------------------------------------------------
    def test_connect_disconnect_lifecycle(self):
        adapter = self.make_adapter()
        try:
            assert adapter.state() is not ConnectionState.CONNECTED
            adapter.connect()
            assert adapter.state() is ConnectionState.CONNECTED
            adapter.disconnect()
            assert adapter.state() is ConnectionState.STOPPED
        finally:
            self.cleanup()

    def test_all_states_have_beginner_explanations(self):
        for state in ConnectionState:
            assert state.beginner_explanation

    # ------------------------------------------------------------------
    # Market data normalization (chapter 7)
    # ------------------------------------------------------------------
    def test_fetch_markets_returns_normalized_models(self):
        adapter = self.make_adapter()
        try:
            adapter.connect()
            markets = adapter.fetch_markets()
            assert markets, "adapter must expose at least one market"
            market = next(m for m in markets if m.symbol == BTCUSDT)
            assert market.base == "BTC" and market.quote == "USDT"
            assert isinstance(market.price_precision, int)
            assert market.min_quantity is None or isinstance(
                market.min_quantity, Decimal
            )
        finally:
            self.cleanup()

    def test_fetch_ticker_normalizes_decimal_prices(self):
        adapter = self.make_adapter()
        try:
            adapter.connect()
            ticker = adapter.fetch_ticker(BTCUSDT)
            assert isinstance(ticker.last, Decimal)
            assert ticker.last > 0
            assert ticker.timestamp.tzinfo is not None
        finally:
            self.cleanup()

    def test_fetch_candles_chronological_and_valid(self):
        adapter = self.make_adapter()
        try:
            adapter.connect()
            candles = adapter.fetch_candles(BTCUSDT, "1h")
            assert candles, "adapter must serve the seeded candles"
            times = [c.open_time for c in candles]
            assert times == sorted(times)
            for candle in candles:
                assert isinstance(candle.close, Decimal)
                assert candle.high >= max(candle.open, candle.close)
                assert candle.low <= min(candle.open, candle.close)
        finally:
            self.cleanup()

    def test_fetch_candles_limit(self):
        adapter = self.make_adapter()
        try:
            adapter.connect()
            candles = adapter.fetch_candles(BTCUSDT, "1h", limit=5)
            assert len(candles) <= 5
        finally:
            self.cleanup()

    # ------------------------------------------------------------------
    # Read-only safety default (chapters 60/61)
    # ------------------------------------------------------------------
    def test_order_operations_require_trading_capability(self):
        adapter = self.make_adapter()
        try:
            adapter.connect()
            if adapter.supports(_TRADING):
                pytest.skip("adapter under test has trading enabled")
            with pytest.raises(AdapterNotSupported):
                adapter.create_order(_limit_request())
        finally:
            self.cleanup()

    # ------------------------------------------------------------------
    # Trading and order updates (chapter 26)
    # ------------------------------------------------------------------
    def test_create_order_fills_and_reports_update(self):
        adapter = self.make_adapter()
        try:
            adapter.connect()
            if not adapter.supports(_TRADING):
                pytest.skip("read-only adapter")
            updates: list[object] = []
            adapter.on_order_update(updates.append)
            result = adapter.create_order(_limit_request())
            assert result.status in (OrderStatus.FILLED, OrderStatus.OPEN)
            assert result.adapter_order_id
            assert result.quantity == Decimal("0.01")
            assert updates, "create_order must emit an order update"
            assert updates[-1].adapter_order_id == result.adapter_order_id
        finally:
            self.cleanup()

    def test_cancel_unknown_order_raises_domain_error(self):
        adapter = self.make_adapter()
        try:
            adapter.connect()
            if not adapter.supports(_TRADING):
                pytest.skip("read-only adapter")
            with pytest.raises(AdapterError):
                adapter.cancel_order("no-such-order", BTCUSDT)
        finally:
            self.cleanup()

    # ------------------------------------------------------------------
    # Subscriptions (chapter 26)
    # ------------------------------------------------------------------
    def test_subscribe_ticker_receives_updates(self):
        adapter = self.make_adapter()
        try:
            adapter.connect()
            received: list[object] = []
            adapter.subscribe_ticker(BTCUSDT, received.append)
            self.trigger_ticker(adapter)
            assert received, "ticker subscription must deliver updates"
            assert received[0].symbol == BTCUSDT
        finally:
            self.cleanup()

    def test_unsubscribe_stops_delivery(self):
        adapter = self.make_adapter()
        try:
            adapter.connect()
            received: list[object] = []
            adapter.subscribe_ticker(BTCUSDT, received.append)
            adapter.unsubscribe_all()
            self.trigger_ticker(adapter)
            assert received == []
        finally:
            self.cleanup()

    # ------------------------------------------------------------------
    # Permissions (chapter 26)
    # ------------------------------------------------------------------
    def test_check_api_permissions_reports_read(self):
        adapter = self.make_adapter()
        try:
            adapter.connect()
            permissions = adapter.check_api_permissions()
            assert permissions["read"] is True
            assert isinstance(permissions["trade"], bool)
        finally:
            self.cleanup()

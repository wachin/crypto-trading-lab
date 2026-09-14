"""MockExchange tests (ROADMAP.md chapter 26.1)."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

import pytest

from crypto_trading_lab.domain.models import (
    ConnectionState,
    OrderRequest,
    OrderSide,
    OrderStatus,
    OrderType,
    Symbol,
    Ticker,
    utc_now,
)
from crypto_trading_lab.exchanges.base.adapter import Capability
from crypto_trading_lab.exchanges.errors import (
    AdapterError,
    AdapterInsufficientFunds,
    AdapterInvalidOrder,
    AdapterNetworkError,
    AdapterNotSupported,
    AdapterRateLimited,
)
from crypto_trading_lab.exchanges.mock import MockExchange, generate_candles
from tests.exchanges.contract import AdapterContract, BTCUSDT

S60000 = Ticker(
    symbol=BTCUSDT,
    timestamp=utc_now(),
    last=Decimal("50000"),
)


def make_trading_mock(**overrides) -> MockExchange:
    params = dict(
        candles=generate_candles(BTCUSDT, "1h", count=10),
        tickers={BTCUSDT: S60000},
        initial_balances={"USDT": Decimal("10000"), "BTC": Decimal("0.5")},
        allow_trading=True,
    )
    params.update(overrides)
    return MockExchange(**params)


class TestMockContract(AdapterContract):
    """MockExchange against the shared contract (chapter 14.3)."""

    def make_adapter(self) -> MockExchange:
        return make_trading_mock()

    def trigger_ticker(self, adapter: MockExchange) -> None:
        adapter.publish_ticker(
            Ticker(symbol=BTCUSDT, timestamp=utc_now(), last=Decimal("50000"))
        )


class TestScriptedFailures:
    def test_queued_error_raises_once_then_recovers(self):
        mock = make_trading_mock()
        mock.connect()
        mock.queue_error(AdapterNetworkError("simulated outage"))
        with pytest.raises(AdapterNetworkError):
            mock.fetch_ticker(BTCUSDT)
        assert mock.fetch_ticker(BTCUSDT).last == Decimal("50000")

    def test_queued_rejection_rejects_order(self):
        mock = make_trading_mock()
        mock.connect()
        mock.queue_rejection("simulated exchange rejection")
        request = OrderRequest(
            symbol=BTCUSDT,
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=Decimal("0.01"),
            price=Decimal("50000"),
        )
        with pytest.raises(AdapterInvalidOrder, match="rejection"):
            mock.create_order(request)

    def test_rate_limit_simulation(self):
        mock = make_trading_mock(rate_limit_calls=2, rate_limit_window_s=60)
        mock.connect()
        mock.fetch_ticker(BTCUSDT)
        mock.fetch_ticker(BTCUSDT)
        with pytest.raises(AdapterRateLimited):
            mock.fetch_ticker(BTCUSDT)
        assert mock.state() is ConnectionState.RATE_LIMITED
        # Recovery: a successful connect clears the state.
        mock.connect()
        assert mock.state() is ConnectionState.CONNECTED

    def test_simulated_latency_disabled_by_default(self, monkeypatch):
        slept = []
        monkeypatch.setattr(
            "crypto_trading_lab.exchanges.mock.exchange.time.sleep",
            lambda s: slept.append(s),
        )
        mock = make_trading_mock()
        mock.connect()
        mock.fetch_ticker(BTCUSDT)
        assert slept == []  # no sleeps in normal tests (chapter 14)

        slow = make_trading_mock(latency_ms=250)
        slow.connect()
        slow.fetch_ticker(BTCUSDT)
        assert slept == [0.25]


class TestFillEngine:
    def _request(self, quantity=Decimal("0.01"), price=Decimal("50000")):
        return OrderRequest(
            symbol=BTCUSDT,
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=quantity,
            price=price,
        )

    def test_full_fill_updates_balances_exactly(self):
        mock = make_trading_mock(taker_fee_pct=Decimal("0.1"))
        mock.connect()
        usdt_before = mock.fetch_balances()["USDT"].free
        result = mock.create_order(self._request())
        assert result.status is OrderStatus.FILLED
        fill = result.fills[0]
        expected_cost = Decimal("0.01") * fill.price + fill.fee
        assert mock.fetch_balances()["USDT"].free == usdt_before - expected_cost

    def test_slippage_moves_buy_price_up(self):
        mock = make_trading_mock(slippage_pct=Decimal("0.2"))
        mock.connect()
        result = mock.create_order(self._request())
        # 0.2 percent of 50,000 = 100 -> 50,100
        assert result.average_price == Decimal("50100.00")

    def test_partial_fill_then_fill_remaining(self):
        mock = make_trading_mock()
        mock.connect()
        mock.queue_partial_fill(Decimal("0.5"))
        result = mock.create_order(self._request(quantity=Decimal("0.02")))
        assert result.status is OrderStatus.PARTIALLY_FILLED
        assert result.filled_quantity == Decimal("0.01")
        assert mock.fetch_open_orders(BTCUSDT)
        completed = mock.fill_remaining(result.adapter_order_id)
        assert completed.status is OrderStatus.FILLED
        assert completed.filled_quantity == Decimal("0.02")
        assert len(completed.fills) == 2
        assert mock.fetch_open_orders(BTCUSDT) == []

    def test_insufficient_funds_rejected(self):
        mock = make_trading_mock(initial_balances={"USDT": Decimal("5")})
        mock.connect()
        with pytest.raises(AdapterInsufficientFunds):
            mock.create_order(self._request(quantity=Decimal("1")))

    def test_sell_requires_base_asset(self):
        mock = make_trading_mock(initial_balances={"USDT": Decimal("10000")})
        mock.connect()
        request = OrderRequest(
            symbol=BTCUSDT,
            side=OrderSide.SELL,
            order_type=OrderType.LIMIT,
            quantity=Decimal("0.01"),
            price=Decimal("50000"),
        )
        with pytest.raises(AdapterInsufficientFunds):
            mock.create_order(request)

    def test_order_update_handler_sees_every_transition(self):
        mock = make_trading_mock()
        mock.connect()
        seen: list[str] = []
        mock.on_order_update(lambda result: seen.append(result.status.value))
        mock.queue_partial_fill(Decimal("0.5"))
        result = mock.create_order(self._request(quantity=Decimal("0.02")))
        mock.fill_remaining(result.adapter_order_id)
        assert seen == ["partially_filled", "filled"]


class TestReadonlyDefault:
    def test_trading_disabled_by_default(self):
        mock = MockExchange(tickers={BTCUSDT: S60000})
        assert not mock.supports(Capability.TRADING)
        mock.connect()
        with pytest.raises(AdapterNotSupported):
            mock.create_order(
                OrderRequest(
                    symbol=BTCUSDT,
                    side=OrderSide.BUY,
                    order_type=OrderType.MARKET,
                    quantity=Decimal("0.01"),
                )
            )


class TestReplayAndDeterminism:
    def test_replay_publishes_all_candles_in_order(self):
        mock = make_trading_mock()
        mock.connect()
        received: list[object] = []
        mock.subscribe_candles(BTCUSDT, "1h", received.append)
        count = mock.replay_candles(BTCUSDT, "1h")
        assert count == 10
        assert len(received) == 10
        times = [c.open_time for c in received]
        assert times == sorted(times)

    def test_generated_candles_are_deterministic(self):
        first = generate_candles(BTCUSDT, "1h", 5, seed=7)
        second = generate_candles(BTCUSDT, "1h", 5, seed=7)
        assert first == second

    def test_disconnection_state_is_visible(self):
        mock = make_trading_mock()
        mock.connect()
        mock.simulate_disconnection()
        assert mock.state() is ConnectionState.RECONNECTING

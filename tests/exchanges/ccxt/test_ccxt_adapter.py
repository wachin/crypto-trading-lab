"""CCXT adapter tests against a fake client.

No ``ccxt`` import and no network anywhere (chapter 14): the adapter
consumes any duck-typed client, so a deterministic fake verifies the
same code paths real ccxt would drive. Error-mapping tests use exception
class *names*, matching the adapter's name-based mapping.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

import pytest

from crypto_trading_lab.domain.models import ConnectionState, Symbol
from crypto_trading_lab.exchanges.base.adapter import Capability
from crypto_trading_lab.exchanges.ccxt.adapter import (
    CcxtExchangeAdapter,
    map_client_error,
)
from crypto_trading_lab.exchanges.errors import (
    AdapterAuthenticationError,
    AdapterDataError,
    AdapterInsufficientFunds,
    AdapterInvalidOrder,
    AdapterNetworkError,
    AdapterNotSupported,
    AdapterRateLimited,
    AdapterRequestError,
)
from tests.exchanges.contract import AdapterContract, BTCUSDT

# ---------------------------------------------------------------------------
# Deterministic fake ccxt client
# ---------------------------------------------------------------------------

RAW_MARKET = {
    "id": "BTCUSDT",
    "symbol": "BTC/USDT",
    "base": "BTC",
    "quote": "USDT",
    "precision": {"price": 2, "amount": 6},
    "limits": {
        "amount": {"min": 0.0001},
        "cost": {"min": 10.0},
    },
    "fees": {"trading": {"maker": 0.001, "taker": 0.001}},
}

RAW_TICKER = {
    "symbol": "BTC/USDT",
    "timestamp": 1704067200000,  # 2024-01-01T00:00:00Z
    "last": 50000.5,
    "bid": 50000.0,
    "ask": 50001.0,
    "baseVolume": 123.456,
}

RAW_OHLCV = [
    [1704067200000, 50000.0, 50100.0, 49900.0, 50050.0, 12.5],
    [1704070800000, 50050.0, 50200.0, 50000.0, 50150.0, 13.5],
]

RAW_BALANCE = {
    "BTC": {"free": 0.5, "used": 0.0, "total": 0.5},
    "USDT": {"free": 10000.0, "used": 0.0, "total": 10000.0},
}

RAW_ORDER = {
    "id": "1",
    "clientOrderId": "cli-1",
    "symbol": "BTC/USDT",
    "type": "limit",
    "side": "buy",
    "status": "closed",
    "amount": 0.01,
    "filled": 0.01,
    "average": 50000.0,
    "fee": {"cost": 0.005, "currency": "USDT"},
    "timestamp": 1704067200000,
}


class FakeCcxtBinance:
    """Minimal deterministic double of the ccxt.binance surface."""

    id = "binance"
    precisionMode = 2  # DECIMAL_PLACES

    def __init__(self) -> None:
        self.markets = [dict(RAW_MARKET)]
        self.orders: dict[str, dict[str, Any]] = {"1": dict(RAW_ORDER)}
        self.next_id = 2
        self.fail_next_with: Exception | None = None

    # -- failure scripting ------------------------------------------------
    def _maybe_fail(self) -> None:
        if self.fail_next_with is not None:
            exc = self.fail_next_with
            self.fail_next_with = None
            raise exc

    # -- ccxt surface ------------------------------------------------------
    def fetch_markets(self):
        self._maybe_fail()
        return [dict(m) for m in self.markets]

    def fetch_ticker(self, symbol):
        self._maybe_fail()
        if symbol != "BTC/USDT":
            raise ValueError(f"unknown symbol {symbol}")
        return dict(RAW_TICKER)

    def fetch_ohlcv(self, symbol, timeframe, since=None, limit=None):
        self._maybe_fail()
        rows = [list(r) for r in RAW_OHLCV]
        if since is not None:
            rows = [r for r in rows if r[0] >= since]
        if limit is not None:
            rows = rows[:limit]
        return rows

    def fetch_balance(self):
        self._maybe_fail()
        return {
            "free": {"BTC": 0.5, "USDT": 10000.0},
            "used": {"BTC": 0.0, "USDT": 0.0},
            "total": {"BTC": 0.5, "USDT": 10000.0},
            "BTC": {"free": 0.5, "used": 0.0, "total": 0.5},
            "USDT": {"free": 10000.0, "used": 0.0, "total": 10000.0},
        }

    def fetch_open_orders(self, symbol=None):
        self._maybe_fail()
        return []

    def create_order(self, symbol, type, side, amount, price, params):
        self._maybe_fail()
        order = {
            "id": str(self.next_id),
            "clientOrderId": params.get("clientOrderId"),
            "symbol": symbol,
            "type": type,
            "side": side,
            "status": "closed",
            "amount": amount,
            "filled": amount,
            "average": price or 50000.0,
            "fee": {"cost": 0.005, "currency": "USDT"},
            "timestamp": 1704067200000,
        }
        self.orders[order["id"]] = order
        self.next_id += 1
        return order

    def cancel_order(self, id, symbol):
        self._maybe_fail()
        order = self.orders.get(str(id))
        if order is None:
            raise KeyError(f"order {id} not found")
        order["status"] = "canceled"
        return order


class TestCcxtContract(AdapterContract):
    """The CCXT adapter against the same contract as the mock."""

    def make_adapter(self) -> CcxtExchangeAdapter:
        return CcxtExchangeAdapter(FakeCcxtBinance(), allow_trading=True)

    def trigger_ticker(self, adapter: CcxtExchangeAdapter) -> None:
        adapter.dispatch_ticker(dict(RAW_TICKER))


class TestReadonlyDefault:
    def test_trading_off_by_default(self):
        adapter = CcxtExchangeAdapter(FakeCcxtBinance())
        assert not adapter.supports(Capability.TRADING)
        adapter.connect()
        with pytest.raises(AdapterNotSupported):
            adapter.create_order(
                _limit(quantity=Decimal("0.01"), price=Decimal("50000"))
            )

    def test_read_operations_still_work(self):
        adapter = CcxtExchangeAdapter(FakeCcxtBinance())
        adapter.connect()
        assert adapter.fetch_ticker(BTCUSDT).last == Decimal("50000.5")


def _limit(quantity: Decimal, price: Decimal):
    from crypto_trading_lab.domain.models import OrderRequest, OrderSide, OrderType

    return OrderRequest(
        symbol=BTCUSDT,
        side=OrderSide.BUY,
        order_type=OrderType.LIMIT,
        quantity=quantity,
        price=price,
    )


class TestErrorMapping:
    def test_known_names_map_to_domain_errors(self):
        assert isinstance(
            map_client_error(_make("RateLimitExceeded")), AdapterRateLimited
        )
        assert isinstance(
            map_client_error(_make("AuthenticationError")), AdapterAuthenticationError
        )
        assert isinstance(
            map_client_error(_make("InsufficientFunds")), AdapterInsufficientFunds
        )
        assert isinstance(
            map_client_error(_make("InvalidOrder")), AdapterInvalidOrder
        )
        assert isinstance(
            map_client_error(_make("RequestTimeout")), AdapterNetworkError
        )
        assert isinstance(map_client_error(_make("BadResponse")), AdapterDataError)

    def test_unknown_names_map_to_request_error(self):
        assert isinstance(map_client_error(_make("SomeWeirdError")), AdapterRequestError)

    def test_domain_errors_pass_through(self):
        err = AdapterRateLimited("already mapped")
        assert map_client_error(err) is err

    def _failure(self, exc: Exception):
        client = FakeCcxtBinance()
        client.fail_next_with = exc
        return CcxtExchangeAdapter(client)

    def test_failed_call_updates_connection_state(self):
        adapter = self._failure(_make("RateLimitExceeded"))
        adapter.connect()
        with pytest.raises(AdapterRateLimited):
            adapter.fetch_ticker(BTCUSDT)
        assert adapter.state() is ConnectionState.RATE_LIMITED

    def test_failed_call_to_network_error_suggests_reconnecting(self):
        adapter = self._failure(_make("RequestTimeout"))
        adapter.connect()
        with pytest.raises(AdapterNetworkError):
            adapter.fetch_ticker(BTCUSDT)
        assert adapter.state() is ConnectionState.RECONNECTING

    def test_failed_call_to_auth_error_maps_to_error_state(self):
        adapter = self._failure(_make("AuthenticationError"))
        adapter.connect()
        with pytest.raises(AdapterAuthenticationError):
            adapter.check_api_permissions()
        assert adapter.state() is ConnectionState.ERROR


def _make(name: str) -> Exception:
    return type(name, (Exception,), {})()


class TestNormalization:
    def test_market_metadata_normalized(self):
        adapter = CcxtExchangeAdapter(FakeCcxtBinance())
        adapter.connect()
        markets = adapter.fetch_markets()
        market = markets[0]
        assert market.exchange == "binance"
        assert market.symbol == Symbol("BTC/USDT")
        assert market.price_precision == 2
        assert market.quantity_precision == 6
        assert market.min_quantity == Decimal("0.0001")
        assert market.min_notional == Decimal("10.0")
        assert market.taker_fee == Decimal("0.001")

    def test_tick_size_precision_mode_derives_decimals(self):
        client = FakeCcxtBinance()
        client.precisionMode = 1  # TICK_SIZE
        client.markets = [
            dict(RAW_MARKET, precision={"price": 0.01, "amount": 0.000001})
        ]
        adapter = CcxtExchangeAdapter(client)
        adapter.connect()
        market = adapter.fetch_markets()[0]
        assert market.price_precision == 2
        assert market.quantity_precision == 6

    def test_candles_sorted_and_decimal(self):
        adapter = CcxtExchangeAdapter(FakeCcxtBinance())
        adapter.connect()
        candles = adapter.fetch_candles(BTCUSDT, "1h")
        assert [c.open_time for c in candles] == sorted(
            c.open_time for c in candles
        )
        assert candles[0].close == Decimal("50050.0")
        assert candles[0].volume == Decimal("12.5")

    def test_balances_skip_aggregate_views(self):
        adapter = CcxtExchangeAdapter(FakeCcxtBinance())
        adapter.connect()
        balances = adapter.fetch_balances()
        assert set(balances) == {"BTC", "USDT"}
        assert balances["USDT"].free == Decimal("10000.0")
        assert balances["USDT"].locked == Decimal("0")

    def test_order_status_closed_maps_to_filled(self):
        adapter = CcxtExchangeAdapter(FakeCcxtBinance(), allow_trading=True)
        adapter.connect()
        updates: list[object] = []
        adapter.on_order_update(updates.append)
        result = adapter.create_order(
            _limit(quantity=Decimal("0.01"), price=Decimal("50000"))
        )
        assert result.status.value == "filled"
        assert result.average_price == Decimal("50000.0")
        assert result.fills == ()
        assert updates[-1].adapter_order_id == result.adapter_order_id

    def test_cancel_maps_to_canceled_status(self):
        adapter = CcxtExchangeAdapter(FakeCcxtBinance(), allow_trading=True)
        adapter.connect()
        result = adapter.cancel_order("1", BTCUSDT)
        assert result.status.value == "canceled"

    def test_unparsable_payload_raises_data_error(self):
        client = FakeCcxtBinance()
        client.markets = [{"symbol": "NOT-A-PAIR"}]
        adapter = CcxtExchangeAdapter(client)
        adapter.connect()
        with pytest.raises(AdapterDataError):
            adapter.fetch_markets()

    def test_client_without_expected_method_raises_data_error(self):
        adapter = CcxtExchangeAdapter(object())
        adapter.connect()
        with pytest.raises(AdapterDataError):
            adapter.fetch_markets()


class TestContractOnlyMethodsPresent:
    def test_subscription_registries_exist(self):
        adapter = CcxtExchangeAdapter(FakeCcxtBinance())
        received: list[object] = []
        adapter.subscribe_ticker(BTCUSDT, received.append)
        adapter.dispatch_ticker(dict(RAW_TICKER))
        assert received and received[0].symbol == BTCUSDT
        adapter.unsubscribe_all()
        adapter.dispatch_ticker(dict(RAW_TICKER))
        assert len(received) == 1

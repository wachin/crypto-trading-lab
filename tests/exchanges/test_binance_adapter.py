"""Tests for Binance adapter (ROADMAP chapters 26.2, 26)."""

from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

from crypto_trading_lab.exchanges.binance.adapter import (
    BinanceRestAdapter,
    _decimal_places,
)
from crypto_trading_lab.exchanges.binance.config import BINANCE_SPOT_TESTNET_ENDPOINTS
from crypto_trading_lab.domain.models import (
    ConnectionState,
    Market,
    OrderRequest,
    OrderSide,
    OrderStatus,
    OrderType,
    Symbol,
)
from crypto_trading_lab.exchanges.base.adapter import Capability
from crypto_trading_lab.exchanges.errors import (
    AdapterInvalidOrder,
    AdapterNotSupported,
)


class TestBinanceRestAdapter:
    @pytest.fixture
    def adapter(self):
        return BinanceRestAdapter(BINANCE_SPOT_TESTNET_ENDPOINTS)
        
    def test_initial_state(self, adapter):
        assert adapter.state() == ConnectionState.DISCONNECTED
        
    def test_connect_disconnect(self, adapter):
        adapter.connect()
        assert adapter.state() == ConnectionState.CONNECTED
        
        adapter.disconnect()
        assert adapter.state() == ConnectionState.STOPPED
        
    def test_capabilities(self, adapter):
        assert adapter.supports(adapter.capabilities)
        # Trading should not be enabled by default
        from crypto_trading_lab.exchanges.base.adapter import Capability
        assert not adapter.supports(Capability.TRADING)
        
    def test_trading_disabled_by_default(self, adapter):
        from crypto_trading_lab.exchanges.base.adapter import Capability
        assert not adapter.supports(Capability.TRADING)
        with pytest.raises(AdapterNotSupported):
            adapter.fetch_balances()
            
    def test_api_permissions(self, adapter):
        perms = adapter.check_api_permissions()
        assert perms['read'] is True
        assert perms['trade'] is False


def test_adapter_with_trading_enabled():
    adapter = BinanceRestAdapter(
        BINANCE_SPOT_TESTNET_ENDPOINTS,
        allow_trading=True,
        api_key="test_key",
        api_secret="test_secret"
    )
    assert adapter.supports(adapter.capabilities)  # Trading capability enabled
    assert adapter.supports(Capability.TRADING)

    # Regression: this used to call Binance for real, which fails with HTTP
    # 451 on geo-blocked CI runners and breaks the project's rule that the
    # suite stays offline. The transport is faked; the logic is what matters.
    with patch.object(
        BinanceRestAdapter, "_make_signed_request", return_value={}
    ):
        assert adapter.check_api_permissions() == {"read": True, "trade": True}

    from crypto_trading_lab.exchanges.errors import AdapterAuthenticationError

    with patch.object(
        BinanceRestAdapter,
        "_make_signed_request",
        side_effect=AdapterAuthenticationError("invalid key"),
    ):
        assert adapter.check_api_permissions() == {"read": True, "trade": False}


def test_adapter_health_store_optional(tmp_path):
    """Health store is disabled by default, enabled when path provided."""
    adapter = BinanceRestAdapter(BINANCE_SPOT_TESTNET_ENDPOINTS)
    assert adapter.health_store is None
    assert adapter.record_health_metrics() is None
    
    adapter2 = BinanceRestAdapter(
        BINANCE_SPOT_TESTNET_ENDPOINTS,
        health_store_path=tmp_path / "health.db",
    )
    assert adapter2.health_store is not None
    record = adapter2.record_health_metrics()
    assert record is not None


def test_market_parsing():
    """Test market parsing from exchange info."""
    adapter = BinanceRestAdapter(BINANCE_SPOT_TESTNET_ENDPOINTS)
    
        # Mock response
    mock_data = {
        'symbols': [
            {
                'symbol': 'BTCUSDT',
                'baseAsset': 'BTC',
                'quoteAsset': 'USDT',
                'status': 'TRADING',
                'filters': [
                    {'filterType': 'PRICE_FILTER', 'tickSize': '0.01'},
                    {'filterType': 'LOT_SIZE', 'minQty': '0.00001', 'stepSize': '0.00001'},
                    {'filterType': 'MIN_NOTIONAL', 'minNotional': '10'},
                ]
            }
        ]
    }
    
    with patch.object(adapter, '_make_request', return_value=mock_data):
        markets = adapter.fetch_markets()
        assert len(markets) == 1
        assert str(markets[0].symbol) == 'BTC/USDT'
        assert markets[0].min_notional is not None


def test_ticker_parsing():
    """Test ticker parsing."""
    adapter = BinanceRestAdapter(BINANCE_SPOT_TESTNET_ENDPOINTS)
    
    mock_data = {
        'symbol': 'BTCUSDT',
        'lastPrice': '50000.00',
        'bidPrice': '49999.00',
        'askPrice': '50001.00',
        'volume': '1234.56',
        'closeTime': 1234567890000,
    }
    
    with patch.object(adapter, '_make_request', return_value=mock_data):
        ticker = adapter.fetch_ticker(Symbol('BTC/USDT'))
        assert ticker.symbol == Symbol('BTC/USDT')
        assert ticker.last == 50000.00


def test_candle_parsing():
    """Test candle parsing."""
    adapter = BinanceRestAdapter(BINANCE_SPOT_TESTNET_ENDPOINTS)
    
    mock_data = [
        [
            1234567890000,  # open time
            '50000',  # open
            '51000',  # high
            '49000',  # low
            '50500',  # close
            '100',  # volume
            1234567900000,  # close time
            '...',  # quote asset volume
            100,  # number of trades
            '...',  # taker buy base asset volume
            '...',  # taker buy quote asset volume
            '...'   # ignore
        ]
    ]
    
    with patch.object(adapter, '_make_request', return_value=mock_data):
        candles = adapter.fetch_candles(Symbol('BTC/USDT'), '1m')
        assert len(candles) == 1
        assert candles[0].symbol == Symbol('BTC/USDT')
        assert candles[0].open == 50000
        assert candles[0].close == 50500


# Realistic exchangeInfo: Binance pads step and tick values with zeros.
EXCHANGE_INFO = {
    "symbols": [
        {
            "symbol": "BTCUSDT",
            "baseAsset": "BTC",
            "quoteAsset": "USDT",
            "status": "TRADING",
            "filters": [
                {"filterType": "PRICE_FILTER", "tickSize": "0.01000000"},
                {
                    "filterType": "LOT_SIZE",
                    "minQty": "0.00001000",
                    "stepSize": "0.00001000",
                },
                {"filterType": "MIN_NOTIONAL", "minNotional": "10.00000000"},
            ],
        }
    ]
}


def _trading_adapter():
    return BinanceRestAdapter(
        BINANCE_SPOT_TESTNET_ENDPOINTS,
        allow_trading=True,
        api_key="test_key",
        api_secret="test_secret",
    )


def _order_response(**overrides):
    data = {
        "orderId": 42,
        "symbol": "BTCUSDT",
        "side": "BUY",
        "type": "LIMIT",
        "status": "NEW",
        "origQty": "0.001",
        "executedQty": "0",
        "price": "50000.00",
        "time": 1700000000000,
    }
    data.update(overrides)
    return data


def _limit_request(**overrides):
    data = {
        "symbol": Symbol("BTC/USDT"),
        "side": OrderSide.BUY,
        "order_type": OrderType.LIMIT,
        "quantity": Decimal("0.001"),
        "price": Decimal("50000.00"),
    }
    data.update(overrides)
    return OrderRequest(**data)


@pytest.mark.parametrize(
    "text, expected",
    [("0.01000000", 2), ("0.00001000", 5), ("1.00000000", 0), ("0.5", 1)],
)
def test_decimal_places_of_a_step(text, expected):
    assert _decimal_places(text) == expected


def test_market_precision_comes_from_the_step_and_tick():
    adapter = BinanceRestAdapter(BINANCE_SPOT_TESTNET_ENDPOINTS)
    with patch.object(adapter, "_make_request", return_value=EXCHANGE_INFO):
        market = adapter.fetch_markets()[0]

    assert market.quantity_precision == 5
    assert market.price_precision == 2


def test_create_order_sends_a_valid_limit_order():
    adapter = _trading_adapter()
    with patch.object(adapter, "_make_request", return_value=EXCHANGE_INFO), patch.object(
        adapter, "_make_signed_request", return_value=_order_response()
    ) as signed:
        result = adapter.create_order(_limit_request())

    assert result.adapter_order_id == "42"
    assert result.status is OrderStatus.OPEN
    path, params = signed.call_args[0]
    assert path == "/api/v3/order"
    assert signed.call_args[1]["method"] == "POST"
    assert params["symbol"] == "BTCUSDT"
    assert params["quantity"] == "0.001"
    assert params["price"] == "50000.00"
    assert params["timeInForce"] == "GTC"


def test_create_order_accepts_a_market_order_without_a_price():
    # Regression: validation used to reject every market order with
    # "cannot check minimum order value without a price".
    adapter = _trading_adapter()
    request = OrderRequest(
        symbol=Symbol("BTC/USDT"),
        side=OrderSide.BUY,
        order_type=OrderType.MARKET,
        quantity=Decimal("0.001"),
    )
    with patch.object(adapter, "_make_request", return_value=EXCHANGE_INFO), patch.object(
        adapter,
        "_make_signed_request",
        return_value=_order_response(type="MARKET", price="0"),
    ) as signed:
        result = adapter.create_order(request)

    assert result.adapter_order_id == "42"
    assert "price" not in signed.call_args[0][1]


def test_create_order_rejects_a_quantity_below_the_minimum():
    adapter = _trading_adapter()
    with patch.object(adapter, "_make_request", return_value=EXCHANGE_INFO), patch.object(
        adapter, "_make_signed_request"
    ) as signed:
        with pytest.raises(AdapterInvalidOrder, match="below minimum"):
            adapter.create_order(_limit_request(quantity=Decimal("0.000001")))

    signed.assert_not_called()


def test_create_order_rejects_a_symbol_the_exchange_does_not_list():
    adapter = _trading_adapter()
    with patch.object(adapter, "_make_request", return_value=EXCHANGE_INFO), patch.object(
        adapter, "_make_signed_request"
    ) as signed:
        with pytest.raises(AdapterInvalidOrder, match="not a trading market"):
            adapter.create_order(_limit_request(symbol=Symbol("ETH/USDT")))

    signed.assert_not_called()


def test_market_metadata_is_fetched_once_across_orders():
    adapter = _trading_adapter()
    with patch.object(
        adapter, "_make_request", return_value=EXCHANGE_INFO
    ) as info, patch.object(
        adapter, "_make_signed_request", return_value=_order_response()
    ):
        adapter.create_order(_limit_request())
        adapter.create_order(_limit_request())

    assert info.call_count == 1


def _market(symbol="BTC/USDT"):
    return Market(
        exchange="binance",
        symbol=Symbol(symbol),
        base=symbol.split("/")[0],
        quote=symbol.split("/")[1],
        price_precision=2,
        quantity_precision=3,
        min_quantity=Decimal("0.001"),
        min_notional=Decimal("10"),
    )


def test_validate_order_request_accepts_a_matching_market():
    adapter = _trading_adapter()
    adapter._validate_order_request(_limit_request(), _market())


def test_validate_order_request_rejects_a_mismatched_symbol():
    adapter = _trading_adapter()
    with pytest.raises(AdapterInvalidOrder, match="symbol does not match"):
        adapter._validate_order_request(_limit_request(), _market("ETH/USDT"))

"""Tests for Binance adapter (ROADMAP chapters 26.2, 26)."""

import pytest
from unittest.mock import MagicMock, patch

from crypto_trading_lab.exchanges.binance.adapter import BinanceRestAdapter
from crypto_trading_lab.exchanges.binance.config import BINANCE_SPOT_TESTNET_ENDPOINTS
from crypto_trading_lab.domain.models import ConnectionState, Symbol
from crypto_trading_lab.exchanges.errors import AdapterNotSupported


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
    adapter = BinanceRestAdapter(BINANCE_SPOT_TESTNET_ENDPOINTS, allow_trading=True)
    assert adapter.supports(adapter.capabilities)  # Trading capability enabled
    
    perms = adapter.check_api_permissions()
    assert perms['trade'] is True


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

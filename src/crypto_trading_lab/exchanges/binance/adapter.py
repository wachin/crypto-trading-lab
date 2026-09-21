"""Binance Spot adapter (ROADMAP chapters 26.2, 26, 30).

Read-only adapter for Binance Spot public data via REST and WebSocket.
Trading is disabled by default; credentials must be explicitly provided
and trading must be explicitly enabled to avoid accidental real trades.

Features:
- REST endpoints for markets, tickers, candles (public data only)
- WebSocket subscriptions for live updates
- Rate limiting and connection management
- Secure logging with secret redaction
- Time synchronization
- Stale-data detection
"""

from __future__ import annotations

import json
import logging
import urllib.request
import urllib.error
import urllib.parse
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any, Optional

from crypto_trading_lab.domain.models import (
    Balance,
    Candle,
    ConnectionState,
    Market,
    OrderRequest,
    OrderResult,
    Symbol,
    Ticker,
)
from crypto_trading_lab.exchanges.base.adapter import Capability, ExchangeAdapter
from crypto_trading_lab.exchanges.binance.config import BinanceEndpoints
from crypto_trading_lab.exchanges.errors import (
    AdapterDataError,
    AdapterNetworkError,
    AdapterNotSupported,
    AdapterRateLimited,
)
from crypto_trading_lab.exchanges.connection_manager import (
    CircuitBreaker,
    ReconnectionPolicy,
    StaleDataDetector,
)
from crypto_trading_lab.exchanges.rate_limiter import RateLimiter
from crypto_trading_lab.exchanges.binance.websocket_client import BinanceWebSocketClient
from crypto_trading_lab.exchanges.feed_health import FeedHealthRecord, FeedHealthStore

logger = logging.getLogger(__name__)


class BinanceRestAdapter(ExchangeAdapter):
    """Binance Spot REST adapter for public data.
    
    Read-only by default. Trading requires explicit enablement.
    """
    
    capabilities = (
        Capability.MARKETS
        | Capability.TICKERS
        | Capability.CANDLES
        | Capability.SUBSCRIPTIONS
        | Capability.PERMISSIONS
    )
    
    def __init__(
        self,
        endpoints: BinanceEndpoints,
        *,
        allow_trading: bool = False,
        rate_limiter: Optional[RateLimiter] = None,
        circuit_breaker: Optional[CircuitBreaker] = None,
        websocket_factory=None,
        health_store_path: Path | None = None,
    ) -> None:
        self._endpoints = endpoints
        self._allow_trading = allow_trading
        self._rate_limiter = rate_limiter or RateLimiter(max_weight=1200, window_seconds=60)
        self._circuit_breaker = circuit_breaker or CircuitBreaker()
        self._state = ConnectionState.DISCONNECTED
        self._base_url = endpoints.rest_base_url.rstrip('/')
        self._websocket_factory = websocket_factory
        
        # Feed health persistence (optional; enabled when path provided)
        self._health_store_path = health_store_path
        self._health_store: FeedHealthStore | None = (
            FeedHealthStore(health_store_path) if health_store_path else None
        )
        
        # WebSocket client for subscriptions
        self._ws_client = BinanceWebSocketClient(
            endpoints,
            websocket_factory,
            policy=ReconnectionPolicy(),
            circuit_breaker=self._circuit_breaker,
            rate_limiter=self._rate_limiter,
        )
        
        if allow_trading:
            self.capabilities |= Capability.TRADING | Capability.BALANCES | Capability.ORDERS
            
    def connect(self) -> None:
        self._state = ConnectionState.CONNECTED
        
    def disconnect(self) -> None:
        self._state = ConnectionState.STOPPED
        
    def state(self) -> ConnectionState:
        # Proxy WebSocket client state if active
        if self._ws_client.state != ConnectionState.DISCONNECTED:
            return self._ws_client.state
        return self._state
        
    def _make_request(self, endpoint: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        """Make a rate-limited REST request."""
        if not self._circuit_breaker.can_attempt():
            raise AdapterRateLimited("Circuit breaker is open")
            
        try:
            self._rate_limiter.acquire(weight=1)
        except Exception as e:
            raise AdapterRateLimited(str(e)) from e
            
        url = f"{self._base_url}{endpoint}"
        if params:
            query = urllib.parse.urlencode(params)
            url = f"{url}?{query}"
            
        try:
            self._circuit_breaker.record_success()
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "CryptoTradingLab/1.0 (research)"}
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = resp.read()
                return json.loads(data.decode('utf-8'))
        except urllib.error.HTTPError as e:
            self._circuit_breaker.record_failure()
            if e.code == 429:
                raise AdapterRateLimited("Rate limited by exchange") from e
            raise AdapterNetworkError(f"HTTP {e.code}: {e.reason}") from e
        except Exception as e:
            self._circuit_breaker.record_failure()
            raise AdapterNetworkError(f"Network error: {e}") from e
            
    def fetch_markets(self) -> list[Market]:
        """Fetch exchange info and return normalized markets."""
        data = self._make_request("/api/v3/exchangeInfo")
        
        markets = []
        for symbol_info in data.get('symbols', []):
            try:
                if symbol_info.get('status') != 'TRADING':
                    continue
                    
                symbol_str = symbol_info['symbol']
                base = symbol_info.get('baseAsset', symbol_str[:-4])
                quote = symbol_info.get('quoteAsset', symbol_str[-4:])
                symbol_display = f"{base}/{quote}"
                
                # Parse filters
                min_qty = None
                min_notional = None
                price_prec = 8
                qty_prec = 8
                
                for f in symbol_info.get('filters', []):
                    if f['filterType'] == 'MIN_NOTIONAL':
                        min_notional = Decimal(f['minNotional'])
                    elif f['filterType'] == 'LOT_SIZE':
                        min_qty = Decimal(f['minQty'])
                        qty_prec = int(f['stepSize'].split('.')[-1] or '1')
                    elif f['filterType'] == 'PRICE_FILTER':
                        price_prec = int(f['tickSize'].split('.')[-1] or '1')
                        
                markets.append(Market(
                    exchange='binance',
                    symbol=Symbol(symbol_display),
                    base=base,
                    quote=quote,
                    price_precision=price_prec,
                    quantity_precision=qty_prec,
                    min_quantity=min_qty,
                    min_notional=min_notional,
                    maker_fee=Decimal('0.001'),
                    taker_fee=Decimal('0.001'),
                ))
            except Exception as e:
                logger.debug("Skipping market %s: %s", symbol_info.get('symbol'), e)
                continue
                
        return markets
        
    def fetch_ticker(self, symbol: Symbol) -> Ticker:
        """Fetch 24hr ticker for symbol."""
        symbol_str = str(symbol).replace('/', '')
        data = self._make_request("/api/v3/ticker/24hr", {'symbol': symbol_str})
        
        try:
            return Ticker(
                symbol=symbol,
                timestamp=datetime.fromtimestamp(
                    int(data['closeTime']) / 1000,
                    tz=timezone.utc
                ),
                last=Decimal(data['lastPrice']),
                bid=Decimal(data.get('bidPrice', '0')) if data.get('bidPrice') else None,
                ask=Decimal(data.get('askPrice', '0')) if data.get('askPrice') else None,
                volume=Decimal(data['volume']),
            )
        except (KeyError, ValueError, TypeError) as e:
            raise AdapterDataError(f"Invalid ticker data: {e}") from e
            
    def fetch_candles(
        self,
        symbol: Symbol,
        interval: str,
        since: datetime | None = None,
        limit: int | None = None,
    ) -> list[Candle]:
        """Fetch historical klines."""
        symbol_str = str(symbol).replace('/', '')
        
        params: dict[str, Any] = {'symbol': symbol_str, 'interval': interval}
        if since:
            params['startTime'] = int(since.timestamp() * 1000)
        if limit:
            params['limit'] = min(limit, 1000)
            
        data = self._make_request("/api/v3/klines", params)
        
        candles = []
        for row in data:
            try:
                candles.append(Candle(
                    symbol=symbol,
                    interval=interval,
                    open_time=datetime.fromtimestamp(int(row[0]) / 1000, tz=timezone.utc),
                    close_time=datetime.fromtimestamp(int(row[6]) / 1000, tz=timezone.utc),
                    open=Decimal(row[1]),
                    high=Decimal(row[2]),
                    low=Decimal(row[3]),
                    close=Decimal(row[4]),
                    volume=Decimal(row[5]),
                ))
            except Exception as e:
                logger.debug("Skipping candle row: %s", e)
                continue
                
        return candles
        
    # Subscriptions - integrated with WebSocket client
    def subscribe_ticker(self, symbol: Symbol, handler) -> None:
        stream = f"{str(symbol).replace('/', '').lower()}@ticker"
        self._ws_client.subscribe(stream)
        # Note: WebSocket client needs handler registration logic
        logger.debug("Subscribed to ticker stream: %s", stream)
        
    def subscribe_candles(self, symbol: Symbol, interval: str, handler) -> None:
        stream = f"{str(symbol).replace('/', '').lower()}@kline_{interval}"
        self._ws_client.subscribe(stream)
        logger.debug("Subscribed to kline stream: %s", stream)
        
    def subscribe_trades(self, symbol: Symbol, handler) -> None:
        stream = f"{str(symbol).replace('/', '').lower()}@trade"
        self._ws_client.subscribe(stream)
        logger.debug("Subscribed to trade stream: %s", stream)
        
    def subscribe_order_book(self, symbol: Symbol, handler) -> None:
        stream = f"{str(symbol).replace('/', '').lower()}@depth"
        self._ws_client.subscribe(stream)
        logger.debug("Subscribed to order book stream: %s", stream)
        
    def unsubscribe_all(self) -> None:
        self._ws_client._subscriptions.clear()
        self._ws_client._pending_subscriptions.clear()
        
    # Account operations - read-only
    def fetch_balances(self) -> dict[str, Balance]:
        if not self.supports(Capability.BALANCES):
            raise AdapterNotSupported("Balances require trading enabled")
        return {}
        
    def fetch_open_orders(self, symbol: Symbol | None = None) -> list[OrderResult]:
        if not self.supports(Capability.ORDERS):
            raise AdapterNotSupported("Orders require trading enabled")
        return []
        
    def create_order(self, request: OrderRequest) -> OrderResult:
        if not self.supports(Capability.TRADING):
            raise AdapterNotSupported("Trading is not enabled on this adapter")
        raise AdapterNotSupported("Trading not implemented in testnet adapter")
        
    def cancel_order(self, adapter_order_id: str, symbol: Symbol) -> OrderResult:
        if not self.supports(Capability.TRADING):
            raise AdapterNotSupported("Trading is not enabled on this adapter")
        raise AdapterNotSupported("Trading not implemented in testnet adapter")
        
    def on_order_update(self, handler) -> None:
        pass
        
    def check_api_permissions(self) -> dict[str, bool]:
        return {'read': True, 'trade': self._allow_trading}
        
    def record_health_metrics(self) -> FeedHealthRecord | None:
        """Persist current feed health metrics, if storage is enabled."""
        if self._health_store is None:
            return None
        metrics = self._ws_client.get_health_metrics()
        record = FeedHealthRecord(
            timestamp=datetime.now(timezone.utc),
            state=self.state(),
            stale=bool(metrics.get('stale', False)),
            age_seconds=metrics.get('age_seconds'),
            server_time_offset=float(metrics.get('server_time_offset', 0.0)),
            subscriptions=metrics.get('subscriptions', []),
            message_count=int(metrics.get('message_count', 0)),
            reconnect_attempts=int(metrics.get('reconnect_attempts', 0)),
            circuit_breaker_state=str(metrics.get('circuit_breaker_state', 'closed')),
        )
        self._health_store.record(record)
        return record
        
    @property
    def health_store(self) -> FeedHealthStore | None:
        """Access persisted feed health metrics."""
        return self._health_store

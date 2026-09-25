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
- Authenticated trading for testnet (HMAC-SHA256 signed requests)
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import random
import time
import urllib.request
import asyncio
import urllib.error
import urllib.parse
from functools import wraps
from collections import defaultdict
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any, Optional, Callable, TypeVar

from crypto_trading_lab.domain.models import (
    Balance,
    Candle,
    ConnectionState,
    Market,
    OrderRequest,
    OrderResult,
    OrderSide,
    OrderStatus,
    OrderType,
    Symbol,
    Ticker,
)
from crypto_trading_lab.exchanges.base.adapter import Capability, ExchangeAdapter, TickerHandler, CandleHandler, TradeHandler, OrderBookHandler
from crypto_trading_lab.exchanges.binance.config import BinanceEndpoints
from crypto_trading_lab.exchanges.errors import (
    AdapterAuthenticationError,
    AdapterDataError,
    AdapterInsufficientFunds,
    AdapterInvalidOrder,
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


# Retry helper with exponential backoff and jitter (ROADMAP chapter 27)
# Transient errors that should trigger a retry
_TRANSIENT_ERRORS = (
    urllib.error.URLError,
    ConnectionError,
    TimeoutError,
    OSError,
)

# HTTP status codes that are transient (5xx, 429)
_TRANSIENT_HTTP_CODES = {429, 500, 502, 503, 504}

# Default retry configuration
DEFAULT_MAX_RETRIES = 3
DEFAULT_BASE_DELAY = 1.0  # seconds
DEFAULT_MAX_DELAY = 30.0  # seconds
DEFAULT_JITTER = 0.2  # 20% jitter


def is_transient_error(error: Exception) -> bool:
    """Check if an error is transient and should trigger a retry."""
    if isinstance(error, _TRANSIENT_ERRORS):
        return True
    if isinstance(error, urllib.error.HTTPError):
        return error.code in _TRANSIENT_HTTP_CODES
    return False


T = TypeVar('T')


def with_retry(
    func: Callable[..., T],
    max_retries: int = DEFAULT_MAX_RETRIES,
    base_delay: float = DEFAULT_BASE_DELAY,
    max_delay: float = DEFAULT_MAX_DELAY,
    jitter: float = DEFAULT_JITTER,
) -> Callable[..., T]:
    """Decorator that adds exponential backoff retry for transient errors.

    Args:
        func: Function to wrap with retry logic
        max_retries: Maximum number of retry attempts
        base_delay: Initial delay in seconds
        max_delay: Maximum delay in seconds
        jitter: Jitter factor (0.0-1.0) for randomising delay

    Returns:
        Wrapped function with retry logic
    """
    @wraps(func)
    def wrapper(*args, **kwargs) -> T:
        attempt = 0
        while True:
            try:
                return func(*args, **kwargs)
            except Exception as e:
                if not is_transient_error(e):
                    raise
                if attempt >= DEFAULT_MAX_RETRIES:
                    logger.warning(
                        "Max retries (%d) exceeded for %s: %s",
                        DEFAULT_MAX_RETRIES, func.__name__, e
                    )
                    raise
                # Exponential backoff with jitter
                delay = min(DEFAULT_BASE_DELAY * (2 ** attempt), DEFAULT_MAX_DELAY)
                delay *= (1.0 + random.uniform(-DEFAULT_JITTER, DEFAULT_JITTER))
                logger.debug(
                    "Transient error in %s (attempt %d/%d): %s. Retrying in %.2fs",
                    func.__name__, attempt + 1, DEFAULT_MAX_RETRIES, e, delay
                )
                time.sleep(delay)
                attempt += 1
    return wrapper


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
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
    ) -> None:
        self._endpoints = endpoints
        self._allow_trading = allow_trading
        self._rate_limiter = rate_limiter or RateLimiter(max_weight=1200, window_seconds=60)
        self._circuit_breaker = circuit_breaker or CircuitBreaker()
        self._state = ConnectionState.DISCONNECTED
        self._base_url = endpoints.rest_base_url.rstrip('/')
        self._websocket_factory = websocket_factory
        
        # API credentials for authenticated requests
        self._api_key = api_key
        self._api_secret = api_secret
        
        # Feed health persistence (optional; enabled when path provided)
        self._health_store_path = health_store_path
        self._health_store: FeedHealthStore | None = (
            FeedHealthStore(health_store_path) if health_store_path else None
        )
        
        # Handler dictionaries for WebSocket subscriptions
        self._ticker_handlers: defaultdict[Symbol, list[TickerHandler]] = defaultdict(list)
        self._candle_handlers: defaultdict[tuple[Symbol, str], list[CandleHandler]] = defaultdict(list)
        self._trade_handlers: defaultdict[Symbol, list[TradeHandler]] = defaultdict(list)
        self._order_book_handlers: defaultdict[Symbol, list[OrderBookHandler]] = defaultdict(list)
        
        # WebSocket client for subscriptions
        self._ws_client = BinanceWebSocketClient(
            endpoints,
            websocket_factory,
            policy=ReconnectionPolicy(),
            circuit_breaker=self._circuit_breaker,
            rate_limiter=self._rate_limiter,
        )
        # Register internal handlers with the WebSocket client
        self._ws_client.add_ticker_handler(self._handle_ticker_message)
        self._ws_client.add_trade_handler(self._handle_trade_message)
        self._ws_client.add_candle_handler(self._handle_candle_message)
        # Note: order book handlers not yet implemented in WebSocket client
        
        if allow_trading:
            self.capabilities |= Capability.TRADING | Capability.BALANCES | Capability.ORDERS
            
    def connect(self) -> None:
        """Open the connection; start WebSocket client."""
        if self._ws_client.state == ConnectionState.DISCONNECTED:
            self._state = ConnectionState.CONNECTING
            # Start WebSocket client in background without blocking
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                # No running loop - we can't start the async client
                # This is a synchronous interface; the WS client will be started
                # when the application runs in an async context
                self._state = ConnectionState.CONNECTED
                return
            
            # Schedule the start coroutine
            loop.create_task(self._ws_client.start())
        self._state = ConnectionState.CONNECTED
        
    def disconnect(self) -> None:
        """Close the connection; stop WebSocket client."""
        try:
            loop = asyncio.get_running_loop()
            # Schedule the stop coroutine
            loop.create_task(self._ws_client.stop())
        except RuntimeError:
            # No running loop - nothing to do
            pass
        self._state = ConnectionState.STOPPED
        
    def state(self) -> ConnectionState:
        # Proxy WebSocket client state if active
        if self._ws_client.state != ConnectionState.DISCONNECTED:
            return self._ws_client.state
        return self._state
        
    # -- WebSocket internal message handlers ---------------------------------
    
    def _handle_ticker_message(self, payload: dict) -> None:
        """Convert Binance ticker payload to Ticker and dispatch to user handlers."""
        try:
            symbol_str = payload.get('s', '')
            if not symbol_str:
                return
            # Convert "BTCUSDT" -> "BTC/USDT"
            symbol = Symbol(symbol_str[:-4] + '/' + symbol_str[-4:])
            ticker = Ticker(
                symbol=symbol,
                timestamp=datetime.fromtimestamp(payload['E'] / 1000, tz=timezone.utc),
                last=Decimal(payload['c']),
                bid=Decimal(payload['b']) if payload.get('b') else None,
                ask=Decimal(payload['a']) if payload.get('a') else None,
                volume=Decimal(payload['v']) if payload.get('v') else None,
            )
            for handler in self._ticker_handlers.get(symbol, []):
                handler(ticker)
        except Exception as e:
            logger.debug("Error handling ticker message: %s", e)
    
    def _handle_trade_message(self, payload: dict) -> None:
        """Convert Binance trade payload to trade data and dispatch."""
        try:
            symbol_str = payload.get('s', '')
            if not symbol_str:
                return
            symbol = Symbol(symbol_str[:-4] + '/' + symbol_str[-4:])
            # We don't have a Trade domain model yet; pass raw payload
            for handler in self._trade_handlers.get(symbol, []):
                handler(payload)
        except Exception as e:
            logger.debug("Error handling trade message: %s", e)
    
    def _handle_candle_message(self, payload: dict) -> None:
        """Convert Binance kline payload to Candle and dispatch."""
        try:
            data = payload.get('k', {})
            symbol_str = data.get('s', '')
            if not symbol_str:
                return
            symbol = Symbol(symbol_str[:-4] + '/' + symbol_str[-4:])
            interval = data.get('i', '')
            if not interval:
                return
            # Only process closed candles (x = true)
            if not data.get('x', False):
                return
            candle = Candle(
                symbol=symbol,
                interval=interval,
                open_time=datetime.fromtimestamp(data['t'] / 1000, tz=timezone.utc),
                close_time=datetime.fromtimestamp(data['T'] / 1000, tz=timezone.utc),
                open=Decimal(data['o']),
                high=Decimal(data['h']),
                low=Decimal(data['l']),
                close=Decimal(data['c']),
                volume=Decimal(data['v']),
            )
            for handler in self._candle_handlers.get((symbol, interval), []):
                handler(candle)
        except Exception as e:
            logger.debug("Error handling candle message: %s", e)
        
    @with_retry
    def _make_request(self, endpoint: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        """Make a rate-limited REST request (public endpoint) with automatic retry."""
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
            
    @with_retry
    def _make_signed_request(self, endpoint: str, params: dict[str, Any] | None = None, method: str = "GET") -> dict[str, Any]:
        """Make a signed REST request for authenticated endpoints.
        
        Adds timestamp, signature, and API key header as required by Binance.
        """
        if not self._api_key or not self._api_secret:
            raise AdapterAuthenticationError("API key and secret required for authenticated endpoints")
            
        if not self._circuit_breaker.can_attempt():
            raise AdapterRateLimited("Circuit breaker is open")
            
        # Weight is higher for signed endpoints (typically 1-10 depending on endpoint)
        try:
            self._rate_limiter.acquire(weight=10)
        except Exception as e:
            raise AdapterRateLimited(str(e)) from e
            
        # Prepare parameters
        if params is None:
            params = {}
            
        # Add timestamp (in milliseconds)
        params['timestamp'] = int(time.time() * 1000)
        
        # Create query string for signature
        query_string = urllib.parse.urlencode(params)
        
        # Generate signature
        signature = hmac.new(
            self._api_secret.encode('utf-8'),
            query_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        # Add signature to params
        params['signature'] = signature
        
        # Build final query string with signature
        final_query = urllib.parse.urlencode(params)
        url = f"{self._base_url}{endpoint}?{final_query}"
        
        try:
            self._circuit_breaker.record_success()
            req = urllib.request.Request(
                url,
                method=method,
                headers={
                    "User-Agent": "CryptoTradingLab/1.0 (research)",
                    "X-MBX-APIKEY": self._api_key
                }
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = resp.read()
                return json.loads(data.decode('utf-8'))
        except urllib.error.HTTPError as e:
            self._circuit_breaker.record_failure()
            if e.code == 429:
                raise AdapterRateLimited("Rate limited by exchange") from e
            if e.code == 401:
                raise AdapterAuthenticationError("Invalid API key or signature") from e
            if e.code == 403:
                raise AdapterAuthenticationError("API key does not have required permissions") from e
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
    def subscribe_ticker(self, symbol: Symbol, handler: TickerHandler) -> None:
        stream = f"{str(symbol).replace('/', '').lower()}@ticker"
        self._ws_client.subscribe(stream)
        self._ticker_handlers[symbol].append(handler)
        logger.debug("Subscribed to ticker stream: %s", stream)
        
    def subscribe_candles(self, symbol: Symbol, interval: str, handler: CandleHandler) -> None:
        stream = f"{str(symbol).replace('/', '').lower()}@kline_{interval}"
        self._ws_client.subscribe(stream)
        self._candle_handlers[(symbol, interval)].append(handler)
        logger.debug("Subscribed to kline stream: %s", stream)
        
    def subscribe_trades(self, symbol: Symbol, handler: TradeHandler) -> None:
        stream = f"{str(symbol).replace('/', '').lower()}@trade"
        self._ws_client.subscribe(stream)
        self._trade_handlers[symbol].append(handler)
        logger.debug("Subscribed to trade stream: %s", stream)
        
    def subscribe_order_book(self, symbol: Symbol, handler: OrderBookHandler) -> None:
        stream = f"{str(symbol).replace('/', '').lower()}@depth"
        self._ws_client.subscribe(stream)
        self._order_book_handlers[symbol].append(handler)
        logger.debug("Subscribed to order book stream: %s", stream)
        
    def unsubscribe_all(self) -> None:
        self._ws_client._subscriptions.clear()
        self._ws_client._pending_subscriptions.clear()
        self._ticker_handlers.clear()
        self._candle_handlers.clear()
        self._trade_handlers.clear()
        self._order_book_handlers.clear()
        
    # Account operations - authenticated
    def fetch_balances(self) -> dict[str, Balance]:
        if not self.supports(Capability.BALANCES):
            raise AdapterNotSupported("Balances require trading enabled")
        if not self._api_key or not self._api_secret:
            raise AdapterAuthenticationError("API credentials required for balance query")
            
        data = self._make_signed_request("/api/v3/account")
        
        balances: dict[str, Balance] = {}
        try:
            for entry in data.get('balances', []):
                asset = entry['asset']
                free = Decimal(entry['free'])
                locked = Decimal(entry['locked'])
                if free > 0 or locked > 0:
                    balances[asset] = Balance(asset=asset, free=free, locked=locked)
        except (KeyError, ValueError, TypeError) as e:
            raise AdapterDataError(f"Invalid balance data: {e}") from e
        return balances
        
    def fetch_open_orders(self, symbol: Symbol | None = None) -> list[OrderResult]:
        if not self.supports(Capability.ORDERS):
            raise AdapterNotSupported("Orders require trading enabled")
        if not self._api_key or not self._api_secret:
            raise AdapterAuthenticationError("API credentials required for order query")
            
        params = {}
        if symbol:
            params['symbol'] = str(symbol).replace('/', '')
            
        data = self._make_signed_request("/api/v3/openOrders", params)
        
        return [self._parse_order(row) for row in data]
        
    def _parse_order(self, raw: dict[str, Any]) -> OrderResult:
        """Parse Binance order response into OrderResult."""
        try:
            status_raw = str(raw.get('status', 'NEW'))
            status_map = {
                'NEW': OrderStatus.OPEN,
                'PARTIALLY_FILLED': OrderStatus.PARTIALLY_FILLED,
                'FILLED': OrderStatus.FILLED,
                'CANCELED': OrderStatus.CANCELED,
                'REJECTED': OrderStatus.REJECTED,
                'EXPIRED': OrderStatus.EXPIRED,
            }
            status = status_map.get(status_raw, OrderStatus.OPEN)
            
            filled = Decimal(raw.get('executedQty', '0'))
            if status == OrderStatus.OPEN and filled > 0:
                status = OrderStatus.PARTIALLY_FILLED
                
            avg_price = raw.get('avgPrice') or raw.get('price')
            fee = Decimal('0')
            if 'commission' in raw:
                fee = Decimal(raw['commission'])
                
            timestamp = datetime.fromtimestamp(
                raw['time'] / 1000, tz=timezone.utc
            ) if 'time' in raw else datetime.now(timezone.utc)
            
            # Parse Binance symbol format (e.g., "BTCUSDT" -> "BTC/USDT")
            sym = raw['symbol']
            # Find the quote asset by checking common quote assets
            # This is a simplified approach; in production, use exchange info
            quote_assets = ['USDT', 'BUSD', 'USDC', 'BTC', 'ETH', 'BNB', 'EUR', 'GBP']
            base = sym
            quote = ''
            for qa in quote_assets:
                if sym.endswith(qa):
                    base = sym[:-len(qa)]
                    quote = qa
                    break
            symbol_display = f"{base}/{quote}"
            
            return OrderResult(
                adapter_order_id=str(raw['orderId']),
                client_order_id=raw.get('clientOrderId'),
                symbol=Symbol(symbol_display),
                side=OrderSide(raw['side'].lower()),
                order_type=OrderType(raw['type'].lower()),
                status=status,
                quantity=Decimal(raw['origQty']),
                filled_quantity=filled,
                average_price=Decimal(avg_price) if avg_price else None,
                fills=(),
                timestamp=timestamp,
                raw_status=status_raw,
            )
        except (KeyError, ValueError, TypeError) as e:
            raise AdapterDataError(f"Invalid order data: {e}") from e
        
    def create_order(self, request: OrderRequest) -> OrderResult:
        if not self.supports(Capability.TRADING):
            raise AdapterNotSupported("Trading is not enabled on this adapter")
        if not self._api_key or not self._api_secret:
            raise AdapterAuthenticationError("API credentials required for order placement")
            
        # Pre-trade validation (chapter 30)
        self._validate_order_request(request)
        
        params = {
            'symbol': str(request.symbol).replace('/', ''),
            'side': request.side.value.upper(),
            'type': request.order_type.value.upper(),
            'quantity': self._format_quantity(request.quantity),
        }
        
        if request.client_order_id:
            params['clientOrderId'] = request.client_order_id
            
        if request.order_type == OrderType.LIMIT:
            if request.price is None:
                raise AdapterInvalidOrder("Limit order requires price")
            params['price'] = self._format_price(request.price)
            params['timeInForce'] = 'GTC'
        elif request.order_type == OrderType.MARKET:
            if request.price is not None:
                raise AdapterInvalidOrder("Market order should not specify price")
                
        data = self._make_signed_request("/api/v3/order", params, method="POST")
        return self._parse_order(data)
        
    def cancel_order(self, adapter_order_id: str, symbol: Symbol) -> OrderResult:
        if not self.supports(Capability.TRADING):
            raise AdapterNotSupported("Trading is not enabled on this adapter")
        if not self._api_key or not self._api_secret:
            raise AdapterAuthenticationError("API credentials required for order cancellation")
            
        params = {
            'symbol': str(symbol).replace('/', ''),
            'orderId': adapter_order_id,
        }
        
        data = self._make_signed_request("/api/v3/order", params, method="DELETE")
        return self._parse_order(data)
        
    def _validate_order_request(self, request: OrderRequest, market: Market | None = None) -> None:
        """Pre-trade validation (chapter 30).
        
        Validates: tick size, step size, min notional, min quantity, 
        risk limits, data freshness, duplicate prevention.
        """
        if not self.supports(Capability.TRADING):
            raise AdapterNotSupported("trading is not enabled on this adapter (read-only mode)")
        if request.symbol != market.symbol if market else True:
            raise AdapterInvalidOrder("symbol does not match market")
            
        # Validate quantity precision (step size)
        if market:
            if market.min_quantity is not None and request.quantity < market.min_quantity:
                raise AdapterInvalidOrder(
                    f"quantity {request.quantity} below minimum {market.min_quantity}"
                )
            if market.min_notional is not None:
                price = request.price
                if price is None:
                    raise AdapterInvalidOrder(
                        "cannot check minimum order value without a price"
                    )
                notional = request.quantity * price
                if notional < market.min_notional:
                    raise AdapterInvalidOrder(
                        f"order value {notional} below minimum order value "
                        f"{market.min_notional}"
                    )
            # Validate price precision (tick size)
            if market.price_precision > 0 and request.price is not None:
                price_str = str(request.price)
                if '.' in price_str:
                    decimals = len(price_str.split('.')[1])
                    if decimals > market.price_precision:
                        raise AdapterInvalidOrder(
                            f"price {request.price} has more decimals ({decimals}) "
                            f"than allowed ({market.price_precision})"
                        )
            if market.quantity_precision > 0:
                qty_str = str(request.quantity)
                if '.' in qty_str:
                    decimals = len(qty_str.split('.')[1])
                    if decimals > market.quantity_precision:
                        raise AdapterInvalidOrder(
                            f"quantity {request.quantity} has more decimals ({decimals}) "
                            f"than allowed ({market.quantity_precision})"
                        )
        # TODO: Add risk limit checks, data freshness, duplicate prevention (idempotency)
        
    def _format_quantity(self, quantity: Decimal) -> str:
        """Format quantity to avoid scientific notation."""
        return format(quantity, 'f')
        
    def _format_price(self, price: Decimal) -> str:
        """Format price to avoid scientific notation."""
        return format(price, 'f')
        
    def _check_idempotency(self, client_order_id: str) -> bool:
        """Check if an order with this clientOrderId already exists (idempotency)."""
        # In a full implementation, this would check a persistent store
        # For now, we track in-memory to prevent duplicates in the same session
        if not hasattr(self, '_seen_client_order_ids'):
            self._seen_client_order_ids = set()
        if client_order_id in self._seen_client_order_ids:
            return False  # Duplicate detected
        self._seen_client_order_ids.add(client_order_id)
        return True
        
    def reconcile_orders(self) -> dict[str, Any]:
        """Reconcile local order state with exchange after reconnection.
        
        Returns a report of any discrepancies found.
        """
        if not self._api_key or not self._api_secret:
            return {'error': 'API credentials required for reconciliation'}
            
        try:
            # Fetch all open orders from exchange
            open_orders = self.fetch_open_orders()
            exchange_order_ids = {o.adapter_order_id for o in open_orders}
            
            # In a full implementation, compare with local state
            # For now, return the exchange state
            return {
                'reconciled_at': datetime.now(timezone.utc).isoformat(),
                'open_orders_count': len(open_orders),
                'exchange_order_ids': list(exchange_order_ids),
                'discrepancies': [],  # Would compare with local state
            }
        except Exception as e:
            logger.warning("Order reconciliation failed: %s", e)
            return {'error': str(e)}
        
    def on_order_update(self, handler) -> None:
        pass
        
    def check_api_permissions(self) -> dict[str, bool]:
        if not self._api_key or not self._api_secret:
            return {'read': True, 'trade': False}
        # Test by trying to fetch account info
        try:
            self._make_signed_request("/api/v3/account")
            return {'read': True, 'trade': True}
        except AdapterAuthenticationError:
            return {'read': True, 'trade': False}
        
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

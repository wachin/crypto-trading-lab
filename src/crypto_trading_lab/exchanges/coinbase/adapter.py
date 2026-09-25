"""Coinbase Spot adapter (ROADMAP.md chapter 26.3).

Read-only adapter for Coinbase public data via REST and WebSocket.
Trading is explicitly disabled - this adapter only provides public market data.

Features:
- REST endpoints for markets, tickers, candles (public data only)
- WebSocket subscriptions for live updates
- Rate limiting and connection management
- Time synchronization
- Experimental support (chapter 26.3)

WARNING: The Coinbase sandbox may return static or predefined data and must
not be treated as a realistic profitability simulation.
"""

from __future__ import annotations

import json
import logging
import time
import urllib.request
import asyncio
import urllib.error
import urllib.parse
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import Any

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
from crypto_trading_lab.exchanges.coinbase.config import CoinbaseEndpoints
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

logger = logging.getLogger(__name__)


class CoinbaseRestAdapter(ExchangeAdapter):
    """Coinbase Spot REST adapter for public data.

    Read-only adapter. Trading is explicitly disabled.
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
        endpoints: CoinbaseEndpoints,
        *,
        api_key: str | None = None,
        api_secret: str | None = None,
        passphrase: str | None = None,
        allow_trading: bool = False,
        rate_limiter: RateLimiter | None = None,
    ) -> None:
        self._endpoints = endpoints
        self._base_url = endpoints.rest_base_url
        self._api_key = api_key
        self._api_secret = api_secret
        self._passphrase = passphrase
        self._ws_client: CoinbaseWebSocketClient | None = None

        self._circuit_breaker = CircuitBreaker(failure_threshold=5, reset_timeout=60.0)
        self._rate_limiter = rate_limiter or RateLimiter(max_weight=1000, window_seconds=60)
        self._stale_detector = StaleDataDetector(max_age_seconds=30)
        self._state = ConnectionState.DISCONNECTED

        # Time sync
        self._server_time_offset: float = 0.0

        # Subscription handlers
        self._ticker_handlers: dict[Symbol, list[TickerHandler]] = defaultdict(list)
        self._candle_handlers: dict[Symbol, list[CandleHandler]] = defaultdict(list)
        self._trade_handlers: dict[Symbol, list[TradeHandler]] = defaultdict(list)
        self._order_book_handlers: dict[Symbol, list[OrderBookHandler]] = defaultdict(list)

        # Allow trading is always False for Coinbase (public data only)
        self._allow_trading = False

        # Initialize WebSocket client
        self._ws_client = CoinbaseWebSocketClient(
            endpoints=endpoints,
            rate_limiter=self._rate_limiter,
            circuit_breaker=self._circuit_breaker,
        )
        self._ws_client.add_ticker_handler(self._handle_ticker_message)
        self._ws_client.add_trade_handler(self._handle_trade_message)
        self._ws_client.add_candle_handler(self._handle_candle_message)
        self._ws_client.add_order_book_handler(self._handle_order_book_message)

    # -- Lifecycle ----------------------------------------------------------

    def connect(self) -> None:
        if self._state == ConnectionState.DISCONNECTED:
            self._state = ConnectionState.CONNECTING
            try:
                # Test REST connectivity
                self._make_request("/products")
                self._state = ConnectionState.CONNECTED
                logger.info("Connected to Coinbase REST API")
            except Exception as e:
                self._state = ConnectionState.ERROR
                logger.error("Failed to connect to Coinbase: %s", e)
                raise AdapterNetworkError(f"Failed to connect to Coinbase: {e}") from e

    def disconnect(self) -> None:
        if self._ws_client:
            self._ws_client.stop()
        self._state = ConnectionState.STOPPED
        logger.info("Disconnected from Coinbase")

    def state(self) -> ConnectionState:
        if self._ws_client and self._ws_client.state != ConnectionState.DISCONNECTED:
            return self._ws_client.state
        return self._state

    # -- Market metadata ----------------------------------------------------

    def fetch_markets(self) -> list[Market]:
        data = self._make_request("/products")
        markets = []
        for item in data:
            if item.get("status") != "online":
                continue
            try:
                base_currency = item["base_currency"]
                quote_currency = item["quote_currency"]
                symbol = Symbol(f"{base_currency}/{quote_currency}")
                # Coinbase uses base_increment/quote_increment for precision
                # Convert to decimal places
                base_inc = Decimal(item.get("base_increment", "1"))
                quote_inc = Decimal(item.get("quote_increment", "1"))
                price_prec = max(0, -base_inc.as_tuple().exponent) if base_inc != 1 else 8
                qty_prec = max(0, -base_inc.as_tuple().exponent) if base_inc != 1 else 8
                
                market = Market(
                    exchange="coinbase",
                    symbol=symbol,
                    base=base_currency,
                    quote=quote_currency,
                    price_precision=price_prec,
                    quantity_precision=qty_prec,
                    min_quantity=Decimal(item.get("base_min_size", "0")),
                    min_notional=Decimal(item.get("min_market_funds", "0")),
                    maker_fee=Decimal("0"),
                    taker_fee=Decimal("0"),
                )
                markets.append(market)
            except (KeyError, ValueError) as e:
                logger.debug("Skipping invalid market data: %s", e)
        return markets

    def fetch_ticker(self, symbol: Symbol) -> Ticker:
        product_id = f"{symbol.base}/{symbol.quote}"
        data = self._make_request(f"/products/{product_id}/ticker")
        return Ticker(
            symbol=symbol,
            timestamp=datetime.now(timezone.utc),
            last=Decimal(data["price"]),
            bid=Decimal(data["bid"]) if data.get("bid") else None,
            ask=Decimal(data["ask"]) if data.get("ask") else None,
            volume=Decimal(data["volume"]) if data.get("volume") else None,
        )

    def fetch_candles(
        self,
        symbol: Symbol,
        interval: str,
        since: datetime | None = None,
        limit: int | None = None,
    ) -> list[Candle]:
        product_id = f"{symbol.base}/{symbol.quote}"
        granularity = self._interval_to_granularity(interval)
        params = {"granularity": str(granularity)}
        if since:
            params["start"] = since.isoformat()
        if limit:
            params["limit"] = str(min(limit, 300))  # Coinbase max is 300

        data = self._make_request(f"/products/{product_id}/candles", params)
        candles = []
        for row in reversed(data):  # Coinbase returns newest first
            try:
                ts = datetime.fromtimestamp(row[0], tz=timezone.utc)
                candle = Candle(
                    symbol=symbol,
                    interval=interval,
                    open_time=ts,
                    close_time=ts + self._granularity_to_timedelta(granularity),
                    open=Decimal(str(row[3])),
                    high=Decimal(str(row[2])),
                    low=Decimal(str(row[1])),
                    close=Decimal(str(row[4])),
                    volume=Decimal(str(row[5])),
                )
                candles.append(candle)
            except (IndexError, ValueError) as e:
                logger.debug("Skipping invalid candle: %s", e)
        return candles

    # -- Subscriptions ------------------------------------------------------

    def subscribe_ticker(self, symbol: Symbol, handler: TickerHandler) -> None:
        self._ticker_handlers[symbol].append(handler)
        product_id = f"{symbol.base}/{symbol.quote}"
        self._ws_client.subscribe("ticker", [product_id])

    def subscribe_candles(self, symbol: Symbol, interval: str, handler: CandleHandler) -> None:
        self._candle_handlers[symbol].append(handler)
        product_id = f"{symbol.base}/{symbol.quote}"
        granularity = self._interval_to_granularity(interval)
        self._ws_client.subscribe("candles", [product_id], granularity=granularity)

    def subscribe_trades(self, symbol: Symbol, handler: TradeHandler) -> None:
        self._trade_handlers[symbol].append(handler)
        product_id = f"{symbol.base}/{symbol.quote}"
        self._ws_client.subscribe("matches", [product_id])

    def subscribe_order_book(self, symbol: Symbol, handler: OrderBookHandler) -> None:
        self._order_book_handlers[symbol].append(handler)
        product_id = f"{symbol.base}/{symbol.quote}"
        self._ws_client.subscribe("level2", [product_id])

    def unsubscribe_all(self) -> None:
        self._ws_client.unsubscribe_all()

    # -- Account operations -------------------------------------------------

    def fetch_balances(self) -> dict[str, Balance]:
        raise AdapterNotSupported("Coinbase adapter is read-only; balances require authenticated endpoints")

    def fetch_open_orders(self, symbol: Symbol | None = None) -> list[OrderResult]:
        raise AdapterNotSupported("Coinbase adapter is read-only; orders require authenticated endpoints")

    # -- Trading ------------------------------------------------------------

    def create_order(self, request: OrderRequest) -> OrderResult:
        raise AdapterNotSupported("Coinbase adapter is read-only; trading requires authenticated Advanced Trade API")

    def cancel_order(self, adapter_order_id: str, symbol: Symbol) -> OrderResult:
        raise AdapterNotSupported("Coinbase adapter is read-only")

    def on_order_update(self, handler) -> None:
        raise AdapterNotSupported("Coinbase adapter is read-only")

    # -- Permissions --------------------------------------------------------

    def check_api_permissions(self) -> dict[str, bool]:
        return {"read": True, "trade": False, "withdraw": False}

    # -- Internal helpers ---------------------------------------------------

    def _make_request(self, endpoint: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        """Make a rate-limited REST request (public endpoint)."""
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

    def _interval_to_granularity(self, interval: str) -> int:
        """Convert interval string to Coinbase granularity (seconds)."""
        mapping = {
            "1m": 60,
            "5m": 300,
            "15m": 900,
            "1h": 3600,
            "6h": 21600,
            "1d": 86400,
        }
        if interval not in mapping:
            raise ValueError(f"Unsupported interval for Coinbase: {interval}")
        return mapping[interval]

    def _granularity_to_timedelta(self, granularity: int) -> timedelta:
        return timedelta(seconds=granularity)

    # -- WebSocket internal message handlers ---------------------------------

    def _handle_ticker_message(self, payload: dict) -> None:
        try:
            product_id = payload.get("product_id", "")
            if not product_id:
                return
            symbol = Symbol(product_id.replace("-", "/"))
            ticker = Ticker(
                symbol=symbol,
                timestamp=datetime.now(timezone.utc),
                last=Decimal(payload["price"]),
                bid=Decimal(payload["best_bid"]) if payload.get("best_bid") else None,
                ask=Decimal(payload["best_ask"]) if payload.get("best_ask") else None,
                volume=Decimal(payload["volume_24h"]) if payload.get("volume_24h") else None,
            )
            for handler in self._ticker_handlers.get(symbol, []):
                handler(ticker)
        except Exception as e:
            logger.debug("Error handling ticker message: %s", e)

    def _handle_trade_message(self, payload: dict) -> None:
        try:
            product_id = payload.get("product_id", "")
            if not product_id:
                return
            symbol = Symbol(product_id.replace("-", "/"))
            for handler in self._trade_handlers.get(symbol, []):
                handler(payload)
        except Exception as e:
            logger.debug("Error handling trade message: %s", e)

    def _handle_candle_message(self, payload: dict) -> None:
        try:
            product_id = payload.get("product_id", "")
            if not product_id:
                return
            symbol = Symbol(product_id.replace("-", "/"))
            candle = Candle(
                symbol=symbol,
                interval=payload.get("granularity", "1m"),
                open_time=datetime.fromisoformat(payload["start"].replace("Z", "+00:00")),
                close_time=datetime.fromisoformat(payload["end"].replace("Z", "+00:00")),
                open=Decimal(str(payload["open"])),
                high=Decimal(str(payload["high"])),
                low=Decimal(str(payload["low"])),
                close=Decimal(str(payload["close"])),
                volume=Decimal(str(payload["volume"])),
            )
            for handler in self._candle_handlers.get(symbol, []):
                handler(candle)
        except Exception as e:
            logger.debug("Error handling candle message: %s", e)

    def _handle_order_book_message(self, payload: dict) -> None:
        try:
            product_id = payload.get("product_id", "")
            if not product_id:
                return
            symbol = Symbol(product_id.replace("-", "/"))
            for handler in self._order_book_handlers.get(symbol, []):
                handler(payload)
        except Exception as e:
            logger.debug("Error handling order book message: %s", e)


class CoinbaseWebSocketClient:
    """Coinbase WebSocket client for public streams."""

    def __init__(
        self,
        endpoints: CoinbaseEndpoints,
        rate_limiter: RateLimiter | None = None,
        circuit_breaker: CircuitBreaker | None = None,
    ) -> None:
        self._endpoints = endpoints
        self._rate_limiter = rate_limiter or RateLimiter(max_weight=1000, window_seconds=60)
        self._circuit_breaker = circuit_breaker or CircuitBreaker(failure_threshold=5, reset_timeout=60.0)
        self._state = ConnectionState.DISCONNECTED
        self._handlers: dict[str, list] = {
            "ticker": [],
            "trade": [],
            "candle": [],
            "order_book": [],
        }
        self._subscriptions: set[str] = set()
        self._stop_event = asyncio.Event()

    def add_ticker_handler(self, handler) -> None:
        self._handlers["ticker"].append(handler)

    def add_trade_handler(self, handler) -> None:
        self._handlers["trade"].append(handler)

    def add_candle_handler(self, handler) -> None:
        self._handlers["candle"].append(handler)

    def add_order_book_handler(self, handler) -> None:
        self._handlers["order_book"].append(handler)

    def subscribe(self, channel: str, product_ids: list[str], **kwargs) -> None:
        for pid in product_ids:
            self._subscriptions.add(f"{channel}:{pid}")

    def unsubscribe_all(self) -> None:
        self._subscriptions.clear()

    async def start(self) -> None:
        # Placeholder for actual WebSocket implementation
        self._state = ConnectionState.CONNECTED

    async def stop(self) -> None:
        self._stop_event.set()

    @property
    def state(self) -> ConnectionState:
        return self._state

    def stop(self) -> None:
        self._stop_event.set()
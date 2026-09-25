"""CCXT-backed adapter implementation.

Design rules (from the CCXT reference study, Part D of
``docs/en/developers/reference-projects.md``, and ROADMAP.md chapter 26):

- CCXT is **injected**, never imported at module load: this module stays
  importable (and fully testable with a fake client) without ccxt
  installed, and no automated test performs network calls (chapter 14).
- CCXT types never leak into the domain: every response is normalized
  into ``crypto_trading_lab.domain.models`` (chapter 7).
- The adapter is read-only unless trading is explicitly enabled
  (chapters 60/61: capital protection first).

Error mapping uses the exception *class name* of the injected client, so
it behaves identically against real ccxt and against test doubles.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from functools import wraps
from typing import Any, Callable, Protocol, TypeVar
import asyncio
import json
import logging
import random
import time

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
from crypto_trading_lab.exchanges.base.adapter import (
    Capability,
    ExchangeAdapter,
)
from crypto_trading_lab.exchanges.errors import (
    AdapterAuthenticationError,
    AdapterDataError,
    AdapterError,
    AdapterInsufficientFunds,
    AdapterInvalidOrder,
    AdapterNetworkError,
    AdapterNotSupported,
    AdapterRateLimited,
    AdapterRequestError,
    suggest_connection_state,
)
from crypto_trading_lab.exchanges.connection_manager import (
    CircuitBreaker,
    CircuitState,
    ReconnectionPolicy,
    StaleDataDetector,
)
from crypto_trading_lab.exchanges.rate_limiter import RateLimiter
from crypto_trading_lab.exchanges.binance.websocket_client import BinanceWebSocketClient
from crypto_trading_lab.exchanges.feed_health import FeedHealthRecord, FeedHealthStore

logger = logging.getLogger(__name__)
from crypto_trading_lab.exchanges.binance.websocket_client import BinanceWebSocketClient

__all__ = ["CcxtExchangeAdapter", "map_client_error", "CcxtWebSocketClient"]

#: ccxt ``precisionMode`` constant values (from ccxt.base.decimal_to_precision).
_PRECISION_TICK_SIZE = 1
_PRECISION_DECIMAL_PLACES = 2

#: Interval string to seconds for deriving candle close times from ccxt's
#: open-only timestamps. Unknown intervals default to one minute.
_INTERVAL_SECONDS: dict[str, int] = {
    "1m": 60,
    "3m": 180,
    "5m": 300,
    "15m": 900,
    "30m": 1800,
    "1h": 3600,
    "2h": 7200,
    "4h": 14400,
    "6h": 21600,
    "8h": 28800,
    "12h": 43200,
    "1d": 86400,
    "3d": 259200,
    "1w": 604800,
    "1M": 2629800,  # ~30.44 days; exchanges vary on month boundaries
}

#: Exception class names that map onto domain errors. Names rather than
#: classes so that no ccxt import is required; the names were verified in
#: the CCXT reference study (Part D of reference-projects.md).
_ERROR_NAME_MAP: dict[str, type[AdapterError]] = {
    "RateLimitExceeded": AdapterRateLimited,
    "DDoSProtection": AdapterRateLimited,
    "ExchangeNotAvailable": AdapterNetworkError,
    "ExchangeUnavailable": AdapterNetworkError,
    "RequestTimeout": AdapterNetworkError,
    "ConnectionError": AdapterNetworkError,
    "AuthenticationError": AdapterAuthenticationError,
    "PermissionDenied": AdapterAuthenticationError,
    "AccountSuspended": AdapterAuthenticationError,
    "InsufficientFunds": AdapterInsufficientFunds,
    "InvalidOrder": AdapterInvalidOrder,
    "BadSymbol": AdapterInvalidOrder,
    "BadRequest": AdapterRequestError,
    "BadResponse": AdapterDataError,
    "NetworkError": AdapterNetworkError,
    "ExchangeError": AdapterRequestError,
}


# Retry helper with exponential backoff and jitter (ROADMAP chapter 27)
# Transient errors that should trigger a retry
_TRANSIENT_ERRORS = (
    TimeoutError,
    ConnectionError,
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
    # Check for transient exception types
    if any(isinstance(error, err_type) for err_type in _TRANSIENT_ERRORS):
        return True
    # Check for transient HTTP status codes
    code = getattr(error, 'code', None)
    if isinstance(code, int) and code in _TRANSIENT_HTTP_CODES:
        return True
    # Check for CCXT-specific transient errors by name
    error_name = type(error).__name__
    if error_name in _ERROR_NAME_MAP:
        mapped = _ERROR_NAME_MAP[error_name]
        # Rate limits and network errors are transient
        if mapped in (AdapterRateLimited, AdapterNetworkError):
            return True
    return False


T = TypeVar('T')


def with_retry(
    func: Callable[..., T],
    max_retries: int = DEFAULT_MAX_RETRIES,
    base_delay: float = DEFAULT_BASE_DELAY,
    max_delay: float = DEFAULT_MAX_DELAY,
    jitter: float = DEFAULT_JITTER,
) -> Callable[..., T]:
    """Decorator that adds exponential backoff retry for transient errors."""
    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        attempt = 0
        while True:
            try:
                return func(*args, **kwargs)
            except Exception as e:
                if not is_transient_error(e):
                    raise
                if attempt >= DEFAULT_MAX_RETRIES:
                    raise
                # Exponential backoff with jitter
                delay = min(DEFAULT_BASE_DELAY * (2 ** attempt), DEFAULT_MAX_DELAY)
                delay *= (1.0 + random.uniform(-DEFAULT_JITTER, DEFAULT_JITTER))
                time.sleep(delay)
                attempt += 1
    return wrapper


class MessageTracker:
    """Track processed message IDs to detect duplicates and out-of-order delivery."""
    
    def __init__(self, max_size: int = 10000) -> None:
        self._seen_ids: set[int] = set()
        self._last_sequence: int | None = None
        self._max_size: int = max_size
        
    def is_duplicate(self, msg_id: int) -> bool:
        return msg_id in self._seen_ids
    
    def is_out_of_order(self, msg_id: int) -> bool:
        if self._last_sequence is None:
            return False
        return msg_id < self._last_sequence
    
    def record(self, msg_id: int) -> tuple[bool, bool]:
        """Return (is_duplicate, is_out_of_order) and record the message."""
        is_dup = self.is_duplicate(msg_id)
        is_oos = self.is_out_of_order(msg_id)
        
        if not is_dup:
            self._seen_ids.add(msg_id)
            # Prune old entries to prevent unbounded growth
            if len(self._seen_ids) > self._max_size:
                # Remove oldest 10%
                to_remove = list(self._seen_ids)[:self._max_size // 10]
                for old_id in to_remove:
                    self._seen_ids.discard(old_id)
        
        if msg_id > (self._last_sequence or -1):
            self._last_sequence = msg_id
            
        return is_dup, is_oos


class CcxtClient(Protocol):
    """Structural description of the ccxt surface this adapter uses.

    Any object exposing these methods works — real ``ccxt.binance()`` or
    a test double. Nothing here is ccxt-specific beyond these calls.
    """

    def fetch_markets(self) -> list[dict[str, Any]]: ...

    def fetch_ticker(self, symbol: str) -> dict[str, Any]: ...

    def fetch_ohlcv(
        self, symbol: str, timeframe: str, since: int | None, limit: int | None
    ) -> list[list[Any]]: ...

    def fetch_balance(self) -> dict[str, Any]: ...

    def fetch_open_orders(self, symbol: str | None) -> list[dict[str, Any]]: ...

    def create_order(
        self,
        symbol: str,
        type: str,
        side: str,
        amount: float,
        price: float | None,
        params: dict[str, Any],
    ) -> dict[str, Any]: ...

    def cancel_order(self, id: str, symbol: str) -> dict[str, Any]: ...


def map_client_error(exc: Exception) -> AdapterError:
    """Translate any client exception into the domain error taxonomy."""
    if isinstance(exc, AdapterError):
        return exc
    mapped = _ERROR_NAME_MAP.get(type(exc).__name__)
    if mapped is not None:
        return mapped(f"{type(exc).__name__}: {exc}")
    return AdapterRequestError(f"{type(exc).__name__}: {exc}")


def _decimal(value: Any) -> Decimal:
    """Convert a numeric JSON value into Decimal without float artifacts."""
    return Decimal(str(value))


def _ms_to_utc(ms: Any) -> datetime:
    """Convert a millisecond Unix timestamp into aware UTC datetime."""
    return datetime.fromtimestamp(int(ms) / 1000, tz=timezone.utc)


def _decimals_of(value: Any, precision_mode: int) -> int:
    """Normalize ccxt market precision into a number of decimal places.

    ``DECIMAL_PLACES`` markets declare the number of decimals directly;
    ``TICK_SIZE`` markets declare the smallest increment (e.g. ``0.01``),
    from which the number of decimals is derived. This keeps chapter 30's
    normalization inside the adapter, not the domain.
    """
    if value is None:
        return 8
    if precision_mode == _PRECISION_TICK_SIZE:
        exponent = Decimal(str(value)).normalize().as_tuple().exponent
        return max(0, -int(exponent))
    return max(0, int(value))


class CcxtExchangeAdapter(ExchangeAdapter):
    """Adapter delegating to an injected ccxt client instance.

    Parameters
    ----------
    client:
        A ccxt exchange instance (or compatible double). The caller is
        responsible for configuration; credentials must come from the
        credential store (chapter 9), never be hardcoded here.
    allow_trading:
        Read-only by default. Order operations raise
        :class:`AdapterNotSupported` unless this is explicitly True.
    """

    _BASE_CAPABILITIES = (
        Capability.MARKETS
        | Capability.TICKERS
        | Capability.CANDLES
        | Capability.SUBSCRIPTIONS
        | Capability.BALANCES
        | Capability.ORDERS
        | Capability.PERMISSIONS
    )

    def __init__(
        self,
        client: CcxtClient,
        *,
        allow_trading: bool = False,
        rate_limiter: RateLimiter | None = None,
        circuit_breaker: CircuitBreaker | None = None,
        stale_detector: StaleDataDetector | None = None,
    ) -> None:
        self._client = client
        self.capabilities = self._BASE_CAPABILITIES
        if allow_trading:
            self.capabilities |= Capability.TRADING
        self._state = ConnectionState.DISCONNECTED
        self._ticker_handlers: list[Any] = []
        self._candle_handlers: list[Any] = []
        self._trade_handlers: list[Any] = []
        self._book_handlers: list[Any] = []
        self._order_update_handlers: list[Any] = []

        # Infrastructure integration
        self._rate_limiter = rate_limiter or RateLimiter(max_weight=1200, window_seconds=60)
        self._circuit_breaker = circuit_breaker or CircuitBreaker(failure_threshold=5, reset_timeout=60.0)
        self._stale_detector = stale_detector or StaleDataDetector(max_age_seconds=30)
        self._allow_trading = allow_trading

    # ------------------------------------------------------------------
    # Error wrapping and state transitions
    # ------------------------------------------------------------------
    def _call(self, method_name: str, *args: Any, **kwargs: Any) -> Any:
        method = getattr(self._client, method_name, None)
        if method is None:
            raise AdapterDataError(
                f"client does not provide {method_name!r}; is this a "
                "compatible ccxt instance?"
            )
        
        # Circuit breaker check
        if not self._circuit_breaker.can_attempt():
            raise AdapterRateLimited("Circuit breaker is open")
        
        # Rate limiter
        try:
            self._rate_limiter.acquire(weight=1)
        except Exception as e:
            raise AdapterRateLimited(str(e)) from e
        
        # Execute with retry logic
        attempt = 0
        while True:
            try:
                result = method(*args, **kwargs)
                self._circuit_breaker.record_success()
                return result
            except AdapterError:
                raise
            except Exception as exc:
                # Check if this is a transient error that should be retried
                if is_transient_error(exc) and attempt < DEFAULT_MAX_RETRIES:
                    # Exponential backoff with jitter
                    delay = min(DEFAULT_BASE_DELAY * (2 ** attempt), DEFAULT_MAX_DELAY)
                    delay *= (1.0 + random.uniform(-DEFAULT_JITTER, DEFAULT_JITTER))
                    time.sleep(delay)
                    attempt += 1
                    continue
                # Non-transient error or max retries exceeded
                self._circuit_breaker.record_failure()
                mapped = map_client_error(exc)
                self._state = suggest_connection_state(mapped)
                raise mapped from exc

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------
    def connect(self) -> None:
        # REST clients are stateless; the full state machine with
        # backoff, circuit breaker, and WS reconnection is chapter 27
        # and lands with the WebSocket integration.
        self._state = ConnectionState.CONNECTED

    def disconnect(self) -> None:
        self._state = ConnectionState.STOPPED

    def state(self) -> ConnectionState:
        return self._state

    # ------------------------------------------------------------------
    # Market data
    # ------------------------------------------------------------------
    def fetch_markets(self) -> list[Market]:
        mode = getattr(self._client, "precisionMode", _PRECISION_DECIMAL_PLACES)
        exchange_name = str(getattr(self._client, "id", ""))
        markets: list[Market] = []
        for raw in self._call("fetch_markets") or []:
            try:
                markets.append(self._parse_market(raw, mode, exchange_name))
            except (KeyError, ValueError, TypeError) as exc:
                raise AdapterDataError(f"unparsable market entry: {exc}") from exc
        return markets

    def _parse_market(
        self, raw: dict[str, Any], mode: int, exchange_name: str
    ) -> Market:
        limits = raw.get("limits") or {}
        amount_limits = limits.get("amount") or {}
        cost_limits = limits.get("cost") or {}
        fees = (raw.get("fees") or {}).get("trading") or {}
        precision = raw.get("precision") or {}
        min_qty = amount_limits.get("min")
        min_cost = cost_limits.get("min")
        maker = fees.get("maker")
        taker = fees.get("taker")
        return Market(
            exchange=str(raw.get("exchange") or exchange_name),
            symbol=Symbol(raw["symbol"]),
            base=str(raw.get("base", raw["symbol"].split("/")[0])),
            quote=str(raw.get("quote", raw["symbol"].split("/")[1])),
            price_precision=_decimals_of(precision.get("price"), mode),
            quantity_precision=_decimals_of(precision.get("amount"), mode),
            min_quantity=_decimal(min_qty) if min_qty is not None else None,
            min_notional=_decimal(min_cost) if min_cost is not None else None,
            maker_fee=_decimal(maker) if maker is not None else None,
            taker_fee=_decimal(taker) if taker is not None else None,
        )

    def fetch_ticker(self, symbol: Symbol) -> Ticker:
        raw = self._call("fetch_ticker", str(symbol))
        return self._parse_ticker(raw, symbol)

    def _parse_ticker(self, raw: dict[str, Any], symbol: Symbol) -> Ticker:
        try:
            last = raw.get("last") or raw.get("close")
            if last is None:
                raise AdapterDataError(f"ticker for {symbol} has no last price")
            bid, ask = raw.get("bid"), raw.get("ask")
            volume = raw.get("volume") or raw.get("baseVolume")
            return Ticker(
                symbol=symbol,
                timestamp=(
                    _ms_to_utc(raw["timestamp"])
                    if raw.get("timestamp")
                    else datetime.now(tz=timezone.utc)
                ),
                last=_decimal(last),
                bid=_decimal(bid) if bid is not None else None,
                ask=_decimal(ask) if ask is not None else None,
                volume=_decimal(volume) if volume is not None else None,
            )
        except AdapterError:
            raise
        except (KeyError, ValueError, TypeError) as exc:
            raise AdapterDataError(f"unparsable ticker: {exc}") from exc

    def dispatch_ticker(self, raw: dict[str, Any]) -> Ticker:
        """Normalize one raw ticker payload and deliver it to subscribers.

        Public seam for the future polling/streaming loop (chapters 12
        and 27) and for deterministic tests without network access.
        """
        symbol = Symbol(str(raw["symbol"]))
        ticker = self._parse_ticker(raw, symbol)
        for handler in self._ticker_handlers:
            handler(ticker)
        return ticker

    def fetch_candles(
        self,
        symbol: Symbol,
        interval: str,
        since: datetime | None = None,
        limit: int | None = None,
    ) -> list[Candle]:
        since_ms = int(since.timestamp() * 1000) if since is not None else None
        rows = self._call("fetch_ohlcv", str(symbol), interval, since_ms, limit) or []
        candles: list[Candle] = []
        # ccxt OHLCV rows carry only the bar-open timestamp; the close
        # time is derived from the interval so domain validation holds.
        interval_seconds = _INTERVAL_SECONDS.get(interval)
        for row in rows:
            try:
                open_ms, o, h, low, c, v = row
                open_time = _ms_to_utc(open_ms)
                if interval_seconds is not None:
                    close_time = open_time + timedelta(seconds=interval_seconds)
                else:
                    close_time = open_time + timedelta(seconds=60)
                candles.append(
                    Candle(
                        symbol=symbol,
                        interval=interval,
                        open_time=open_time,
                        close_time=close_time,
                        open=_decimal(o),
                        high=_decimal(h),
                        low=_decimal(low),
                        close=_decimal(c),
                        volume=_decimal(v),
                    )
                )
            except (KeyError, ValueError, TypeError) as exc:
                raise AdapterDataError(f"unparsable candle row: {exc}") from exc
        candles.sort(key=lambda candle: candle.open_time)
        return candles

    # ------------------------------------------------------------------
    # Subscriptions
    # ------------------------------------------------------------------
    def subscribe_ticker(self, symbol: Symbol, handler) -> None:
        self._ticker_handlers.append(handler)

    def subscribe_candles(self, symbol: Symbol, interval: str, handler) -> None:
        self._candle_handlers.append(handler)

    def subscribe_trades(self, symbol: Symbol, handler) -> None:
        self._trade_handlers.append(handler)

    def subscribe_order_book(self, symbol: Symbol, handler) -> None:
        self._book_handlers.append(handler)

    def unsubscribe_all(self) -> None:
        self._ticker_handlers.clear()
        self._candle_handlers.clear()
        self._trade_handlers.clear()
        self._book_handlers.clear()

    # NOTE: live streaming via ``ccxt.pro`` (``watch_*``) requires the
    # asyncio bridge of chapter 12 and the reconnection machinery of
    # chapter 27; it is deliberately out of scope for this spike. The
    # handler registries above are the seam where polling/streaming will
    # publish normalized updates.

    # ------------------------------------------------------------------
    # Account
    # ------------------------------------------------------------------
    def fetch_balances(self) -> dict[str, Balance]:
        raw = self._call("fetch_balance")
        balances: dict[str, Balance] = {}
        try:
            for asset, entry in raw.items():
                if asset in ("free", "used", "total") or not isinstance(entry, dict):
                    continue  # skip aggregate views ccxt adds
                free = entry.get("free")
                used = entry.get("used")
                if free is None:
                    continue
                balances[asset] = Balance(
                    asset=asset,
                    free=_decimal(free),
                    locked=_decimal(used) if used is not None else Decimal("0"),
                )
        except (ValueError, TypeError) as exc:
            raise AdapterDataError(f"unparsable balances: {exc}") from exc
        return balances

    def fetch_open_orders(self, symbol: Symbol | None = None) -> list[OrderResult]:
        raw_symbol = str(symbol) if symbol is not None else None
        rows = self._call("fetch_open_orders", raw_symbol) or []
        return [self._parse_order(row) for row in rows]

    # ------------------------------------------------------------------
    # Trading
    # ------------------------------------------------------------------
    def on_order_update(self, handler) -> None:
        self._order_update_handlers.append(handler)

    def _emit_order_update(self, result: OrderResult) -> None:
        for handler in self._order_update_handlers:
            handler(result)

    def check_api_permissions(self) -> dict[str, bool]:
        # Probing the private balance endpoint verifies read access;
        # trade permission is reported from the declared capability
        # until exchange permission endpoints are wired (later phase).
        self._call("fetch_balance")
        return {"read": True, "trade": self.supports(Capability.TRADING)}

    def create_order(self, request: OrderRequest) -> OrderResult:
        if not self.supports(Capability.TRADING):
            raise AdapterNotSupported(
                "trading is not enabled on this adapter (read-only mode)"
            )
        params: dict[str, Any] = {}
        if request.client_order_id:
            params["clientOrderId"] = request.client_order_id
        raw = self._call(
            "create_order",
            str(request.symbol),
            request.order_type.value,
            request.side.value,
            float(request.quantity),
            float(request.price) if request.price is not None else None,
            params,
        )
        result = self._parse_order(raw)
        self._emit_order_update(result)
        return result

    def cancel_order(self, adapter_order_id: str, symbol: Symbol) -> OrderResult:
        raw = self._call("cancel_order", adapter_order_id, str(symbol))
        result = self._parse_order(raw)
        self._emit_order_update(result)
        return result

    # ------------------------------------------------------------------
    # Normalization helpers
    # ------------------------------------------------------------------
    _STATUS_MAP = {
        "open": OrderStatus.OPEN,
        "closed": OrderStatus.FILLED,
        "canceled": OrderStatus.CANCELED,
        "cancelled": OrderStatus.CANCELED,
        "expired": OrderStatus.EXPIRED,
        "rejected": OrderStatus.REJECTED,
    }

    def _parse_order(self, raw: dict[str, Any]) -> OrderResult:
        try:
            status_raw = str(raw.get("status", "open"))
            status = self._STATUS_MAP.get(status_raw, OrderStatus.OPEN)
            filled = _decimal(raw.get("filled") or 0)
            if status is OrderStatus.OPEN and filled > 0:
                status = OrderStatus.PARTIALLY_FILLED
            average = raw.get("average") or raw.get("price")
            fee_entry = raw.get("fee") or {}
            fee_value = fee_entry.get("cost") if isinstance(fee_entry, dict) else None
            fee_asset = fee_entry.get("currency") if isinstance(fee_entry, dict) else None
            timestamp = _ms_to_utc(raw["timestamp"]) if raw.get("timestamp") else datetime.now(tz=timezone.utc)
            return OrderResult(
                adapter_order_id=str(raw["id"]),
                client_order_id=raw.get("clientOrderId"),
                symbol=Symbol(raw["symbol"]),
                side=OrderSide(str(raw.get("side", "buy"))),
                order_type=OrderType(str(raw.get("type", "limit"))),
                status=status,
                quantity=_decimal(raw.get("amount") or 0),
                filled_quantity=filled,
                average_price=_decimal(average) if average is not None else None,
                fills=(),  # per-fill normalization arrives with Trade model
                timestamp=timestamp,
                raw_status=status_raw,
            )
        except AdapterError:
            raise
        except (KeyError, ValueError, TypeError) as exc:
            raise AdapterDataError(f"unparsable order: {exc}") from exc


class CcxtWebSocketClient:
    """WebSocket client for CCXT exchanges using the websockets library.
    
    Provides live market data streaming for exchanges supported by ccxt,
    using the standard websockets library. Integrates with the existing
    infrastructure: circuit breaker, rate limiter, stale data detector,
    and retry/backoff infrastructure.
    
    Currently supports Binance Spot public streams.
    """
    
    def __init__(
        self,
        exchange_id: str,
        endpoints: Any,  # BinanceEndpoints-like object with websocket_base_url
        *,
        rate_limiter: RateLimiter | None = None,
        circuit_breaker: CircuitBreaker | None = None,
        stale_detector: StaleDataDetector | None = None,
    ) -> None:
        self._exchange_id = exchange_id
        self._endpoints = endpoints
        self._rate_limiter = rate_limiter or RateLimiter(max_weight=1200, window_seconds=60)
        self._circuit_breaker = circuit_breaker or CircuitBreaker(failure_threshold=5, reset_timeout=60.0)
        self._stale_detector = stale_detector or StaleDataDetector(max_age_seconds=30)
        self._policy = ReconnectionPolicy(base_delay=1.0, max_delay=60.0, jitter=0.3)
        
        self._state = ConnectionState.DISCONNECTED
        self._handlers: dict[str, list[Callable]] = {
            'ticker': [],
            'trade': [],
            'kline': [],
        }
        self._subscriptions: set[str] = set()
        self._pending_subscriptions: set[str] = set()
        self._message_tracker = MessageTracker()
        self._server_time_offset: float = 0.0
        self._stop_event = asyncio.Event()
        self._ws_task: asyncio.Task | None = None
        self._reconnect_attempt = 0
        self._last_reconnect_time: float | None = None
        self._warning_callbacks: list[Callable[[str, str], None]] = []
        self._connection_start_time: float | None = None
        self._last_pong_time: float | None = None
        self._renewal_interval: int = 3600  # Renew connection hourly
        
    @property
    def state(self) -> ConnectionState:
        return self._state
    
    def add_ticker_handler(self, handler: Callable[[dict], None]) -> None:
        self._handlers['ticker'].append(handler)
        
    def add_trade_handler(self, handler: Callable[[dict], None]) -> None:
        self._handlers['trade'].append(handler)
        
    def add_candle_handler(self, handler: Callable[[dict], None]) -> None:
        self._handlers['kline'].append(handler)
        
    def add_order_book_handler(self, handler: Callable[[dict], None]) -> None:
        self._handlers['order_book'].append(handler)
        
    def subscribe(self, channel: str, symbols: list[str], **kwargs) -> None:
        """Subscribe to a channel for multiple symbols.
        
        For Binance: channel can be 'ticker', 'trade', 'kline_{interval}', 'depth'
        """
        for symbol in symbols:
            stream = self._build_stream_name(channel, symbol, **kwargs)
            self._subscriptions.add(stream)
            self._pending_subscriptions.add(stream)
            
    def unsubscribe(self, channel: str, symbols: list[str]) -> None:
        for symbol in symbols:
            stream = self._build_stream_name(channel, symbol)
            self._subscriptions.discard(stream)
            self._pending_subscriptions.discard(stream)
            
    def unsubscribe_all(self) -> None:
        self._subscriptions.clear()
        self._pending_subscriptions.clear()
        
    def _build_stream_name(self, channel: str, symbol: str, **kwargs) -> str:
        """Build stream name for the exchange. Override for exchange-specific format."""
        if self._exchange_id == "binance":
            sym = symbol.replace("/", "").lower()
            if channel == "kline":
                interval = kwargs.get("interval", "1m")
                return f"{sym}@kline_{interval}"
            elif channel == "trade":
                return f"{sym}@trade"
            elif channel == "ticker":
                return f"{sym}@ticker"
            elif channel == "depth":
                return f"{sym}@depth"
        raise NotImplementedError(f"Stream building not implemented for {self._exchange_id}: {channel}")
        
    def add_warning_callback(self, callback: Callable[[str, str], None]) -> None:
        self._warning_callbacks.append(callback)
        
    def _emit_warning(self, state: str, message: str) -> None:
        for callback in self._warning_callbacks:
            try:
                callback(state, message)
            except Exception:
                logger.debug("Warning callback failed", exc_info=True)
                
    async def start(self) -> None:
        """Start the WebSocket client with automatic reconnection."""
        while not self._stop_event.is_set():
            if not self._circuit_breaker.can_attempt():
                self._state = ConnectionState.RATE_LIMITED
                await asyncio.sleep(1.0)
                continue
                
            self._reconnect_attempt += 1
            self._state = ConnectionState.CONNECTING
            
            try:
                await self._connect_and_stream()
                self._circuit_breaker.record_success()
                self._reconnect_attempt = 0
                self._state = ConnectionState.CONNECTED
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.warning("WebSocket error: %s", str(e))
                self._circuit_breaker.record_failure()
                self._state = ConnectionState.RECONNECTING
                
                try:
                    delay = self._policy.next_delay(self._reconnect_attempt)
                    await asyncio.sleep(delay)
                except StopIteration:
                    self._state = ConnectionState.ERROR
                    break
                    
        self._state = ConnectionState.STOPPED
        
    async def stop(self) -> None:
        """Stop the WebSocket client."""
        self._stop_event.set()
        if self._ws_task and not self._ws_task.done():
            self._ws_task.cancel()
            
    async def _connect_and_stream(self) -> None:
        """Establish connection and handle messages with subscription recovery."""
        if not self._subscriptions:
            return
            
        streams = '/'.join(self._subscriptions)
        url = f"{self._endpoints.websocket_base_url}/stream?streams={streams}"
        
        self._state = ConnectionState.SUBSCRIBING
        reconnect_time = time.time()
        self._connection_start_time = reconnect_time
        
        import websockets
        ws_cm = websockets.connect(
            url,
            ping_interval=20,
            ping_timeout=10,
            close_timeout=10,
        )
            
        async with ws_cm as ws:
            self._state = ConnectionState.CONNECTED
            self._stale_detector.touch()
            self._pending_subscriptions.clear()
            self._last_reconnect_time = reconnect_time
            self._last_pong_time = time.time()
            
            # Emit recovery warning if reconnecting
            if self._reconnect_attempt > 1:
                self._emit_warning(
                    "reconnected",
                    f"Connection restored after {self._reconnect_attempt} attempts."
                )
            
            # Start renewal monitor
            renewal_task = asyncio.create_task(self._monitor_connection_renewal())
            
            try:
                async for message in ws:
                    if self._stop_event.is_set():
                        break
                        
                    self._stale_detector.touch()
                    await self._handle_message(message)
                    
                    # Check for staleness and emit warnings
                    if self._stale_detector.is_stale():
                        if self._state != ConnectionState.DEGRADED:
                            logger.warning("Data staleness detected")
                            self._state = ConnectionState.DEGRADED
                            self._emit_warning(
                                "degraded",
                                "Market data is stale. Strategy evaluation paused until fresh data arrives."
                            )
                    elif self._state == ConnectionState.DEGRADED:
                        self._state = ConnectionState.CONNECTED
                        self._emit_warning(
                            "recovered",
                            "Market data freshness restored."
                        )
            finally:
                renewal_task.cancel()
                
    async def _monitor_connection_renewal(self) -> None:
        """Monitor connection age and renew periodically to prevent stale connections."""
        try:
            while not self._stop_event.is_set():
                await asyncio.sleep(60)  # Check every minute
                
                if self._connection_start_time is None:
                    continue
                    
                connection_age = time.time() - self._connection_start_time
                
                # Renew connection every hour to prevent long-lived connection issues
                if connection_age >= self._renewal_interval:
                    logger.info("Renewing WebSocket connection (age: %.0f seconds)", connection_age)
                    self._emit_warning(
                        "renewal",
                        f"Renewing connection after {connection_age:.0f} seconds to maintain freshness."
                    )
                    break
                    
        except asyncio.CancelledError:
            pass
            
    async def _handle_message(self, raw_message: Any) -> None:
        """Parse and dispatch a WebSocket message."""
        try:
            if isinstance(raw_message, bytes):
                raw_message = raw_message.decode('utf-8')
            data = json.loads(raw_message)
        except (json.JSONDecodeError, UnicodeDecodeError):
            logger.debug("Invalid JSON received")
            return
            
        # Check for ping/pong (handled by websockets, but log for security)
        if 'result' in data or 'id' in data:
            # Command response
            return
            
        # Binance stream format: { stream: "...", data: {...} }
        stream_name = data.get('stream') or data.get('streamName')
        payload = data.get('data') or data
        
        if not payload:
            return
            
        # Extract message ID for deduplication
        msg_id = payload.get('E') or payload.get('e') or int(time.time() * 1000)
        
        # Check for duplicates and out-of-order
        is_dup, is_oos = self._message_tracker.record(msg_id)
        
        if is_dup:
            logger.debug("Duplicate message %s ignored", msg_id)
            return
            
        if is_oos:
            logger.warning("Out-of-order message %s (last: %s)", 
                         msg_id, self._message_tracker._last_sequence)
            # Still process but flag as degraded
            self._state = ConnectionState.DEGRADED
            
        # Route to appropriate handlers
        if stream_name and 'kline' in stream_name:
            for handler in self._handlers['kline']:
                handler(payload)
        elif stream_name and 'trade' in stream_name:
            for handler in self._handlers['trade']:
                handler(payload)
        elif stream_name and 'ticker' in stream_name:
            for handler in self._handlers['ticker']:
                handler(payload)
                
        # Update server time offset for synchronization
        if 'E' in payload:
            try:
                server_time = payload['E'] / 1000.0
                local_time = time.time()
                self._server_time_offset = server_time - local_time
            except (KeyError, ValueError, TypeError):
                pass
                
    def synchronize_time(self) -> float:
        """Return the current server time offset in seconds."""
        return self._server_time_offset
        
    def get_health_metrics(self) -> dict[str, Any]:
        """Return feed health metrics for monitoring."""
        metrics = {
            'state': self._state.value,
            'state_explanation': self._state.beginner_explanation,
            'stale': self._stale_detector.is_stale(),
            'age_seconds': self._stale_detector.age_seconds,
            'server_time_offset': self._server_time_offset,
            'subscriptions': list(self._subscriptions),
            'pending_subscriptions': list(self._pending_subscriptions),
            'message_count': len(self._message_tracker._seen_ids),
            'reconnect_attempts': self._reconnect_attempt,
            'circuit_breaker_state': self._circuit_breaker.state.value,
            'last_reconnect': self._last_reconnect_time,
        }
        
        # Add warnings for degraded state
        if self._state == ConnectionState.DEGRADED:
            metrics['warning'] = 'Data is stale - strategies should not generate signals'
        elif self._state == ConnectionState.RECONNECTING:
            metrics['warning'] = 'Reconnecting - data may be interrupted'
            
        return metrics
        
    def reconcile_after_reconnect(self) -> dict[str, Any]:
        """Reconcile data after reconnection - check for gaps.
        
        Returns a report of potential data gaps since last connection.
        """
        if self._last_reconnect_time is None:
            return {'has_gap': False}
            
        now = time.time()
        gap_duration = now - self._last_reconnect_time
        
        # Simple gap detection: if gap > 5 seconds, report it
        has_gap = gap_duration > 5.0
        
        report = {
            'has_gap': has_gap,
            'gap_seconds': gap_duration,
            'last_reconnect': self._last_reconnect_time,
            'recommendation': (
                'Verify data integrity by comparing with REST endpoint'
                if has_gap else 'No significant gap detected'
            )
        }
        
        if has_gap:
            self._emit_warning(
                'data_gap',
                f'Potential data gap of {gap_duration:.1f} seconds detected after reconnection. '
                'Consider verifying with historical data.'
            )
            
        return report

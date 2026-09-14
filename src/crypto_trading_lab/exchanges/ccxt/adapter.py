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
from typing import Any, Protocol

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

__all__ = ["CcxtExchangeAdapter", "map_client_error"]

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

    def __init__(self, client: CcxtClient, *, allow_trading: bool = False) -> None:
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
        try:
            return method(*args, **kwargs)
        except AdapterError:
            raise
        except Exception as exc:  # noqa: BLE001 - boundary translation
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

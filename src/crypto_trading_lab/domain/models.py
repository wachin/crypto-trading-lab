"""Strongly validated domain models (ROADMAP.md chapter 7).

All monetary, price, quantity, commission, and balance fields are
:class:`decimal.Decimal`; all timestamps are timezone-aware UTC
datetimes. Every exchange adapter must normalize exchange-specific
data into these models (chapter 7). No ``float`` is used for
critical monetary values.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from decimal import Decimal

__all__ = [
    "utc_now",
    "Symbol",
    "OrderSide",
    "OrderType",
    "OrderStatus",
    "ConnectionState",
    "Market",
    "Ticker",
    "Candle",
    "Balance",
    "OrderRequest",
    "Fill",
    "OrderResult",
]


def utc_now() -> datetime:
    """Current time as a timezone-aware UTC datetime (chapter 7)."""
    return datetime.now(tz=timezone.utc)


class Symbol(str):
    """Normalized pair identifier in ``BASE/QUOTE`` form, e.g. ``BTC/USDT``."""

    __slots__ = ()

    def __new__(cls, value: str) -> "Symbol":
        text = str(value).strip().upper()
        if "/" not in text:
            raise ValueError(f"Symbol must be in BASE/QUOTE form, got {value!r}")
        base, quote = text.split("/", 1)
        if not base or not quote or "/" in quote:
            raise ValueError(f"Symbol must be in BASE/QUOTE form, got {value!r}")
        return super().__new__(cls, text)

    @property
    def base(self) -> str:
        return self.split("/", 1)[0]

    @property
    def quote(self) -> str:
        return self.split("/", 1)[1]


class OrderSide(enum.Enum):
    BUY = "buy"
    SELL = "sell"


class OrderType(enum.Enum):
    MARKET = "market"
    LIMIT = "limit"


class OrderStatus(enum.Enum):
    PENDING_SUBMIT = "pending_submit"
    OPEN = "open"
    PARTIALLY_FILLED = "partially_filled"
    FILLED = "filled"
    CANCELED = "canceled"
    REJECTED = "rejected"
    EXPIRED = "expired"


class ConnectionState(enum.Enum):
    """Connection state machine values (chapter 27).

    Each member carries a beginner-facing explanation so the UI can show
    a visible status label and plain-language help, as required by
    chapter 27 ("every connection state must have a beginner-friendly
    explanation").
    """

    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    AUTHENTICATING = "authenticating"
    SUBSCRIBING = "subscribing"
    CONNECTED = "connected"
    DEGRADED = "degraded"
    RECONNECTING = "reconnecting"
    RATE_LIMITED = "rate_limited"
    ERROR = "error"
    STOPPED = "stopped"

    @property
    def beginner_explanation(self) -> str:
        return _STATE_EXPLANATIONS[self]


_STATE_EXPLANATIONS: dict[ConnectionState, str] = {
    ConnectionState.DISCONNECTED: (
        "Not connected to the exchange. No market data is arriving."
    ),
    ConnectionState.CONNECTING: (
        "Trying to reach the exchange. Please wait a moment."
    ),
    ConnectionState.AUTHENTICATING: (
        "Verifying your API credentials with the exchange."
    ),
    ConnectionState.SUBSCRIBING: (
        "Asking the exchange for the data streams you selected."
    ),
    ConnectionState.CONNECTED: (
        "Connected and receiving live data normally."
    ),
    ConnectionState.DEGRADED: (
        "Connected, but some data is late or incomplete. Treat recent "
        "values with care."
    ),
    ConnectionState.RECONNECTING: (
        "The connection dropped and the app is trying again on its own."
    ),
    ConnectionState.RATE_LIMITED: (
        "The exchange asked us to slow down. Requests are paused "
        "briefly and will resume automatically."
    ),
    ConnectionState.ERROR: (
        "Something failed while talking to the exchange. Check the "
        "message and troubleshooting guide."
    ),
    ConnectionState.STOPPED: (
        "The connection was closed on purpose (for example, by you or "
        "the kill switch)."
    ),
}


@dataclass(frozen=True)
class Market:
    """Normalized market metadata (chapter 30 feeds on this)."""

    exchange: str
    symbol: Symbol
    base: str
    quote: str
    # Precision as number of decimal places for the spike; tick-size
    # markets are normalized to the smallest increment later (chapter 30).
    price_precision: int
    quantity_precision: int
    min_quantity: Decimal | None = None
    min_notional: Decimal | None = None
    maker_fee: Decimal | None = None
    taker_fee: Decimal | None = None

    def __post_init__(self) -> None:
        if self.price_precision < 0 or self.quantity_precision < 0:
            raise ValueError("precisions must be non-negative")
        for name in ("min_quantity", "min_notional", "maker_fee", "taker_fee"):
            value = getattr(self, name)
            if value is not None and value < 0:
                raise ValueError(f"{name} must be non-negative, got {value}")


@dataclass(frozen=True)
class Ticker:
    symbol: Symbol
    timestamp: datetime
    last: Decimal
    bid: Decimal | None = None
    ask: Decimal | None = None
    volume: Decimal | None = None

    def __post_init__(self) -> None:
        _require_utc("timestamp", self.timestamp)
        if self.last < 0:
            raise ValueError("last price must be non-negative")
        if self.bid is not None and self.ask is not None and self.bid > self.ask:
            raise ValueError("bid must not exceed ask")


def _require_utc(name: str, value: object) -> None:
    """Enforce timezone-aware UTC timestamps (chapter 7: UTC internally).

    Naive datetimes are rejected: they would silently introduce
    timezone bugs into research data.
    """
    if not isinstance(value, datetime) or value.tzinfo is None:
        raise TypeError(f"{name} must be a timezone-aware datetime, got {value!r}")
    if value.utcoffset() != timedelta(0):
        raise ValueError(f"{name} must be UTC, got offset {value.utcoffset()}")


@dataclass(frozen=True)
class Candle:
    """One OHLCV candle; timestamps are the UTC open time."""

    symbol: Symbol
    interval: str  # e.g. "1m", "1h", "1d"
    open_time: datetime
    close_time: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal

    def __post_init__(self) -> None:
        _require_utc("open_time", self.open_time)
        _require_utc("close_time", self.close_time)
        if self.open_time >= self.close_time:
            raise ValueError("open_time must precede close_time")
        if min(self.open, self.high, self.low, self.close) < 0:
            raise ValueError("prices must be non-negative")
        if self.high < max(self.open, self.close) or self.low > min(self.open, self.close):
            raise ValueError("high/low must bound open and close")
        if self.volume < 0:
            raise ValueError("volume must be non-negative")


@dataclass(frozen=True)
class Balance:
    """Balance of one asset; free + locked = total (chapter 7)."""

    asset: str
    free: Decimal
    locked: Decimal

    def __post_init__(self) -> None:
        if self.free < 0 or self.locked < 0:
            raise ValueError("balance components must be non-negative")

    @property
    def total(self) -> Decimal:
        return self.free + self.locked


@dataclass(frozen=True)
class OrderRequest:
    """A request to create an order. This is not an order yet (chapter 2:
    signal/order separation lives in the strategy and risk layers)."""

    symbol: Symbol
    side: OrderSide
    order_type: OrderType
    quantity: Decimal
    price: Decimal | None = None  # required for LIMIT
    client_order_id: str | None = None

    def __post_init__(self) -> None:
        if self.quantity <= 0:
            raise ValueError("quantity must be positive")
        if self.order_type is OrderType.LIMIT:
            if self.price is None or self.price <= 0:
                raise ValueError("LIMIT orders require a positive price")


@dataclass(frozen=True)
class Fill:
    symbol: Symbol
    quantity: Decimal
    price: Decimal
    fee: Decimal | None = None
    fee_asset: str | None = None
    timestamp: datetime | None = None


@dataclass(frozen=True)
class OrderResult:
    """Adapter-agnostic result of submitting an OrderRequest."""

    adapter_order_id: str
    client_order_id: str | None
    symbol: Symbol
    side: OrderSide
    order_type: OrderType
    status: OrderStatus
    quantity: Decimal
    filled_quantity: Decimal = Decimal("0")
    average_price: Decimal | None = None
    fills: tuple[Fill, ...] = field(default_factory=tuple)
    timestamp: datetime = field(default_factory=utc_now)
    raw_status: str | None = None  # exchange-native status, kept for audit

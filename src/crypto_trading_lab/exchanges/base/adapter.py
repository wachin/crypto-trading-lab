"""The ``ExchangeAdapter`` port (ROADMAP.md chapter 26).

One abstract operation per capability listed in chapter 26:

- retrieving markets / tickers / historical candles;
- subscribing to tickers / candles / trades / order book;
- retrieving balances / orders;
- creating / cancelling an order;
- receiving order updates;
- checking API permissions.

Implementations must be **side-effect honest**: no method here ever
touches a real exchange unless the concrete adapter is explicitly
constructed with real credentials *and* trading enabled. The spike
defaults to read-only mode and refuses order operations otherwise.
"""

from __future__ import annotations

import abc
import enum
from collections.abc import Callable
from datetime import datetime

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
from crypto_trading_lab.exchanges.errors import (
    AdapterInvalidOrder,
    AdapterNotSupported,
)

__all__ = ["Capability", "ExchangeAdapter"]

#: Callbacks receiving normalized payloads for subscriptions. The order
#: book and trade payloads reuse domain value objects once those gain
#: full models (OrderBook / Trade in chapter 7); ``object`` keeps the
#: port stable until then.
TickerHandler = Callable[[Ticker], None]
CandleHandler = Callable[[Candle], None]
TradeHandler = Callable[[object], None]
OrderBookHandler = Callable[[object], None]
OrderUpdateHandler = Callable[[OrderResult], None]


class Capability(enum.Flag):
    """Declared features of an adapter; adapters may implement subsets."""

    NONE = 0
    MARKETS = enum.auto()
    TICKERS = enum.auto()
    CANDLES = enum.auto()
    SUBSCRIPTIONS = enum.auto()
    TRADING = enum.auto()
    BALANCES = enum.auto()
    ORDERS = enum.auto()
    PERMISSIONS = enum.auto()


class ExchangeAdapter(abc.ABC):
    """Abstract port every adapter must implement (chapter 26)."""

    #: Subclasses declare what they support; ``TRADING`` must never be
    #: set by accident (chapters 60/61: capital protection first).
    capabilities: Capability = Capability.NONE

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------
    @abc.abstractmethod
    def connect(self) -> None:
        """Open the connection; must be idempotent."""

    @abc.abstractmethod
    def disconnect(self) -> None:
        """Close the connection; must be idempotent."""

    @abc.abstractmethod
    def state(self) -> ConnectionState:
        """Current connection state (chapter 27)."""

    # ------------------------------------------------------------------
    # Market metadata and data retrieval
    # ------------------------------------------------------------------
    @abc.abstractmethod
    def fetch_markets(self) -> list[Market]:
        """Retrieve markets."""

    @abc.abstractmethod
    def fetch_ticker(self, symbol: Symbol) -> Ticker:
        """Retrieve the latest ticker for one symbol."""

    @abc.abstractmethod
    def fetch_candles(
        self,
        symbol: Symbol,
        interval: str,
        since: datetime | None = None,
        limit: int | None = None,
    ) -> list[Candle]:
        """Retrieve historical candles in chronological order."""

    # ------------------------------------------------------------------
    # Subscriptions (chapter 26)
    # ------------------------------------------------------------------
    @abc.abstractmethod
    def subscribe_ticker(self, symbol: Symbol, handler: TickerHandler) -> None:
        """Subscribe to tickers."""

    @abc.abstractmethod
    def subscribe_candles(
        self, symbol: Symbol, interval: str, handler: CandleHandler
    ) -> None:
        """Subscribe to candles."""

    @abc.abstractmethod
    def subscribe_trades(self, symbol: Symbol, handler: TradeHandler) -> None:
        """Subscribe to trades."""

    @abc.abstractmethod
    def subscribe_order_book(self, symbol: Symbol, handler: OrderBookHandler) -> None:
        """Subscribe to the order book."""

    @abc.abstractmethod
    def unsubscribe_all(self) -> None:
        """Cancel every active subscription."""

    # ------------------------------------------------------------------
    # Account operations
    # ------------------------------------------------------------------
    @abc.abstractmethod
    def fetch_balances(self) -> dict[str, Balance]:
        """Retrieve balances keyed by asset."""

    @abc.abstractmethod
    def fetch_open_orders(self, symbol: Symbol | None = None) -> list[OrderResult]:
        """Retrieve open orders, optionally filtered by symbol."""

    # ------------------------------------------------------------------
    # Trading
    # ------------------------------------------------------------------
    @abc.abstractmethod
    def create_order(self, request: OrderRequest) -> OrderResult:
        """Create an order."""

    @abc.abstractmethod
    def cancel_order(self, adapter_order_id: str, symbol: Symbol) -> OrderResult:
        """Cancel an order by adapter order id."""

    @abc.abstractmethod
    def on_order_update(self, handler: OrderUpdateHandler) -> None:
        """Register for order updates (chapter 26)."""

    # ------------------------------------------------------------------
    # Permissions
    # ------------------------------------------------------------------
    @abc.abstractmethod
    def check_api_permissions(self) -> dict[str, bool]:
        """Check API permissions, e.g. ``{"read": True, "trade": False}``."""

    # ------------------------------------------------------------------
    # Optional niceties with sensible defaults
    # ------------------------------------------------------------------
    def supports(self, capability: Capability) -> bool:
        return capability in self.capabilities

    def validate_order_request(self, request: OrderRequest, market: Market) -> None:
        """Pre-flight validation against market rules (chapter 30).

        Adapters may override with exchange-specific precision rules; the
        base version checks the quantity/notional minima it knows about.
        """
        if not self.supports(Capability.TRADING):
            raise AdapterNotSupported(
                "trading is not enabled on this adapter (read-only mode)"
            )
        if request.symbol != market.symbol:
            raise AdapterInvalidOrder("symbol does not match market")
        if market.min_quantity is not None and request.quantity < market.min_quantity:
            raise AdapterInvalidOrder(
                f"quantity {request.quantity} below minimum {market.min_quantity}"
            )
        if market.min_notional is not None:
            price = request.price
            if price is None:
                # Market orders need a reference price for the notional
                # check; adapters with live tickers can override.
                raise AdapterInvalidOrder(
                    "cannot check minimum order value without a price"
                )
            notional = request.quantity * price
            if notional < market.min_notional:
                raise AdapterInvalidOrder(
                    f"order value {notional} below minimum order value "
                    f"{market.min_notional}"
                )

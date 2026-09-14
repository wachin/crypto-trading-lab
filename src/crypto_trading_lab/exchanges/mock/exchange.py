"""Fully local exchange provider (ROADMAP.md chapter 26.1).

``MockExchange`` exists for:

- automated tests (deterministic by seed, no network, no sleeps by default);
- demonstrations;
- paper trading (a simple local account with balances and fills);
- historical replay (publish stored candles to candle subscribers);
- simulated failures, disconnections, latency, slippage, partially
  filled orders, rejected orders, and rate limits.

Everything is scripted explicitly: without scripting, the mock behaves
like a healthy exchange.
"""

from __future__ import annotations

import random
import time
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_EVEN
from typing import Callable

from crypto_trading_lab.domain.models import (
    Balance,
    Candle,
    ConnectionState,
    Fill,
    Market,
    OrderRequest,
    OrderResult,
    OrderSide,
    OrderStatus,
    Symbol,
    Ticker,
    utc_now,
)
from crypto_trading_lab.exchanges.base.adapter import (
    Capability,
    ExchangeAdapter,
)
from crypto_trading_lab.exchanges.errors import (
    AdapterError,
    AdapterInsufficientFunds,
    AdapterInvalidOrder,
    AdapterRateLimited,
)

__all__ = ["MockExchange", "TradeTick", "OrderBookSnapshot", "generate_candles"]


def _q(value: Decimal, precision: int) -> Decimal:
    return value.quantize(Decimal(1).scaleb(-precision), rounding=ROUND_HALF_EVEN)


@dataclass(frozen=True)
class TradeTick:
    """Placeholder trade payload until the full domain Trade model lands."""

    symbol: Symbol
    price: Decimal
    quantity: Decimal
    side: str
    timestamp: datetime


@dataclass(frozen=True)
class OrderBookSnapshot:
    """Placeholder order-book payload until the full domain model lands."""

    symbol: Symbol
    bids: tuple[tuple[Decimal, Decimal], ...]
    asks: tuple[tuple[Decimal, Decimal], ...]
    timestamp: datetime


@dataclass
class _MockOrder:
    result: OrderResult
    remaining: Decimal
    market: Market


class MockExchange(ExchangeAdapter):
    """Deterministic, scriptable, fully local adapter (chapter 26.1)."""

    capabilities = (
        Capability.MARKETS
        | Capability.TICKERS
        | Capability.CANDLES
        | Capability.SUBSCRIPTIONS
        | Capability.TRADING
        | Capability.BALANCES
        | Capability.ORDERS
        | Capability.PERMISSIONS
    )

    def __init__(
        self,
        *,
        markets: list[Market] | None = None,
        candles: list[Candle] | None = None,
        tickers: dict[Symbol, Ticker] | None = None,
        initial_balances: dict[str, Decimal] | None = None,
        slippage_pct: Decimal = Decimal("0"),
        taker_fee_pct: Decimal = Decimal("0.1"),  # percent, i.e. 0.1%
        latency_ms: float = 0.0,
        rate_limit_calls: int | None = None,
        rate_limit_window_s: float = 1.0,
        seed: int = 42,
        allow_trading: bool = False,
    ) -> None:
        if not allow_trading:
            self.capabilities = Capability(
                self.capabilities & ~Capability.TRADING
            )
        self._markets = {m.symbol: m for m in (markets or _default_markets())}
        self._candles = list(candles or [])
        self._tickers = dict(tickers or {})
        self._balances: dict[str, Balance] = {
            asset: Balance(asset=asset, free=amount, locked=Decimal("0"))
            for asset, amount in (initial_balances or {"USDT": Decimal("10000")}).items()
        }
        self._slippage_pct = slippage_pct
        self._taker_fee_pct = taker_fee_pct
        self._latency_ms = latency_ms
        self._rate_limit_calls = rate_limit_calls
        self._rate_limit_window_s = rate_limit_window_s
        self._call_times: deque[float] = deque()
        self._rng = random.Random(seed)
        self._state = ConnectionState.DISCONNECTED
        self._orders: dict[str, _MockOrder] = {}
        self._order_seq = 0
        self._ticker_handlers: list[Callable[[Ticker], None]] = []
        self._candle_handlers: list[Callable[[Candle], None]] = []
        self._trade_handlers: list[Callable[[TradeTick], None]] = []
        self._book_handlers: list[Callable[[OrderBookSnapshot], None]] = []
        self._order_update_handlers: list[Callable[[OrderResult], None]] = []
        # Script queues (popped one entry per matching event).
        self._error_script: list[AdapterError] = []
        self._rejection_script: list[str] = []
        self._partial_fill_script: list[Decimal] = []

    # ------------------------------------------------------------------
    # Scripting helpers (tests / demos)
    # ------------------------------------------------------------------
    def queue_error(self, error: AdapterError) -> None:
        """Make the next adapter call raise ``error`` (simulated failure)."""
        self._error_script.append(error)

    def queue_rejection(self, reason: str) -> None:
        """Make the next order be rejected with ``reason``."""
        self._rejection_script.append(reason)

    def queue_partial_fill(self, fraction: Decimal) -> None:
        """Make the next order fill only ``fraction`` of its quantity."""
        if not Decimal("0") < fraction < Decimal("1"):
            raise ValueError("fraction must be in (0, 1)")
        self._partial_fill_script.append(fraction)

    def simulate_disconnection(self) -> None:
        self._state = ConnectionState.RECONNECTING

    def set_ticker(self, ticker: Ticker) -> None:
        """Provide/refresh the reference price used for fills."""
        self._tickers[ticker.symbol] = ticker

    def add_candles(self, candles: list[Candle]) -> None:
        self._candles.extend(candles)

    # ------------------------------------------------------------------
    # Internal plumbing
    # ------------------------------------------------------------------
    def _require_connected(self) -> None:
        if self._state is ConnectionState.STOPPED:
            raise AdapterError("adapter is stopped")
        if self._state not in (ConnectionState.CONNECTED, ConnectionState.RATE_LIMITED):
            raise AdapterError("adapter is not connected; call connect() first")
        if self._error_script:
            raise self._error_script.pop(0)
        self._enforce_rate_limit()
        if self._latency_ms:
            time.sleep(self._latency_ms / 1000.0)

    def _enforce_rate_limit(self) -> None:
        if self._rate_limit_calls is None:
            return
        now = time.monotonic()
        while self._call_times and now - self._call_times[0] > self._rate_limit_window_s:
            self._call_times.popleft()
        if len(self._call_times) >= self._rate_limit_calls:
            self._state = ConnectionState.RATE_LIMITED
            raise AdapterRateLimited(
                f"mock rate limit: {self._rate_limit_calls} calls per "
                f"{self._rate_limit_window_s}s window"
            )
        self._call_times.append(now)

    def _reference_price(self, symbol: Symbol) -> Decimal:
        ticker = self._tickers.get(symbol)
        if ticker is None:
            raise AdapterInvalidOrder(f"no reference price available for {symbol}")
        return ticker.last

    def _emit_order_update(self, result: OrderResult) -> None:
        for handler in self._order_update_handlers:
            handler(result)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------
    def connect(self) -> None:
        if self._state is ConnectionState.RATE_LIMITED:
            self._state = ConnectionState.CONNECTED
        elif self._state is not ConnectionState.CONNECTED:
            self._state = ConnectionState.CONNECTED

    def disconnect(self) -> None:
        self._state = ConnectionState.STOPPED

    def state(self) -> ConnectionState:
        return self._state

    # ------------------------------------------------------------------
    # Market data
    # ------------------------------------------------------------------
    def fetch_markets(self) -> list[Market]:
        self._require_connected()
        return list(self._markets.values())

    def fetch_ticker(self, symbol: Symbol) -> Ticker:
        self._require_connected()
        ticker = self._tickers.get(symbol)
        if ticker is None:
            raise AdapterInvalidOrder(f"no ticker published for {symbol}")
        return ticker

    def fetch_candles(
        self,
        symbol: Symbol,
        interval: str,
        since: datetime | None = None,
        limit: int | None = None,
    ) -> list[Candle]:
        self._require_connected()
        rows = [
            c
            for c in self._candles
            if c.symbol == symbol and c.interval == interval
        ]
        rows.sort(key=lambda c: c.open_time)
        if since is not None:
            rows = [c for c in rows if c.open_time >= since]
        if limit is not None:
            rows = rows[-limit:]
        return list(rows)

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

    # Publish-side API: drives replay and demonstrations.
    def publish_ticker(self, ticker: Ticker) -> None:
        self.set_ticker(ticker)
        for handler in self._ticker_handlers:
            handler(ticker)

    def publish_candle(self, candle: Candle) -> None:
        for handler in self._candle_handlers:
            handler(candle)

    def publish_trade(self, trade: TradeTick) -> None:
        for handler in self._trade_handlers:
            handler(trade)

    def publish_order_book(self, book: OrderBookSnapshot) -> None:
        for handler in self._book_handlers:
            handler(book)

    def replay_candles(self, symbol: Symbol, interval: str) -> int:
        """Historical replay (chapter 26.1): push stored candles out."""
        candles = self.fetch_candles(symbol, interval)
        for candle in candles:
            self.publish_candle(candle)
        return len(candles)

    # ------------------------------------------------------------------
    # Account
    # ------------------------------------------------------------------
    def fetch_balances(self) -> dict[str, Balance]:
        self._require_connected()
        return dict(self._balances)

    def fetch_open_orders(self, symbol: Symbol | None = None) -> list[OrderResult]:
        self._require_connected()
        results = []
        for mock_order in self._orders.values():
            status = mock_order.result.status
            if status in (OrderStatus.OPEN, OrderStatus.PARTIALLY_FILLED):
                if symbol is None or mock_order.result.symbol == symbol:
                    results.append(mock_order.result)
        return results

    # ------------------------------------------------------------------
    # Trading
    # ------------------------------------------------------------------
    def on_order_update(self, handler) -> None:
        self._order_update_handlers.append(handler)

    def check_api_permissions(self) -> dict[str, bool]:
        self._require_connected()
        return {"read": True, "trade": self.supports(Capability.TRADING)}

    def create_order(self, request: OrderRequest) -> OrderResult:
        self._require_connected()
        market = self._markets.get(request.symbol)
        if market is None:
            raise AdapterInvalidOrder(f"unknown market {request.symbol}")
        self.validate_order_request(request, market)
        if self._rejection_script:
            raise AdapterInvalidOrder(self._rejection_script.pop(0))
        return self._fill(request, market)

    def cancel_order(self, adapter_order_id: str, symbol: Symbol) -> OrderResult:
        self._require_connected()
        mock_order = self._orders.get(adapter_order_id)
        if mock_order is None or mock_order.result.symbol != symbol:
            raise AdapterInvalidOrder(f"unknown order {adapter_order_id}")
        if mock_order.result.status is OrderStatus.FILLED:
            raise AdapterInvalidOrder("order already filled")
        canceled = OrderResult(
            adapter_order_id=adapter_order_id,
            client_order_id=mock_order.result.client_order_id,
            symbol=mock_order.result.symbol,
            side=mock_order.result.side,
            order_type=mock_order.result.order_type,
            status=OrderStatus.CANCELED,
            quantity=mock_order.result.quantity,
            filled_quantity=mock_order.result.filled_quantity,
            average_price=mock_order.result.average_price,
            fills=mock_order.result.fills,
            raw_status="CANCELED",
        )
        self._orders[adapter_order_id] = _MockOrder(
            result=canceled, remaining=Decimal("0"), market=mock_order.market
        )
        self._release_locked(canceled)
        self._emit_order_update(canceled)
        return canceled

    # ------------------------------------------------------------------
    # Fill engine
    # ------------------------------------------------------------------
    def _fill(self, request: OrderRequest, market: Market) -> OrderResult:
        reference = self._reference_price(request.symbol)
        slip = self._slippage_pct / Decimal("100")
        if request.side is OrderSide.BUY:
            fill_price = reference * (Decimal("1") + slip)
        else:
            fill_price = reference * (Decimal("1") - slip)
        fill_price = _q(fill_price, market.price_precision)

        fraction = self._partial_fill_script.pop(0) if self._partial_fill_script else None
        filled = request.quantity if fraction is None else request.quantity * fraction
        filled = _q(filled, market.quantity_precision)

        fee = _q(filled * fill_price * self._taker_fee_pct / Decimal("100"), 8)
        self._require_funds(request, market, filled, fill_price, fee)
        fill = _build_fill(request, fill_price, filled, fee, market)

        self._order_seq += 1
        order_id = f"mock-{self._order_seq:06d}"
        status = (
            OrderStatus.FILLED if fraction is None else OrderStatus.PARTIALLY_FILLED
        )
        self._apply_balance_effects(request, fill_price, filled, fee)

        result = OrderResult(
            adapter_order_id=order_id,
            client_order_id=request.client_order_id,
            symbol=request.symbol,
            side=request.side,
            order_type=request.order_type,
            status=status,
            quantity=request.quantity,
            filled_quantity=filled,
            average_price=fill_price,
            fills=(fill,),
            raw_status=status.value,
        )
        self._orders[order_id] = _MockOrder(
            result=result, remaining=request.quantity - filled, market=market
        )
        self._emit_order_update(result)
        return result

    def fill_remaining(self, adapter_order_id: str) -> OrderResult:
        """Complete a partially filled order (used by tests/demos)."""
        mock_order = self._orders.get(adapter_order_id)
        if mock_order is None:
            raise AdapterInvalidOrder(f"unknown order {adapter_order_id}")
        prior = mock_order.result
        if prior.status is OrderStatus.FILLED:
            raise AdapterInvalidOrder("order is already filled")
        market = mock_order.market
        reference = self._reference_price(prior.symbol)
        slip = self._slippage_pct / Decimal("100")
        direction = Decimal("1") if prior.side is OrderSide.BUY else Decimal("-1")
        price = _q(reference * (Decimal("1") + direction * slip), market.price_precision)
        extra = _q(prior.quantity - prior.filled_quantity, market.quantity_precision)
        fee = _q(extra * price * self._taker_fee_pct / Decimal("100"), 8)

        request = OrderRequest(
            symbol=prior.symbol,
            side=prior.side,
            order_type=prior.order_type,
            quantity=extra,
            price=prior.average_price,
        )
        fill = _build_fill(request, price, extra, fee, market)
        self._apply_balance_effects(request, price, extra, fee)
        total_filled = prior.filled_quantity + extra
        result = OrderResult(
            adapter_order_id=prior.adapter_order_id,
            client_order_id=prior.client_order_id,
            symbol=prior.symbol,
            side=prior.side,
            order_type=prior.order_type,
            status=OrderStatus.FILLED,
            quantity=prior.quantity,
            filled_quantity=total_filled,
            average_price=price,
            fills=prior.fills + (fill,),
            raw_status="filled",
        )
        self._orders[adapter_order_id] = _MockOrder(
            result=result, remaining=Decimal("0"), market=market
        )
        self._emit_order_update(result)
        return result

    def _require_funds(
        self,
        request: OrderRequest,
        market: Market,
        quantity: Decimal,
        price: Decimal,
        fee: Decimal,
    ) -> None:
        """Refuse orders the local account cannot cover (paper-trading
        honesty: balances must never go negative silently)."""
        if request.side is OrderSide.BUY:
            cost = quantity * price + fee
            quote = self._balances.get(market.quote)
            if quote is None or quote.free < cost:
                have = quote.free if quote else Decimal("0")
                raise AdapterInsufficientFunds(
                    f"insufficient {market.quote}: need {cost}, have {have}"
                )
        else:
            base = self._balances.get(market.base)
            if base is None or base.free < quantity:
                have = base.free if base else Decimal("0")
                raise AdapterInsufficientFunds(
                    f"insufficient {market.base}: need {quantity}, have {have}"
                )

    def _apply_balance_effects(
        self, request: OrderRequest, price: Decimal, quantity: Decimal, fee: Decimal
    ) -> None:
        market = self._markets[request.symbol]
        base, quote = market.base, market.quote
        self._ensure_asset(base)
        self._ensure_asset(quote)
        if request.side is OrderSide.BUY:
            self._balances[base] = Balance(
                asset=base,
                free=self._balances[base].free + quantity,
                locked=self._balances[base].locked,
            )
            cost = quantity * price + fee
            self._balances[quote] = Balance(
                asset=quote,
                free=self._balances[quote].free - cost,
                locked=self._balances[quote].locked,
            )
        else:
            self._balances[base] = Balance(
                asset=base,
                free=self._balances[base].free - quantity,
                locked=self._balances[base].locked,
            )
            proceeds = quantity * price - fee
            self._balances[quote] = Balance(
                asset=quote,
                free=self._balances[quote].free + proceeds,
                locked=self._balances[quote].locked,
            )

    def _release_locked(self, result: OrderResult) -> None:  # pragma: no cover
        # Spike simplification: the mock debits balances on fill and does
        # not lock funds on submit; a real escrow model belongs to the
        # paper-trading engine (chapter 57), not to the mock.
        return None

    def _ensure_asset(self, asset: str) -> None:
        if asset not in self._balances:
            self._balances[asset] = Balance(
                asset=asset, free=Decimal("0"), locked=Decimal("0")
            )


def _build_fill(
    request: OrderRequest,
    price: Decimal,
    quantity: Decimal,
    fee: Decimal,
    market: Market,
) -> object:
    return Fill(
        symbol=request.symbol,
        quantity=quantity,
        price=price,
        fee=fee,
        fee_asset=market.quote,
        timestamp=utc_now(),
    )


def _default_markets() -> list[Market]:
    return [
        Market(
            exchange="mock",
            symbol=Symbol("BTC/USDT"),
            base="BTC",
            quote="USDT",
            price_precision=2,
            quantity_precision=6,
            min_quantity=Decimal("0.0001"),
            min_notional=Decimal("10"),
            maker_fee=Decimal("0.001"),
            taker_fee=Decimal("0.001"),
        ),
        Market(
            exchange="mock",
            symbol=Symbol("ETH/USDT"),
            base="ETH",
            quote="USDT",
            price_precision=2,
            quantity_precision=5,
            min_quantity=Decimal("0.001"),
            min_notional=Decimal("10"),
            maker_fee=Decimal("0.001"),
            taker_fee=Decimal("0.001"),
        ),
    ]


def generate_candles(
    symbol: Symbol,
    interval: str,
    count: int,
    *,
    start_price: Decimal = Decimal("50000"),
    start_time: datetime | None = None,
    step_minutes: int = 60,
    volatility_pct: Decimal = Decimal("0.5"),
    seed: int = 42,
) -> list[Candle]:
    """Deterministic random-walk candles for tests and demos."""
    rng = random.Random(seed)
    moment = start_time or datetime(2024, 1, 1, tzinfo=timezone.utc)
    step = timedelta(minutes=step_minutes)
    price = start_price
    candles: list[Candle] = []
    for index in range(count):
        drift = Decimal(str(rng.gauss(0, float(volatility_pct) / 100)))
        open_price = price
        close_price = _q(open_price * (Decimal("1") + drift), 2)
        high = _q(max(open_price, close_price) * (Decimal("1") + abs(drift) / 2), 2)
        low = _q(min(open_price, close_price) * (Decimal("1") - abs(drift) / 2), 2)
        volume = _q(Decimal(str(abs(rng.gauss(100, 20)))), 4)
        candles.append(
            Candle(
                symbol=symbol,
                interval=interval,
                open_time=moment,
                close_time=moment + step,
                open=open_price,
                high=high,
                low=low,
                close=close_price,
                volume=volume,
            )
        )
        price = close_price
        moment += step
    return candles

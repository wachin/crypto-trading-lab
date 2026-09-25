"""Simulated WebSocket for testing (ROADMAP.md chapter 14.2).

Provides a deterministic, in-memory WebSocket implementation for testing
without network access. Chapter 14 requires simulated WebSockets for
contract tests and GUI tests.
"""

from __future__ import annotations

import asyncio
import json
import logging
import random
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import Any, Callable

from crypto_trading_lab.domain.models import Candle, Symbol

logger = logging.getLogger(__name__)


@dataclass
class SimulatedWebSocketMessage:
    """A message in the simulated WebSocket."""
    stream: str
    payload: dict
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class SimulatedWebSocketServer:
    """In-memory WebSocket server for testing.

    Simulates Binance WebSocket API behavior without network access.
    Supports ticker, kline, trade, and depth streams.
    """

    def __init__(self) -> None:
        self._subscriptions: dict[str, set[str]] = defaultdict(set)  # stream -> client_ids
        self._client_queues: dict[str, asyncio.Queue] = {}  # client_id -> queue
        self._running = False
        self._message_counter = 0

    def register_client(self, client_id: str) -> asyncio.Queue:
        """Register a new client and return its message queue."""
        queue: asyncio.Queue = asyncio.Queue()
        self._client_queues[client_id] = queue
        return queue

    def unregister_client(self, client_id: str) -> None:
        """Unregister a client."""
        self._client_queues.pop(client_id, None)
        for streams in self._subscriptions.values():
            streams.discard(client_id)

    def subscribe(self, client_id: str, stream: str) -> None:
        """Subscribe a client to a stream."""
        self._subscriptions[stream].add(client_id)

    def unsubscribe(self, client_id: str, stream: str) -> None:
        """Unsubscribe a client from a stream."""
        self._subscriptions[stream].discard(client_id)

    def broadcast(self, stream: str, payload: dict) -> None:
        """Broadcast a message to all subscribers of a stream."""
        for client_id in self._subscriptions.get(stream, set()):
            queue = self._client_queues.get(client_id)
            if queue:
                message = {
                    "stream": stream,
                    "data": payload,
                }
                try:
                    queue.put_nowait(message)
                except asyncio.QueueFull:
                    logger.warning("Client %s queue full, dropping message", client_id)

    def publish_ticker(self, symbol: str, price: Decimal, bid: Decimal | None = None,
                       ask: Decimal | None = None, volume: Decimal | None = None) -> None:
        """Publish a ticker update for a symbol."""
        stream = f"{symbol.replace('/', '').lower()}@ticker"
        payload = {
            "s": symbol.replace("/", ""),
            "c": str(price),
            "b": str(bid) if bid else None,
            "a": str(ask) if ask else None,
            "v": str(volume) if volume else None,
            "E": int(Decimal(datetime.now(timezone.utc).timestamp()) * 1000),
        }
        # Remove None values
        payload = {k: v for k, v in payload.items() if v is not None}
        self.broadcast(stream, payload)

    def publish_kline(self, symbol: str, interval: str, open_: Decimal, high: Decimal,
                      low: Decimal, close: Decimal, volume: Decimal,
                      open_time: datetime | None = None, close_time: datetime | None = None,
                      is_closed: bool = True) -> None:
        """Publish a kline/candlestick update."""
        stream = f"{symbol.replace('/', '').lower()}@kline_{interval}"
        now = datetime.now(timezone.utc)
        open_time = open_time or datetime.now(timezone.utc)
        close_time = close_time or (open_time.replace(second=59, microsecond=999999)
                                     if interval.endswith('m') else open_time)
        payload = {
            "s": symbol.replace("/", ""),
            "k": {
                "t": int(open_time.timestamp() * 1000),
                "T": int(close_time.timestamp() * 1000),
                "s": symbol.replace("/", ""),
                "i": interval,
                "f": 1,
                "L": 1,
                "o": str(open_),
                "h": str(high),
                "l": str(low),
                "c": str(close),
                "v": str(volume),
                "n": 1,
                "x": is_closed,
                "q": str(volume * close),
                "V": "0",
                "Q": "0",
            },
        }
        self.broadcast(stream, payload)

    def publish_trade(self, symbol: str, price: Decimal, quantity: Decimal,
                      is_buyer_maker: bool, trade_time: datetime | None = None) -> None:
        """Publish a trade update."""
        stream = f"{symbol.replace('/', '').lower()}@trade"
        payload = {
            "s": symbol.replace("/", ""),
            "p": str(price),
            "q": str(quantity),
            "m": is_buyer_maker,
            "T": int((time.time() * 1000)) if time else int(Decimal(datetime.now(timezone.utc).timestamp()) * 1000),
        }
        self.broadcast(stream, payload)


class SimulatedWebSocketClient:
    """Simulated WebSocket client for testing.

    Mimics the BinanceWebSocketClient interface but connects to a
    SimulatedWebSocketServer instead of a real network.
    """

    def __init__(
        self,
        server: SimulatedWebSocketServer,
        client_id: str,
    ) -> None:
        self._server = server
        self._client_id = client_id
        self._queue = server.register_client(client_id)
        self._state = "DISCONNECTED"
        self._handlers: dict[str, list[Callable]] = {
            'ticker': [],
            'trade': [],
            'kline': [],
            'depth': [],
        }
        self._subscriptions: set[str] = set()
        self._running = False

    async def connect(self) -> None:
        """Simulate connection."""
        self._state = "CONNECTED"
        logger.info("Simulated WebSocket connected (client_id=%s)", self._client_id)

    async def disconnect(self) -> None:
        """Simulate disconnection."""
        self._server.unregister_client(self._client_id)
        self._state = "DISCONNECTED"
        logger.info("Simulated WebSocket disconnected (client_id=%s)", self._client_id)

    @property
    def state(self) -> str:
        return self._state

    def subscribe(self, stream: str) -> None:
        self._server.subscribe(self._client_id, stream)
        self._subscriptions.add(stream)

    def unsubscribe(self, stream: str) -> None:
        self._server.unsubscribe(self._client_id, stream)
        self._subscriptions.discard(stream)

    def unsubscribe_all(self) -> None:
        for stream in list(self._subscriptions):
            self.unsubscribe(stream)

    def add_ticker_handler(self, handler: Callable[[dict], None]) -> None:
        self._handlers['ticker'].append(handler)

    def add_trade_handler(self, handler: Callable[[dict], None]) -> None:
        self._handlers['trade'].append(handler)

    def add_candle_handler(self, handler: Callable[[dict], None]) -> None:
        self._handlers['kline'].append(handler)

    def add_depth_handler(self, handler: Callable[[dict], None]) -> None:
        self._handlers['depth'].append(handler)

    async def receive_messages(self) -> None:
        """Process incoming messages from the server queue."""
        while True:
            message = await self._queue.get()
            stream = message.get('stream', '')
            payload = message.get('data', {})

            if 'ticker' in stream:
                for handler in self._handlers['ticker']:
                    handler(payload)
            elif 'trade' in stream:
                for handler in self._handlers['trade']:
                    handler(payload)
            elif 'kline' in stream:
                for handler in self._handlers['kline']:
                    handler(payload)
            elif 'depth' in stream:
                for handler in self._handlers['depth']:
                    handler(payload)

    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.disconnect()


@dataclass
class SimulatedMarketDataGenerator:
    """Generates realistic simulated market data for testing."""

    symbol: Symbol
    base_price: Decimal
    volatility: Decimal = Decimal("0.01")
    interval_seconds: int = 60

    _current_price: Decimal = field(init=False)
    _current_time: datetime = field(init=False)

    def __post_init__(self) -> None:
        self._current_price = self.base_price
        self._current_time = datetime.now(timezone.utc)

    def generate_candle(self, interval: str = "1m") -> Candle:
        """Generate a single realistic candle."""
        import random
        from decimal import Decimal

        # Random walk with drift
        change = Decimal(str(random.uniform(-1, 1))) * self.volatility * self._current_price
        new_price = self._current_price + change
        new_price = max(new_price, Decimal("0.01"))  # Price can't go below 1 cent

        open_price = self._current_price
        close_price = new_price
        high_price = max(open_price, close_price) * Decimal(str(1 + random.uniform(0, 0.005)))
        low_price = min(open_price, close_price) * Decimal(str(1 - random.uniform(0, 0.005)))

        self._current_price = close_price
        now = datetime.now(timezone.utc)
        interval_seconds = {"1m": 60, "5m": 300, "15m": 900, "1h": 3600}.get(
            interval, 60)

        candle = Candle(
            symbol=self.symbol,
            interval="1m",
            open_time=self._current_time,
            close_time=self._current_time.replace(second=59, microsecond=999999),
            open=open_price,
            high=high_price,
            low=low_price,
            close=close_price,
            volume=Decimal(str(Decimal("10") + Decimal(str(random.uniform(0, 5))))),
        )
        self._current_time = self._current_time.replace(second=0, microsecond=0) + timedelta(seconds=interval_seconds)
        return candle

    def generate_ticker(self) -> dict:
        """Generate a ticker update."""
        import random
        change = Decimal(str(random.uniform(-1, 1))) * self.volatility * self._current_price
        new_price = self._current_price + change
        new_price = max(new_price, Decimal("0.01"))

        return {
            "s": str(self.symbol).replace("/", ""),
            "c": str(new_price),
            "b": str(new_price * Decimal("0.9995")),
            "a": str(new_price * Decimal("1.0005")),
            "v": str(Decimal("100") + Decimal(str(random.uniform(0, 10)))),
            "E": int(Decimal(datetime.now(timezone.utc).timestamp()) * 1000),
        }
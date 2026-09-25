"""Qt-native WebSocket client for real-time chart updates (ROADMAP.md chapter 4.2).

Uses PyQt6.QtWebSockets.QWebSocket for Qt-native WebSocket support.
Provides real-time market data streaming for live chart updates.
"""

from __future__ import annotations

import json
import logging
import random
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Callable, Optional

from PyQt6.QtCore import QObject, QUrl, QTimer, pyqtSignal, pyqtSlot
from PyQt6.QtNetwork import QAbstractSocket
from PyQt6.QtWebSockets import QWebSocket

from crypto_trading_lab.domain.models import Candle, Symbol

logger = logging.getLogger(__name__)


class QtWebSocketError(Exception):
    """Qt WebSocket error."""
    pass


@dataclass(frozen=True)
class TickerData:
    """Real-time ticker data."""
    symbol: str
    price: Decimal
    bid: Decimal | None = None
    ask: Decimal | None = None
    volume: Decimal | None = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class QtWebSocketClient(QObject):
    """Qt-native WebSocket client for real-time market data.
    
    Uses PyQt6.QtWebSockets.QWebSocket for Qt-native WebSocket support.
    Designed for real-time chart updates in the GUI.
    """
    
    # Signals
    ticker_received = pyqtSignal(object)  # TickerData
    candle_received = pyqtSignal(object)   # Candle
    trade_received = pyqtSignal(dict)      # Trade data
    connection_state_changed = pyqtSignal(str)  # ConnectionState
    error_occurred = pyqtSignal(str)       # Error message
    
    def __init__(
        self,
        url: str,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._url = QUrl(url)
        self._socket = QWebSocket(parent=self)
        self._reconnect_timer = QTimer(self)
        self._reconnect_timer.setSingleShot(True)
        self._reconnect_attempt = 0
        self._max_reconnect_attempts = 10
        self._base_reconnect_delay = 1000  # ms
        self._max_reconnect_delay = 60000  # ms
        self._reconnect_jitter = 0.2
        
        # Message tracking for deduplication
        self._seen_ids: set[int] = set()
        self._last_sequence: int | None = None
        self._max_message_history = 10000
        
        # Signal connections
        self._socket.connected.connect(self._on_connected)
        self._socket.disconnected.connect(self._on_disconnected)
        self._socket.errorOccurred.connect(self._on_error)
        self._socket.textMessageReceived.connect(self._on_text_message)
        
        self._reconnect_timer = QTimer(self)
        self._reconnect_timer.setSingleShot(True)
        self._reconnect_timer.timeout.connect(self._attempt_reconnect)
        
        # Message handlers
        self._handlers: dict[str, list[Callable]] = {
            'ticker': [],
            'trade': [],
            'kline': [],
            'depth': [],
        }
        
        self._subscriptions: set[str] = set()
        
    def connect(self) -> None:
        """Open WebSocket connection."""
        if self._socket.state() == QAbstractSocket.SocketState.ConnectedState:
            return
        logger.info("Connecting to %s", self._url.toString())
        self._socket.open(self._url)
        
    def close(self) -> None:
        """Close WebSocket connection."""
        self._reconnect_timer.stop()
        self._socket.close()
        
    def subscribe_ticker(self, symbol: str) -> None:
        """Subscribe to ticker updates for a symbol."""
        stream = self._build_stream_name("ticker", symbol)
        self._subscribe(stream)
        
    def subscribe_trades(self, symbol: str) -> None:
        """Subscribe to trade updates for a symbol."""
        stream = self._build_stream_name("trade", symbol)
        self._subscribe(stream)
        
    def subscribe_kline(self, symbol: str, interval: str) -> None:
        """Subscribe to kline/candlestick updates for a symbol."""
        stream = self._build_stream_name("kline", symbol, interval=interval)
        self._subscribe(stream)
        
    def subscribe_depth(self, symbol: str) -> None:
        """Subscribe to order book depth updates."""
        stream = self._build_stream_name("depth", symbol)
        self._subscribe(stream)
        
    def unsubscribe(self, stream_name: str) -> None:
        """Unsubscribe from a stream."""
        self._socket.sendTextMessage(json.dumps({
            "method": "UNSUBSCRIBE",
            "params": [stream_name],
            "id": int(time.time() * 1000)
        }))
        self._subscriptions.discard(stream_name)
        
    def add_ticker_handler(self, handler: Callable) -> None:
        """Add handler for ticker updates."""
        self._handlers['ticker'].append(handler)
        
    def add_trade_handler(self, handler: Callable) -> None:
        self._handlers['trade'].append(handler)
        
    def add_candle_handler(self, handler: Callable) -> None:
        self._handlers['kline'].append(handler)
        
    def add_depth_handler(self, handler: Callable) -> None:
        self._handlers['depth'].append(handler)
        
    def _build_stream_name(self, channel: str, symbol: str, **kwargs) -> str:
        """Build Binance stream name from channel and symbol."""
        sym = symbol.replace("/", "").lower()
        if channel == "ticker":
            return f"{sym}@ticker"
        elif channel == "trade":
            return f"{sym}@trade"
        elif channel == "kline":
            interval = kwargs.get("interval", "1m")
            return f"{sym}@kline_{interval}"
        elif channel == "depth":
            return f"{sym}@depth"
        raise ValueError(f"Unknown channel: {channel}")
        
    def _subscribe(self, stream: str) -> None:
        if stream not in self._subscriptions:
            self._subscriptions.add(stream)
            if self._socket.state() == QAbstractSocket.SocketState.ConnectedState:
                self._send_subscription(stream)
                
    def _send_subscription(self, stream: str) -> None:
        msg = {
            "method": "SUBSCRIBE",
            "params": [stream],
            "id": int(time.time() * 1000)
        }
        self._socket.sendTextMessage(json.dumps(msg))
        
    @pyqtSlot()
    def _on_connected(self) -> None:
        logger.info("WebSocket connected")
        self._reconnect_attempt = 0
        # Resend subscriptions
        for stream in self._subscriptions:
            self._send_subscription(stream)
        self._emit_state("connected")
        
    @pyqtSlot()
    def _on_disconnected(self) -> None:
        logger.warning("WebSocket disconnected")
        self._emit_state("disconnected")
        self._schedule_reconnect()
        
    @pyqtSlot(QAbstractSocket.SocketError)
    def _on_error(self, error: QAbstractSocket.SocketError) -> None:
        error_msg = self._socket.errorString()
        logger.error("WebSocket error: %s", error_msg)
        self.error_occurred.emit(error_msg)
        self._schedule_reconnect()
        
    @pyqtSlot(str)
    def _on_text_message(self, message: str) -> None:
        try:
            data = json.loads(message)
        except json.JSONDecodeError:
            logger.debug("Invalid JSON received")
            return
            
        # Handle subscription responses
        if 'result' in data or 'id' in data:
            return
            
        # Binance combined stream format: { stream: "...", data: {...} }
        stream = data.get('stream') or data.get('streamName')
        payload = data.get('data') or data
        
        if not payload:
            return
            
        # Route to appropriate handler based on stream type
        if stream and 'ticker' in stream:
            self._handle_ticker(payload)
        elif stream and 'trade' in stream:
            self._handle_trade(payload)
        elif stream and 'kline' in stream:
            self._handle_kline(payload)
        elif stream and 'depth' in stream:
            self._handle_depth(payload)
            
    def _handle_ticker(self, payload: dict) -> None:
        try:
            symbol_str = payload.get('s', '')
            if not symbol_str:
                return
            symbol = symbol_str[:-4] + '/' + symbol_str[-4:]  # BTCUSDT -> BTC/USDT
            
            ticker = TickerData(
                symbol=symbol,
                price=Decimal(payload.get('c', '0')),
                bid=Decimal(payload.get('b', '0')) if payload.get('b') else None,
                ask=Decimal(payload.get('a', '0')) if payload.get('a') else None,
                volume=Decimal(payload.get('v', '0')) if payload.get('v') else None,
            )
            self.ticker_received.emit(ticker)
            for handler in self._handlers.get('ticker', []):
                handler(ticker)
        except Exception as e:
            logger.debug("Error handling ticker: %s", e)
            
    def _handle_trade(self, payload: dict) -> None:
        for handler in self._handlers.get('trade', []):
            handler(payload)
            
    def _handle_kline(self, payload: dict) -> None:
        try:
            k = payload.get('k', {})
            if not k.get('x'):  # x = is_closed
                return
                
            symbol_str = payload.get('s', '')
            symbol = symbol_str[:-4] + '/' + symbol_str[-4:]
            
            candle = Candle(
                symbol=Symbol(symbol),
                interval='1m',  # Will be overridden if needed
                open_time=datetime.fromtimestamp(payload['t'] / 1000, tz=timezone.utc),
                close_time=datetime.fromtimestamp(payload['T'] / 1000, tz=timezone.utc),
                open=Decimal(str(payload.get('o', '0'))),
                high=Decimal(str(payload.get('h', '0'))),
                low=Decimal(str(payload.get('l', '0'))),
                close=Decimal(str(payload.get('c', '0'))),
                volume=Decimal(str(payload.get('v', '0'))),
            )
            self.candle_received.emit(candle)
            for handler in self._handlers.get('kline', []):
                handler(candle)
        except Exception as e:
            logger.debug("Error handling kline: %s", e)
            
    def _handle_depth(self, payload: dict) -> None:
        for handler in self._handlers.get('depth', []):
            handler(payload)
            
    def _schedule_reconnect(self) -> None:
        if self._reconnect_attempt >= 10:
            logger.error("Max reconnect attempts reached")
            return
            
        delay = min(1000 * (2 ** self._reconnect_attempt), 60000)
        jitter = int(delay * 0.2 * (random.random() * 2 - 1))
        delay = max(100, delay + jitter)
        
        self._reconnect_attempt += 1
        QTimer.singleShot(delay, self._attempt_reconnect)
        
    def _attempt_reconnect(self) -> None:
        if self._socket.state() != QAbstractSocket.SocketState.ConnectedState:
            logger.info("Reconnecting... (attempt %d)", self._reconnect_attempt)
            self._socket.open(self._url)
            
    def _emit_state(self, state: str) -> None:
        self.connection_state_changed.emit(state)
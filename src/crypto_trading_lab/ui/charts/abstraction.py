"""Chart abstraction layer (ROADMAP.md chapters 4.2 and 32).

The application talks to charts only through the :class:`ChartView`
port, so the rendering backend (PyQtGraph today; Matplotlib/QtCharts
tomorrow) can be replaced without touching the financial domain or
strategy logic — exactly as chapter 4.2 requires.

Data is separated from visual representation: :class:`CandleSeries`
is plain immutable data; the widget layer never owns market state.
"""

from __future__ import annotations

import abc
from dataclasses import dataclass
from decimal import Decimal
from typing import Sequence

from crypto_trading_lab.domain.models import Candle

__all__ = [
    "CandleSeries",
    "OverlaySeries",
    "ChartView",
    "beginner_chart_explanation",
]


@dataclass(frozen=True)
class CandleSeries:
    """Immutable chart data (chapter 32: separate data from visuals)."""

    symbol: str
    interval: str
    candles: tuple[Candle, ...]

    @classmethod
    def from_candles(
        cls, symbol: str, interval: str, candles: Sequence[Candle]
    ) -> "CandleSeries":
        ordered = tuple(sorted(candles, key=lambda c: c.open_time))
        return cls(symbol=symbol, interval=interval, candles=ordered)

    @property
    def closes(self) -> tuple[Decimal, ...]:
        return tuple(candle.close for candle in self.candles)

    @property
    def times(self) -> tuple[float, ...]:
        """Open times as POSIX timestamps (backend-agnostic)."""
        return tuple(
            candle.open_time.timestamp() for candle in self.candles
        )


@dataclass(frozen=True)
class OverlaySeries:
    """An indicator line/points drawn over the price chart."""

    name: str
    times: tuple[float, ...]
    values: tuple[float | None, ...]
    color: str = "#e0b000"
    width: int = 1
    dashed: bool = False


class ChartView(abc.ABC):
    """Port: what every chart backend must provide (chapter 32)."""

    @abc.abstractmethod
    def set_candles(self, series: CandleSeries) -> None:
        """Replace the OHLCV data; keep zoom when possible."""

    @abc.abstractmethod
    def add_overlay(self, overlay: OverlaySeries) -> None:
        """Draw an indicator series over the candles."""

    @abc.abstractmethod
    def clear_overlays(self) -> None:
        """Remove all indicator overlays."""

    @abc.abstractmethod
    def candle_at(self, index: int) -> Candle | None:
        """Candle at ``index`` for crosshair/tooltip lookups."""


def beginner_chart_explanation(kind: str = "candles") -> str:
    """Chapter 32's beginner panel content, backend-independent."""
    explanations = {
        "candles": (
            "What this chart shows: the price history of one market, one "
            "candle per time interval. Each candle has a body (open to "
            "close) and wicks (high and low).\n\n"
            "How to read it: green candles closed higher than they "
            "opened; red candles closed lower. Tall wicks mean the price "
            "wandered far before settling.\n\n"
            "What beginners often misunderstand: a green candle does not "
            "mean 'good time to buy'. It only describes the past.\n\n"
            "What this chart cannot predict: the next candle. Nobody can "
            "predict it — not this app, not any indicator.\n\n"
            "Simple example: a row of green candles means the price rose "
            "over that period; it says nothing about tomorrow.\n\n"
            "Glossary: see candle, volume, timeframe in the Learning "
            "Center glossary."
        ),
    }
    return explanations.get(kind, explanations["candles"])

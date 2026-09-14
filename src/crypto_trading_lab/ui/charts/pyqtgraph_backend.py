"""PyQtGraph candlestick backend (ROADMAP.md chapter 32).

Implements the :class:`ChartView` port with PyQtGraph: zoom, panning,
crosshair with OHLC information under the cursor, auto-scaling, a
visible-point limit, and correct handling of missing time intervals
(time axis uses real timestamps, so gaps stay gaps — no fake data).
"""

from __future__ import annotations

from decimal import Decimal
from typing import Sequence

import pyqtgraph as pg

from PyQt6.QtCore import Qt

from crypto_trading_lab.domain.models import Candle
from crypto_trading_lab.ui.charts.abstraction import (
    CandleSeries,
    ChartView,
    OverlaySeries,
)

__all__ = ["PyQtGraphCandleChart", "MAX_VISIBLE_POINTS"]

#: Chapter 32: "limit the number of visible points".
MAX_VISIBLE_POINTS = 5_000


class _CandleItem(pg.GraphicsObject):
    """Custom OHLC candlestick graphics item (downsampled input)."""

    def __init__(self, data: list[tuple[float, float, float, float, float]]):
        # data rows: (time, open, high, low, close)
        super().__init__()
        self._data = data
        self._picture = None
        self.generate_picture()

    def generate_picture(self) -> None:
        from PyQt6.QtGui import QPicture, QPainter
        from PyQt6.QtCore import QPointF, QRectF

        self._picture = QPicture()
        if not self._data:
            return
        width = self._bar_width()
        painter = QPainter(self._picture)
        try:
            painter.setPen(pg.mkPen("w"))
            for time, open_, high, low, close in self._data:
                rising = close >= open_
                color = pg.mkColor("#2ecc71" if rising else "#e74c3c")
                painter.setPen(pg.mkPen(color))
                painter.setBrush(pg.mkBrush(color))
                # wick
                painter.drawLine(
                    QPointF(time, low),
                    QPointF(time, high),
                )
                # body
                body_top = max(open_, close)
                body_bottom = min(open_, close)
                if body_top == body_bottom:
                    body_top += 1e-12
                painter.drawRect(
                    QRectF(
                        time - width / 2, body_bottom, width,
                        body_top - body_bottom,
                    )
                )
        finally:
            painter.end()

    def _bar_width(self) -> float:
        if len(self._data) < 2:
            return 1.0
        times = sorted(row[0] for row in self._data)
        gaps = [b - a for a, b in zip(times, times[1:]) if b > a]
        if not gaps:
            return 1.0
        return 0.7 * min(gaps)

    def boundingRect(self):  # noqa: N802 (Qt naming)
        from PyQt6.QtCore import QRectF

        if not self._data:
            return QRectF()
        times = [row[0] for row in self._data]
        lows = [row[3] for row in self._data]
        highs = [row[2] for row in self._data]
        width = self._bar_width()
        return QRectF(
            min(times) - width,
            min(lows),
            (max(times) - min(times)) + 2 * width,
            (max(highs) - min(lows)) or 1.0,
        )

    def paint(self, painter, option, widget=None):  # noqa: ANN001
        if self._picture is not None:
            self._picture.play(painter)


class PyQtGraphCandleChart(pg.PlotWidget):
    """Candlestick chart with crosshair OHLC readout (chapter 32).

    Implements the :class:`ChartView` port (registered below); Qt
    widgets cannot inherit from ABCs due to metaclass conflicts.
    """

    def __init__(self, parent=None, show_beginner_panel: bool = True):
        super().__init__(
            parent,
            background="w",
            axisItems={
                "bottom": pg.DateAxisItem(orientation="bottom")
            },
        )
        self._candles: tuple[Candle, ...] = ()
        self._symbol = ""
        self._interval = ""
        self._overlay_items: list[pg.PlotDataItem] = []
        self._limit_label = None

        self.getPlotItem().showGrid(x=True, y=True, alpha=0.25)
        self.setMouseEnabled(x=True, y=True)  # zoom + panning
        self.setMenuEnabled(True)

        # Crosshair with OHLC info under the cursor (chapter 32).
        self._vline = pg.InfiniteLine(
            angle=90, movable=False, pen=pg.mkPen("#888", style=Qt.PenStyle.DashLine)
        )
        self._hline = pg.InfiniteLine(
            angle=0, movable=False, pen=pg.mkPen("#888", style=Qt.PenStyle.DashLine)
        )
        self._info = pg.TextItem(anchor=(0, 1), color="k")
        plot_item = self.getPlotItem()
        plot_item.addItem(self._vline, ignoreBounds=True)
        plot_item.addItem(self._hline, ignoreBounds=True)
        plot_item.addItem(self._info, ignoreBounds=True)
        self.scene().sigMouseMoved.connect(self._on_mouse_moved)

        if show_beginner_panel:
            self._show_beginner_info()

    # -- ChartView port ----------------------------------------------------

    def set_candles(self, series: CandleSeries) -> None:
        self._symbol = series.symbol
        self._interval = series.interval
        # Chapter 32: limit visible points — downsample oldest-first.
        candles = series.candles
        if len(candles) > MAX_VISIBLE_POINTS:
            candles = candles[-MAX_VISIBLE_POINTS:]
            if self._limit_label is None:
                self._limit_label = pg.TextItem(
                    "showing the most recent 5,000 candles", color="#666"
                )
                self.getPlotItem().addItem(
                    self._limit_label, ignoreBounds=True
                )
        self._candles = candles
        data = [
            (
                candle.open_time.timestamp(),
                float(candle.open),
                float(candle.high),
                float(candle.low),
                float(candle.close),
            )
            for candle in candles
        ]
        self.getPlotItem().clear()
        self._overlay_items = []
        if self._vline is not None:
            plot_item = self.getPlotItem()
            plot_item.addItem(self._vline, ignoreBounds=True)
            plot_item.addItem(self._hline, ignoreBounds=True)
            plot_item.addItem(self._info, ignoreBounds=True)
        if data:
            self.getPlotItem().addItem(_CandleItem(data))
            self.autoRange()

    def add_overlay(self, overlay: OverlaySeries) -> None:
        pen = pg.mkPen(
            overlay.color,
            width=overlay.width,
            style=Qt.PenStyle.DashLine if overlay.dashed else Qt.PenStyle.SolidLine,
        )
        # None values must break the line, not drop to zero.
        xs: list[float] = []
        ys: list[float] = []
        for time, value in zip(overlay.times, overlay.values):
            xs.append(time)
            ys.append(float("nan") if value is None else value)
        item = self.getPlotItem().plot(xs, ys, pen=pen, name=overlay.name)
        self._overlay_items.append(item)

    def clear_overlays(self) -> None:
        for item in self._overlay_items:
            self.getPlotItem().removeItem(item)
        self._overlay_items = []

    def candle_at(self, index: int) -> Candle | None:
        if 0 <= index < len(self._candles):
            return self._candles[index]
        return None

    # -- crosshair -----------------------------------------------------------

    def _on_mouse_moved(self, position) -> None:
        if not self._candles:
            return
        view = self.getPlotItem().getViewBox()
        if self.sceneBoundingRect().contains(position):
            mouse_point = view.mapSceneToView(position)
            self._vline.setPos(mouse_point.x())
            self._hline.setPos(mouse_point.y())
            candle = self._nearest_candle(mouse_point.x())
            if candle is not None:
                self._info.setHtml(self._ohlcv_html(candle))
                self._info.setPos(mouse_point.x(), view.viewRect().top())
        else:
            self._info.setHtml("")

    def _nearest_candle(self, x: float) -> Candle | None:
        if not self._candles:
            return None
        best = None
        best_distance = None
        for candle in self._candles:
            distance = abs(candle.open_time.timestamp() - x)
            if best_distance is None or distance < best_distance:
                best_distance = distance
                best = candle
        return best

    @staticmethod
    def _ohlcv_html(candle: Candle) -> str:
        time = candle.open_time.strftime("%Y-%m-%d %H:%M")
        return (
            f"<b>{time} UTC</b><br>"
            f"O {candle.open} &nbsp; H {candle.high}<br>"
            f"L {candle.low} &nbsp; C {candle.close}<br>"
            f"V {candle.volume}"
        )

    def _show_beginner_info(self) -> None:
        from crypto_trading_lab.ui.charts.abstraction import (
            beginner_chart_explanation,
        )

        self.getPlotItem().setTitle(
            "Candles — hover for OHLC. Green = rose, red = fell. "
            "See Learning Center: this describes the past, never the future."
        )
        self.setToolTip(beginner_chart_explanation("candles"))

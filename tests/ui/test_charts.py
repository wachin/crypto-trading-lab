"""Tests for the chart layer (ROADMAP.md chapter 32).

GUI tests run offscreen; the abstraction layer is tested without Qt at
all, and the PyQtGraph backend is exercised as a ChartView port.
"""

from __future__ import annotations

import os

import pytest

pytest.importorskip("pyqtgraph")

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from datetime import datetime, timedelta, timezone  # noqa: E402
from decimal import Decimal  # noqa: E402

from crypto_trading_lab.domain.models import Candle, Symbol  # noqa: E402
from crypto_trading_lab.ui.charts.abstraction import (  # noqa: E402
    CandleSeries,
    OverlaySeries,
    beginner_chart_explanation,
)

BASE = datetime(2024, 1, 1, tzinfo=timezone.utc)


def _candles(count=10, gap_minutes=0):
    out = []
    for i in range(count):
        start = BASE + timedelta(minutes=i + i * gap_minutes)
        out.append(
            Candle(
                Symbol("BTC/USDT"),
                "1m",
                start,
                start + timedelta(minutes=1),
                Decimal("100"),
                Decimal("110"),
                Decimal("90"),
                Decimal("105" if i % 2 == 0 else "95"),
                Decimal("10"),
            )
        )
    return out


# -- data layer (no Qt) -------------------------------------------------------


def test_candle_series_sorts_by_time():
    candles = _candles(5)
    shuffled = [candles[3], candles[0], candles[2], candles[1], candles[4]]
    series = CandleSeries.from_candles("BTC/USDT", "1m", shuffled)
    assert series.candles == tuple(sorted(shuffled, key=lambda c: c.open_time))


def test_candle_series_closes_and_times():
    series = CandleSeries.from_candles("BTC/USDT", "1m", _candles(3))
    assert series.closes == (Decimal("105"), Decimal("95"), Decimal("105"))
    assert len(series.times) == 3
    assert series.times[1] > series.times[0]


def test_beginner_explanation_has_mandated_sections():
    text = beginner_chart_explanation("candles")
    for section in (
        "What this chart shows",
        "How to read it",
        "often misunderstand",
        "cannot predict",
        "Simple example",
        "Glossary",
    ):
        assert section in text


# -- backend (offscreen Qt) ----------------------------------------------------


@pytest.fixture()
def chart(qapp):
    from crypto_trading_lab.ui.charts.pyqtgraph_backend import (
        PyQtGraphCandleChart,
    )

    widget = PyQtGraphCandleChart()
    yield widget
    widget.close()


def test_backend_is_a_chart_view_port(chart):
    from crypto_trading_lab.ui.charts.abstraction import ChartView

    assert isinstance(chart, ChartView) is False  # Qt metaclass
    # But it provides the full port surface:
    for method in ("set_candles", "add_overlay", "clear_overlays", "candle_at"):
        assert callable(getattr(chart, method))


def test_set_candles_then_lookup(chart):
    candles = _candles(5)
    chart.set_candles(CandleSeries.from_candles("BTC/USDT", "1m", candles))
    assert chart.candle_at(0) is candles[0]
    assert chart.candle_at(4) is candles[4]
    assert chart.candle_at(-1) is None
    assert chart.candle_at(99) is None


def test_overlay_none_values_do_not_crash(chart):
    candles = _candles(5)
    chart.set_candles(CandleSeries.from_candles("BTC/USDT", "1m", candles))
    chart.add_overlay(
        OverlaySeries(
            "SMA(3)",
            tuple(c.open_time.timestamp() for c in candles),
            (None, None, 2.0, 3.0, 4.0),
        )
    )
    chart.clear_overlays()


def test_large_series_is_downsampled(chart):
    candles = _candles(6_000)
    chart.set_candles(CandleSeries.from_candles("BTC/USDT", "1m", candles))
    # Visible-point limit: only the most recent 5,000 remain.
    assert chart.candle_at(0).open_time > candles[0].open_time


def test_empty_series_renders_without_crash(chart):
    chart.set_candles(CandleSeries("BTC/USDT", "1m", ()))
    assert chart.candle_at(0) is None


def test_missing_intervals_stay_missing(chart):
    # A 10-minute gap must not be filled with fake candles; the axis is
    # real time, so the gap simply shows as empty space.
    candles = _candles(3, gap_minutes=10)
    chart.set_candles(CandleSeries.from_candles("BTC/USDT", "1m", candles))
    first, second = chart.candle_at(0), chart.candle_at(1)
    gap = second.open_time - first.open_time
    assert gap == timedelta(minutes=11)  # 10-minute market gap + 1m candle

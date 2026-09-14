"""GUI tests for the chart window flow (chapter 32)."""

from __future__ import annotations

import pytest

pytest.importorskip("pyqtgraph")

from crypto_trading_lab.configuration.xdg import AppPaths  # noqa: E402

HEADER = "timestamp,open,high,low,close,volume\n"
ROWS = "".join(
    f"2024-01-01T00:{m:02d}:00+00:00,100,110,90,105,10\n" for m in range(5)
)


@pytest.fixture()
def isolated_xdg(tmp_path):
    return AppPaths(
        config_dir=tmp_path / "config",
        data_dir=tmp_path / "data",
        cache_dir=tmp_path / "cache",
        log_dir=tmp_path / "logs",
    )


def test_open_chart_without_data_returns_none(window, isolated_xdg):
    chart = window.open_chart(paths=isolated_xdg, notify=False)
    assert chart is None  # no crash, no modal dialog in tests


def test_import_then_open_chart_shows_candles(window, isolated_xdg, tmp_path):
    csv_path = tmp_path / "candles.csv"
    csv_path.write_text(HEADER + ROWS, encoding="utf-8")
    message = window.load_csv_file(str(csv_path), paths=isolated_xdg)
    assert "Imported 5 candles" in message
    chart = window.open_chart(paths=isolated_xdg, notify=False)
    assert chart is not None
    assert chart.candle_at(0) is not None
    assert chart.candle_at(4) is not None
    chart.close()

"""Tests for the historical data screen (chapters 26.2, 28 and 29).

The fake source keeps the suite offline; the temp AppPaths keeps the
user's real data directory untouched.
"""

from __future__ import annotations

import urllib.parse
from datetime import datetime, timedelta, timezone

import pytest
from PyQt6.QtCore import QDate

pytest.importorskip("PyQt6")

from crypto_trading_lab.configuration.xdg import AppPaths  # noqa: E402
from crypto_trading_lab.market_data.historical import (  # noqa: E402
    BinanceKlinesSource,
)
from crypto_trading_lab.ui.data.historical_data import (  # noqa: E402
    HistoricalDataWidget,
)

HOUR = timedelta(hours=1)
START = datetime(2024, 1, 1, tzinfo=timezone.utc)


def _kline(open_time: datetime) -> list[object]:
    close_time = open_time + HOUR - timedelta(milliseconds=1)
    return [
        int(open_time.timestamp() * 1000),
        "100",
        "101",
        "99",
        "100",
        "5",
        int(close_time.timestamp() * 1000),
        "500",
        3,
        "2",
        "200",
        "0",
    ]


def _fake_source(count: int = 24) -> BinanceKlinesSource:
    rows = [_kline(START + i * HOUR) for i in range(count)]

    def opener(url: str) -> object:
        query = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
        start = int(query["startTime"][0])
        end = int(query["endTime"][0])
        limit = int(query["limit"][0])
        return [r for r in rows if start <= int(r[0]) <= end][:limit]

    return BinanceKlinesSource(opener=opener, pause_seconds=0)


def _paths(tmp_path) -> AppPaths:
    return AppPaths(
        config_dir=tmp_path / "config",
        data_dir=tmp_path / "data",
        cache_dir=tmp_path / "cache",
        log_dir=tmp_path / "logs",
    )


def test_widget_builds_a_valid_request(qapp, tmp_path):
    widget = HistoricalDataWidget(source=_fake_source(), paths=_paths(tmp_path))
    widget.symbol_combo.setCurrentText("BTC/USDT")
    widget.interval_combo.setCurrentText("1h")
    widget.start_date.setDate(QDate(2024, 1, 1))
    widget.end_date.setDate(QDate(2024, 1, 2))

    request = widget.build_request()

    assert request.exchange == "binance"
    assert request.symbol == "BTC/USDT"
    assert request.interval == "1h"
    assert request.start.tzinfo is not None
    widget.close()


def test_download_shows_the_dataset_card(qapp, tmp_path):
    widget = HistoricalDataWidget(source=_fake_source(24), paths=_paths(tmp_path))
    widget.symbol_combo.setCurrentText("BTC/USDT")
    widget.interval_combo.setCurrentText("1h")
    widget.start_date.setDate(QDate(2024, 1, 1))
    widget.end_date.setDate(QDate(2024, 1, 2))

    outcome = widget.download()
    text = widget.data_view.toPlainText()

    assert outcome is not None
    assert outcome.version.candle_count == 24
    assert "BINANCE_BTCUSDT_1H_2024-01-01_2024-01-02_V1" in text
    assert "ready for research" in text
    assert "Checksum" in text
    widget.close()


def test_invalid_symbol_is_explained_without_crashing(qapp, tmp_path):
    widget = HistoricalDataWidget(source=_fake_source(), paths=_paths(tmp_path))
    widget.symbol_combo.setCurrentText("NOTAPAIR")
    widget.start_date.setDate(QDate(2024, 1, 1))
    widget.end_date.setDate(QDate(2024, 1, 2))

    outcome = widget.download()

    assert outcome is None
    assert "Please check the form" in widget.data_view.toPlainText()
    widget.close()


def test_every_visible_string_is_translatable(qapp, tmp_path):
    """AGENTS.md rule 7: no hard-coded visible strings in UI code."""
    from pathlib import Path

    source = Path(
        "src/crypto_trading_lab/ui/data/historical_data.py"
    ).read_text(encoding="utf-8")
    assert "self.tr(" in source
    # The download button label must be wrapped, not literal.
    assert 'QPushButton("Download historical data")' not in source

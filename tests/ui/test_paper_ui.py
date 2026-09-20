"""Tests for the paper-trading screen and its journal (chapter 57)."""

from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

pytest.importorskip("PyQt6")

from PyQt6.QtWidgets import QMessageBox  # noqa: E402

from crypto_trading_lab.configuration.xdg import AppPaths  # noqa: E402
from crypto_trading_lab.domain.models import Candle, Symbol  # noqa: E402
from crypto_trading_lab.market_data.historical import DatasetVersion  # noqa: E402
from crypto_trading_lab.ui.paper.paper_trading import PaperTradingWidget  # noqa: E402

HOUR = timedelta(hours=1)
START = datetime(2024, 1, 1, tzinfo=timezone.utc)


def _candles(count: int = 300) -> list[Candle]:
    candles = []
    price = Decimal("100")
    for i in range(count):
        price = max(Decimal("10"), price + Decimal(str(0.5 * math.sin(i / 12.0))))
        open_time = START + i * HOUR
        candles.append(
            Candle(
                symbol=Symbol("BTC/USDT"),
                interval="1h",
                open_time=open_time,
                close_time=open_time + HOUR - timedelta(milliseconds=1),
                open=price,
                high=price + 1,
                low=price - 1,
                close=price,
                volume=Decimal("10"),
            )
        )
    return candles


def _dataset() -> DatasetVersion:
    return DatasetVersion(
        dataset_id="BINANCE_BTCUSDT_1H_2024_V1",
        exchange="binance",
        symbol="BTC/USDT",
        interval="1h",
        start=START,
        end=START + 300 * HOUR,
        candle_count=300,
        missing=0,
        duplicates=0,
        invalid=0,
        checksum="abc",
        source="test",
        downloaded_at=START,
    )


def test_paper_widget_runs_a_session_and_shows_the_journal(qapp):
    widget = PaperTradingWidget(_candles(), _dataset())
    widget.fast_spin_edit.setText("5")
    widget.slow_spin_edit.setText("20")

    result = widget.run_session()

    assert result is not None
    assert widget.last_result is result
    assert "Paper trading account" in widget.account_view.toPlainText()
    assert "Trading journal" in widget.journal_view.toPlainText()
    assert widget.save_button.isEnabled() is True
    widget.close()


def test_paper_widget_refuses_without_data(qapp):
    widget = PaperTradingWidget([], None)

    assert widget.run_session() is None
    assert "download" in widget.status_label.text().lower()
    widget.close()


def test_paper_widget_validates_inputs(qapp):
    widget = PaperTradingWidget(_candles(), _dataset())
    widget.capital_edit.setText("-5")

    assert widget.run_session() is None
    assert "positive" in widget.status_label.text()
    widget.close()


def test_main_window_opens_paper_trading(qapp, tmp_path, monkeypatch):
    from crypto_trading_lab.ui.main_window.window import MainWindow

    monkeypatch.setattr(
        QMessageBox, "information", staticmethod(lambda *a, **k: None)
    )
    window = MainWindow()
    paths = AppPaths(
        config_dir=tmp_path / "c",
        data_dir=tmp_path / "d",
        cache_dir=tmp_path / "k",
        log_dir=tmp_path / "l",
    )
    monkeypatch.setattr(window, "_paths", lambda: paths)

    window._open_paper()

    assert window._paper_window is not None
    window._paper_window.close()
    window.close()

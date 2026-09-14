"""GUI tests for the CSV import flow (chapter 28: summary before import)."""

from __future__ import annotations

import pytest

pytest.importorskip("PyQt6")

from crypto_trading_lab.configuration.xdg import AppPaths  # noqa: E402


HEADER = "timestamp,open,high,low,close,volume\n"
ROWS = "".join(
    f"2024-01-01T00:{m:02d}:00+00:00,100,110,90,105,10\n" for m in range(3)
)


@pytest.fixture()
def isolated_xdg(tmp_path):
    """XDG paths inside tmp_path so no user data is touched."""
    return AppPaths(
        config_dir=tmp_path / "config",
        data_dir=tmp_path / "data",
        cache_dir=tmp_path / "cache",
        log_dir=tmp_path / "logs",
    )


def test_load_csv_file_imports_and_reports(window, isolated_xdg, tmp_path):
    csv_path = tmp_path / "candles.csv"
    csv_path.write_text(HEADER + ROWS, encoding="utf-8")
    message = window.load_csv_file(str(csv_path), paths=isolated_xdg)
    assert "Imported 3 candles" in message
    assert "BTC/USDT" in message
    # The database file was created inside the isolated data dir.
    assert isolated_xdg.database_file.exists()


def test_load_csv_file_reports_errors_without_saving(window, isolated_xdg, tmp_path):
    csv_path = tmp_path / "bad.csv"
    csv_path.write_text(
        HEADER + "2024-01-01T00:00:00+00:00,100,110,90,-5,10\n",
        encoding="utf-8",
    )
    message = window.load_csv_file(str(csv_path), paths=isolated_xdg)
    assert "problems" in message
    # Invalid files must not create a database.
    assert not isolated_xdg.database_file.exists()


def test_invalid_file_is_rejected_before_database(window, isolated_xdg, tmp_path):
    csv_path = tmp_path / "empty.csv"
    csv_path.write_text("time,o,h,l,c\n", encoding="utf-8")
    message = window.load_csv_file(str(csv_path), paths=isolated_xdg)
    assert "could not find" in message
    assert not isolated_xdg.database_file.exists()


def test_reimport_same_file_is_safe(window, isolated_xdg, tmp_path):
    csv_path = tmp_path / "candles.csv"
    csv_path.write_text(HEADER + ROWS, encoding="utf-8")
    first = window.load_csv_file(str(csv_path), paths=isolated_xdg)
    second = window.load_csv_file(str(csv_path), paths=isolated_xdg)
    assert "Imported 3 candles" in first
    assert "Imported 3 candles" in second  # no duplicate errors

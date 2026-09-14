"""Shared pytest fixtures for Qt-based tests."""

from __future__ import annotations

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

pytest.importorskip("PyQt6")

from PyQt6.QtWidgets import QApplication  # noqa: E402


@pytest.fixture(scope="session")
def qapp():
    """One QApplication for the whole test session (offscreen)."""
    app = QApplication.instance() or QApplication([])
    yield app


@pytest.fixture()
def window(qapp):
    """A fresh MainWindow per test, closed afterwards."""
    from crypto_trading_lab.ui.main_window.window import MainWindow

    win = MainWindow()
    yield win
    win.close()

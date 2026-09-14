"""GUI tests for the minimal first-iteration window (chapter 71.1, task 14).

Qt tests need a QApplication and a real display. On headless systems
Debian's python3-pyqt6 provides QT_QPA_PLATFORM=offscreen; pytest-qt is
not required — we drive widgets directly.
"""

from __future__ import annotations

import os

import pytest

pytest.importorskip("PyQt6")

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from crypto_trading_lab.ui.main_window.window import MainWindow, make_app  # noqa: E402
from crypto_trading_lab.i18n.translations import apply_language  # noqa: E402


def test_window_title(window):
    assert window.windowTitle() == "Crypto Trading Lab"


def test_menus_exist(window):
    titles = [menu.title() for menu in window.menuBar().menus()] if hasattr(window.menuBar(), "menus") else []
    if not titles:  # PyQt6 QMenuBar has no .menus(); use actions
        titles = [
            menu.menuAction().text()
            for menu in [
                window.menuBar().actions()[i].menu()
                for i in range(len(window.menuBar().actions()))
            ]
            if menu is not None
        ]
    joined = " ".join(titles)
    assert "&File" in joined
    assert "&View" in joined
    assert "&Tools" in joined
    assert "&Help" in joined


def test_safety_indicators_visible(window):
    assert window.mode_label.text() == "Mode: Paper Trading"
    assert window.real_trading_label.text() == "Real trading: Disabled"
    assert window.status_label.text() == "Disconnected"


def test_backtesting_button_disabled(window):
    assert window.backtesting_button.isEnabled() is False
    assert window.action_backtesting.isEnabled() is False


def test_csv_and_learning_center_buttons_enabled(window):
    assert window.csv_button.isEnabled() is True
    assert window.learning_center_button.isEnabled() is True


def test_educational_farmer_message_present(window):
    # The message must carry the farmer's truth and the no-guarantee duty.
    labels = window.centralWidget().findChildren(type(window.mode_label))
    texts = " ".join(label.text() for label in labels).lower()
    assert "farmer" in texts
    assert "rain" in texts
    assert "cannot guarantee" in texts
    assert "food" in texts
    assert "housing" in texts
    assert "never borrow money" in texts


def test_spanish_translation_changes_indicators(qapp, window):
    apply_language(qapp, "es")
    spanish_window = MainWindow()
    try:
        assert spanish_window.mode_label.text() == "Modo: Trading Simulado"
        assert spanish_window.real_trading_label.text() == "Trading real: Desactivado"
        assert spanish_window.status_label.text() == "Desconectado"
    finally:
        spanish_window.close()
        apply_language(qapp, "en")

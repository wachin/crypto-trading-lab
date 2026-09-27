"""Tests for accessibility helpers (ROADMAP.md chapter 21.3)."""

import pytest
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import QPushButton, QVBoxLayout, QWidget

from crypto_trading_lab.ui.accessibility import AccessibilityHelper
from crypto_trading_lab.ui.main_window.window import MainWindow


def test_accessibility_helper_name_and_description(qtbot):
    button = QPushButton("Test Button")
    qtbot.addWidget(button)

    AccessibilityHelper.set_accessible_name(button, "Accessible Test Button")
    AccessibilityHelper.set_accessible_description(button, "Description for screen readers")

    assert button.accessibleName() == "Accessible Test Button"
    assert button.accessibleDescription() == "Description for screen readers"


def test_accessibility_helper_setup_accessibility(qtbot):
    button = QPushButton("Action")
    qtbot.addWidget(button)

    AccessibilityHelper.setup_accessibility(
        button,
        name="Action Button",
        description="Detailed description",
        tooltip="Quick tooltip",
    )

    assert button.accessibleName() == "Action Button"
    assert button.accessibleDescription() == "Detailed description"
    assert button.toolTip() == "Quick tooltip"


def test_accessibility_helper_set_tab_order(qtbot):
    parent = QWidget()
    qtbot.addWidget(parent)
    layout = QVBoxLayout(parent)
    buttons = [QPushButton(str(index)) for index in range(3)]
    for button in buttons:
        layout.addWidget(button)

    AccessibilityHelper.set_tab_order(buttons)

    # The tab order must actually be applied, not silently dropped.
    assert buttons[0].nextInFocusChain() is buttons[1]
    assert buttons[1].nextInFocusChain() is buttons[2]


def test_accessibility_helper_set_tab_order_across_windows_is_an_error(qtbot):
    first = QPushButton("1")
    second = QPushButton("2")
    qtbot.addWidget(first)
    qtbot.addWidget(second)

    # Qt would only print a warning and leave the order untouched.
    with pytest.raises(ValueError):
        AccessibilityHelper.set_tab_order([first, second])


def test_accessibility_format_status_text():
    ok_text = AccessibilityHelper.format_status_text("Connected", is_positive=True)
    warn_text = AccessibilityHelper.format_status_text("Degraded", is_positive=False)
    info_text = AccessibilityHelper.format_status_text("Idle", is_positive=None)

    assert "[OK]" in ok_text and "Connected" in ok_text
    assert "[WARN]" in warn_text and "Degraded" in warn_text
    assert "[INFO]" in info_text and "Idle" in info_text


def test_accessibility_contrast_recommendations():
    dark_color = QColor(20, 20, 20)
    light_color = QColor(240, 240, 240)

    assert AccessibilityHelper.recommend_contrast_text(dark_color) == "white"
    assert AccessibilityHelper.recommend_contrast_text(light_color) == "black"


def test_main_window_accessibility(qtbot):
    window = MainWindow()
    qtbot.addWidget(window)

    # Check button accessible names and tooltips
    assert window.historical_data_button.accessibleName() != ""
    assert window.csv_button.accessibleName() != ""
    assert window.chart_button.accessibleName() != ""
    assert window.learning_center_button.accessibleName() != ""
    assert window.backtesting_button.accessibleName() != ""
    assert window.wizard_button.accessibleName() != ""
    assert window.paper_button.accessibleName() != ""

    assert window.historical_data_button.toolTip() != ""
    assert window.backtesting_button.toolTip() != ""

    # Check keyboard shortcuts
    assert not window.historical_data_button.shortcut().isEmpty()
    assert not window.learning_center_button.shortcut().isEmpty()
    assert not window.backtesting_button.shortcut().isEmpty()

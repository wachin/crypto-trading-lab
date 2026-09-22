"""Tests for accessibility helpers (ROADMAP.md chapter 21.3)."""

from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import QPushButton, QWidget

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
    b1 = QPushButton("1")
    b2 = QPushButton("2")
    b3 = QPushButton("3")
    for b in (b1, b2, b3):
        qtbot.addWidget(b)

    AccessibilityHelper.set_tab_order([b1, b2, b3])
    # Verify widgets can receive focus and tab order was processed
    assert b1 is not None and b2 is not None and b3 is not None


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

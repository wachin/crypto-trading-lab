"""Tests for lesson-to-screen links (chapter 80)."""

from PyQt6.QtWidgets import QApplication

from crypto_trading_lab.configuration.xdg import AppPaths
from crypto_trading_lab.ui.education.learning_center import (
    LESSON_SCREEN_MAP,
    LearningCenterWidget,
)


def test_lesson_screen_map_coverage():
    """Verify mapped lessons cover key tools."""
    tools = {tool for tool, _ in LESSON_SCREEN_MAP.values()}
    assert "chart" in tools
    assert "historical_data" in tools
    assert "strategy_builder" in tools
    assert "backtesting" in tools
    assert "paper" in tools
    assert "wizard" in tools
    assert len(LESSON_SCREEN_MAP) >= 30


def test_open_tool_button_state(tmp_path):
    """Button enables when lesson has mapped tool, disables otherwise."""
    app = QApplication.instance() or QApplication([])
    paths = AppPaths(data_dir=tmp_path / "data", config_dir=tmp_path / "config")
    widget = LearningCenterWidget(paths)

    # Lesson 1 has no tool
    widget.show_lesson(1)
    assert not widget.open_tool_button.isEnabled()

    # Lesson 20 maps to chart
    widget.show_lesson(20)
    assert widget.open_tool_button.isEnabled()
    assert "chart" in widget.open_tool_button.toolTip().lower()

    # Lesson 38 maps to backtesting
    widget.show_lesson(38)
    assert widget.open_tool_button.isEnabled()
    assert "backtesting" in widget.open_tool_button.toolTip().lower()

    widget.close()

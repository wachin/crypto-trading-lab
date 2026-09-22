"""Accessibility utilities for Qt UI components (ROADMAP.md chapter 21.3).

Provides helpers for making UI more accessible without requiring additional dependencies.

Focuses on:
- Accessible name/description setting for screen readers
- Tab order management for keyboard navigation
- Tooltips and shortcuts
- Color-independent status formatting
- High contrast mode detection
"""

from __future__ import annotations

from PyQt6.QtCore import QObject
from PyQt6.QtGui import QColor, QPalette
from PyQt6.QtWidgets import QApplication, QWidget


class AccessibilityHelper(QObject):
    """Helper for making Qt widgets accessible to screen readers and keyboard users."""

    @staticmethod
    def set_accessible_name(widget: QWidget, name: str) -> None:
        """Set accessible name for screen readers."""
        widget.setAccessibleName(name)

    @staticmethod
    def set_accessible_description(widget: QWidget, description: str) -> None:
        """Set accessible description for screen readers."""
        widget.setAccessibleDescription(description)

    @staticmethod
    def setup_accessibility(
        widget: QWidget,
        name: str,
        description: str | None = None,
        tooltip: str | None = None,
    ) -> None:
        """Configure accessibility metadata for a widget in one call."""
        widget.setAccessibleName(name)
        if description:
            widget.setAccessibleDescription(description)
        if tooltip:
            widget.setToolTip(tooltip)

    @staticmethod
    def set_tab_order(widgets: list[QWidget]) -> None:
        """Set logical tab order for keyboard navigation across a sequence of widgets."""
        for i in range(len(widgets) - 1):
            QWidget.setTabOrder(widgets[i], widgets[i + 1])

    @staticmethod
    def format_status_text(state_name: str, is_positive: bool | None = None) -> str:
        """Format status text so information does not depend solely on color.

        Includes a text-based symbol indicator ([OK], [WARN], [FAIL], [INFO])
        so screen readers and color-blind users can easily distinguish states.
        """
        if is_positive is True:
            return f"[OK] {state_name}"
        elif is_positive is False:
            return f"[WARN] {state_name}"
        return f"[INFO] {state_name}"

    @staticmethod
    def is_high_contrast_enabled() -> bool:
        """Check if system high contrast mode is active."""
        palette = QApplication.palette()
        window_color = palette.color(QPalette.ColorRole.Window)
        text_color = palette.color(QPalette.ColorRole.WindowText)

        window_brightness = (
            window_color.red() * 0.299 +
            window_color.green() * 0.587 +
            window_color.blue() * 0.114
        )
        text_brightness = (
            text_color.red() * 0.299 +
            text_color.green() * 0.587 +
            text_color.blue() * 0.114
        )

        return abs(window_brightness - text_brightness) > 150

    @staticmethod
    def recommend_contrast_text(window_color: QColor) -> str:
        """Recommend text color for best contrast against a window background."""
        window_brightness = (
            window_color.red() * 0.299 +
            window_color.green() * 0.587 +
            window_color.blue() * 0.114
        )

        return "white" if window_brightness < 128 else "black"


# Example usage pattern (commented out to avoid automatic execution):
# helper = AccessibilityHelper()
# helper.set_accessible_name(my_button, "Submit form")
# helper.set_tab_order([button1, button2, button3])
# if AccessibilityHelper.is_high_contrast_enabled():
#     print("High contrast mode is active")
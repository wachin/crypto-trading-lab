"""Accessibility utilities for Qt UI components.

Provides helpers for making UI more accessible without requiring additional dependencies.

This module focuses on:
- Accessible name/description setting
- Tab order management  
- High contrast mode detection
- Without requiring new package installations
"""

from __future__ import annotations

from PyQt6.QtCore import QEvent, QObject, Qt
from PyQt6.QtGui import QColor, QPalette
from PyQt6.QtWidgets import QApplication, QWidget


class AccessibilityHelper(QObject):
    """Helper for making Qt widgets more accessible.

    Provides static methods for common accessibility tasks
    that work within the existing Qt framework.
    """

    @staticmethod
    def set_accessible_name(widget: QWidget, name: str) -> None:
        """Set accessible name for screen readers.

        Args:
            widget: The widget to set the name on
            name: The accessible name string
        """
        widget.setAccessibleName(name)

    @staticmethod
    def set_accessible_description(widget: QWidget, description: str) -> None:
        """Set accessible description for screen readers.

        Args:
            widget: The widget to set the description on
            description: The accessible description string
        """
        widget.setAccessibleDescription(description)

    @staticmethod
    def set_tab_order(widgets: list[QWidget]) -> None:
        """Set logical tab order for keyboard navigation.

        Args:
            widgets: List of widgets to set tab order for
        """
        for i in range(len(widgets) - 1):
            widgets[i].setFocusProxy(widgets[i + 1])

    @staticmethod
    def is_high_contrast_enabled() -> bool:
        """Check if system high contrast mode is active.

        Returns:
            True if high contrast mode is detected, False otherwise.
        """
        palette = QApplication.palette()
        window_color = palette.color(QPalette.ColorRole.Window)
        text_color = palette.color(QPalette.ColorRole.WindowText)

        # Simple brightness difference heuristic
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

        # High contrast typically has > 150 difference in brightness
        return abs(window_brightness - text_brightness) > 150

    @staticmethod
    def recommend_contrast_text(window_color: QColor) -> str:
        """Recommend text color for best contrast against a window background.

        Args:
            window_color: The background color to check contrast against

        Returns:
            Either "black" or "white" depending on which provides better contrast
        """
        window_brightness = (
            window_color.red() * 0.299 +
            window_color.green() * 0.587 +
            window_color.blue() * 0.114
        )

        # Use white text on dark backgrounds, black text on light backgrounds
        return "white" if window_brightness < 128 else "black"


# Example usage pattern (commented out to avoid automatic execution):
# helper = AccessibilityHelper()
# helper.set_accessible_name(my_button, "Submit form")
# helper.set_tab_order([button1, button2, button3])
# if AccessibilityHelper.is_high_contrast_enabled():
#     print("High contrast mode is active")
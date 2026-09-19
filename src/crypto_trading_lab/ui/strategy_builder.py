"""Strategy Builder UI (Chapter 34).

Visual block-based strategy builder.
"""

from __future__ import annotations

from PyQt6.QtWidgets import (
    QGroupBox,
    QApplication,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)
from PyQt6.QtCore import Qt


class StrategyBuilderDialog(QDialog):
    """Visual strategy builder."""

    def __init__(self, parent: QWidget = None):
        super().__init__(parent)
        self.setWindowTitle("Strategy Builder")
        self.resize(800, 600)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout()

        # Header
        header = QLabel("Visual Strategy Builder")
        header.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(header)

        # Block palette
        palette = QGroupBox("Block Palette")
        palette_layout = QHBoxLayout()

        self.indicator_btn = QPushButton("Indicator")
        self.indicator_btn.clicked.connect(lambda: self._add_block("indicator"))
        palette_layout.addWidget(self.indicator_btn)

        self.operator_btn = QPushButton("Operator")
        self.operator_btn.clicked.connect(lambda: self._add_block("operator"))
        palette_layout.addWidget(self.operator_btn)

        self.value_btn = QPushButton("Value")
        self.value_btn.clicked.connect(lambda: self._add_block("value"))
        palette_layout.addWidget(self.value_btn)

        self.condition_btn = QPushButton("Condition")
        self.condition_btn.clicked.connect(lambda: self._add_block("condition"))
        palette_layout.addWidget(self.condition_btn)

        self.entry_btn = QPushButton("Entry")
        self.entry_btn.clicked.connect(lambda: self._add_block("entry"))
        palette_layout.addWidget(self.entry_btn)

        self.exit_btn = QPushButton("Exit")
        self.exit_btn.clicked.connect(lambda: self._add_block("exit"))
        palette_layout.addWidget(self.exit_btn)

        palette.setLayout(palette_layout)
        layout.addWidget(palette)

        # Build area
        self.build_area = QGroupBox("Strategy Blocks")
        self.build_layout = QVBoxLayout()
        self.build_layout.addStretch()
        self.build_area.setLayout(self.build_layout)
        layout.addWidget(self.build_area)

        # Validation status
        self.status_label = QLabel("No blocks added yet")
        layout.addWidget(self.status_label)

        # Buttons
        self.validate_btn = QPushButton("Validate")
        self.validate_btn.clicked.connect(self._validate)
        layout.addWidget(self.validate_btn)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.setLayout(layout)

    def _add_block(self, block_type: str):
        """Add a block to the strategy."""
        label = QLabel(f"{block_type.title()} Block")
        label.setStyleSheet("border: 1px solid gray; padding: 4px;")
        self.build_layout.insertWidget(self.build_layout.count() - 1, label)
        self.status_label.setText(f"{self.build_layout.count() - 1} blocks")

    def _validate(self):
        """Validate the strategy."""
        from crypto_trading_lab.strategy_registry import StrategyRegistry
        registry = StrategyRegistry()

        if self.build_layout.count() < 3:
            QMessageBox.warning(self, "Validation", "Add more blocks")
            return

        # Check for required blocks
        has_entry = any(
            isinstance(w, QLabel) and "entry" in w.text().lower()
            for w in self.build_layout
        )
        has_exit = any(
            isinstance(w, QLabel) and "exit" in w.text().lower()
            for w in self.build_layout
        )

        if has_entry and has_exit:
            QMessageBox.information(self, "Validation", "Strategy has entry and exit")
        else:
            QMessageBox.warning(self, "Validation", "Strategy needs entry and exit signals")


def show_strategy_builder() -> None:
    """Launch the strategy builder."""
    import sys
    app = QApplication.instance() or QApplication(sys.argv)
    try:
        dialog = StrategyBuilderDialog()
        dialog.exec()
    except Exception as e:
        QMessageBox.critical(
            None,
            "Error",
            f"Failed to open Strategy Builder: {str(e)}"
        )
    """Launch the strategy builder."""
    import sys
    app = QApplication.instance() or QApplication(sys.argv)
    dialog = StrategyBuilderDialog()
    dialog.exec()


__all__ = ["StrategyBuilderDialog", "show_strategy_builder"]

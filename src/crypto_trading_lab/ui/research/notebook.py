"""Research notebook UI (Chapter 54).

Provides a simple notebook interface for documenting research experiments.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from PyQt6.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)
from PyQt6.QtCore import Qt


class NotebookEntry:
    """A single research notebook entry."""

    def __init__(
        self,
        experiment_id: str,
        hypothesis: str,
        notes: str,
        created_at: datetime = None,
    ):
        self.experiment_id = experiment_id
        self.hypothesis = hypothesis
        self.notes = notes
        self.created_at = created_at or datetime.now(timezone.utc)


class NotebookEditor(QDialog):
    """Editor for creating research notebook entries."""

    def __init__(
        self,
        experiment_id: str = None,
        parent: QWidget = None,
    ):
        super().__init__(parent)
        self.setWindowTitle("Research Notebook Entry")
        self.resize(600, 500)
        self.experiment_id = experiment_id

        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout()

        # Experiment ID
        id_group = QGroupBox("Experiment ID")
        id_layout = QHBoxLayout()
        self.id_field = QLineEdit()
        if self.experiment_id:
            self.id_field.setText(self.experiment_id)
            self.id_field.setEnabled(False)
        id_layout.addWidget(self.id_field)
        id_group.setLayout(id_layout)
        layout.addWidget(id_group)

        # Hypothesis
        hyp_group = QGroupBox("Hypothesis")
        hyp_layout = QVBoxLayout()
        self.hyp_field = QTextEdit()
        self.hyp_field.setMaximumHeight(80)
        self.hyp_field.setPlaceholderText("Enter your research hypothesis...")
        hyp_layout.addWidget(self.hyp_field)
        hyp_group.setLayout(hyp_layout)
        layout.addWidget(hyp_group)

        # Notes
        notes_group = QGroupBox("Notes")
        notes_layout = QVBoxLayout()
        self.notes_field = QTextEdit()
        self.notes_field.setPlaceholderText("Document your research process, observations, and conclusions...")
        notes_layout.addWidget(self.notes_field)
        notes_group.setLayout(notes_layout)
        layout.addWidget(notes_group)

        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save |
            QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.setLayout(layout)

    def get_entry(self) -> Optional[NotebookEntry]:
        """Get the created entry."""
        if not self.hyp_field.toPlainText().strip():
            return None

        return NotebookEntry(
            experiment_id=self.id_field.text() or f"exp_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            hypothesis=self.hyp_field.toPlainText(),
            notes=self.notes_field.toPlainText(),
        )


class NotebookViewer(QDialog):
    """Viewer for research notebook entries."""

    def __init__(self, entries: List[NotebookEntry], parent: QWidget = None):
        super().__init__(parent)
        self.setWindowTitle("Research Notebook")
        self.resize(800, 600)
        self.entries = entries

        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout()

        # Header
        header = QLabel(f"Research Notebook ({len(self.entries)} entries)")
        header.setStyleSheet("font-size: 14px; font-weight: bold;")
        layout.addWidget(header)

        # Entries
        scroll = QWidget()
        scroll_layout = QVBoxLayout()
        scroll_layout.setContentsMargins(0, 0, 0, 0)

        for entry in self.entries:
            group = QGroupBox()
            group_layout = QVBoxLayout()
            group_layout.setContentsMargins(12, 12, 12, 12)

            # Header row
            row = QHBoxLayout()
            exp_label = QLabel(f"ID: {entry.experiment_id}")
            date_label = QLabel(entry.created_at.strftime("%Y-%m-%d %H:%M"))
            row.addWidget(exp_label)
            row.addStretch()
            row.addWidget(date_label)
            group_layout.addLayout(row)

            # Hypothesis
            hyp_label = QLabel("Hypothesis:")
            hyp_label.setStyleSheet("font-weight: bold;")
            group_layout.addWidget(hyp_label)
            hyp_text = QLabel(entry.hypothesis)
            hyp_text.setWordWrap(True)
            group_layout.addWidget(hyp_text)

            # Notes
            notes_label = QLabel("Notes:")
            notes_label.setStyleSheet("font-weight: bold;")
            group_layout.addWidget(notes_label)
            notes_text = QLabel(entry.notes)
            notes_text.setWordWrap(True)
            group_layout.addWidget(notes_text)

            group_layout.addStretch()
            group.setLayout(group_layout)
            scroll_layout.addWidget(group)

        scroll.setLayout(scroll_layout)
        layout.addWidget(scroll)

        self.setLayout(layout)


def create_notebook_entry(experiment_id: str = None) -> Optional[NotebookEntry]:
    """Open editor and create a new entry."""
    import sys
    app = QApplication.instance() or QApplication(sys.argv)
    dialog = NotebookEditor(experiment_id)
    if dialog.exec():
        return dialog.get_entry()
    return None


def view_notebook(entries: List[NotebookEntry]) -> None:
    """View research notebook entries."""
    import sys
    app = QApplication.instance() or QApplication(sys.argv)
    dialog = NotebookViewer(entries)
    dialog.exec()


__all__ = [
    "NotebookEntry",
    "NotebookEditor",
    "NotebookViewer",
    "create_notebook_entry",
    "view_notebook",
]

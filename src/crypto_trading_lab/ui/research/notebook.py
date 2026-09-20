"""Research notebook (chapters 52-54, analysis §6).

The trader's scientific notebook. Every entry *is* an experiment
record: hypothesis, dataset identity and checksum, parameters,
execution assumptions, metrics, conclusion and research notes. Nothing
here is decorative — the widget reads and writes the same
``ExperimentManager`` the wizard and the CLI use.
"""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)
from PyQt6.QtCore import Qt

from crypto_trading_lab.machine_learning.experiment_manager import (
    ExperimentManager,
    ExperimentRecord,
    ExperimentStatus,
)

__all__ = ["NotebookDialog", "render_experiment", "render_comparison"]

#: Fields shown, in order, when a record is opened.
_RECORD_FIELDS = (
    "experiment_id",
    "hypothesis",
    "strategy_name",
    "strategy_version",
    "dataset_id",
    "dataset_version",
    "dataset_checksum",
    "status",
    "conclusion",
    "notes",
)


def render_experiment(record: ExperimentRecord) -> str:
    """Full notebook entry for one experiment (chapter 52)."""
    lines = ["== Experiment =="]
    for field_name in _RECORD_FIELDS:
        value = getattr(record, field_name)
        if not value:
            continue
        if field_name == "status":
            value = record.status.value
        lines.append(f"{field_name}: {value}")
    lines.append(f"timestamp: {record.timestamp.isoformat()}")
    if record.random_seed is not None:
        lines.append(f"random_seed: {record.random_seed}")
    if record.tags:
        lines.append("tags: " + ", ".join(record.tags))

    for title, mapping in (
        ("Parameters", record.parameters),
        ("Execution assumptions", record.execution_assumptions),
        ("Results (from the backtest)", record.metrics),
    ):
        if mapping:
            lines.append("")
            lines.append(f"== {title} ==")
            lines.extend(f"  {k}: {v}" for k, v in mapping.items())
    return "\n".join(lines)


def render_comparison(comparison: dict) -> str:
    """Side-by-side experiment comparison (chapter 52.3)."""
    rows = comparison.get("rows", [])
    if not rows:
        return "No experiments selected."
    lines = ["== Experiment comparison =="]
    for row in rows:
        lines.append("")
        lines.append(f"- {row['experiment_id'][:8]}: {row['hypothesis']}")
        lines.append(
            f"    strategy: {row['strategy_name']} "
            f"(v{row['strategy_version']}), status: {row['status']}"
        )
        lines.append(f"    dataset: {row['dataset_id']}")
        for key, value in row["metrics"].items():
            if value:
                lines.append(f"    {key}: {value}")
        if row["conclusion"]:
            lines.append(f"    conclusion: {row['conclusion']}")
    return "\n".join(lines)


class NotebookDialog(QDialog):
    """Browse, create and annotate experiment records."""

    def __init__(self, manager: ExperimentManager, parent: QWidget | None = None):
        super().__init__(parent)
        self._manager = manager
        self.setWindowTitle(self.tr("Research Notebook"))
        self.resize(920, 640)

        layout = QVBoxLayout(self)

        search_row = QHBoxLayout()
        search_row.addWidget(QLabel(self.tr("Search:")))
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText(
            self.tr("hypothesis, strategy, dataset, tag…")
        )
        self.search_edit.textChanged.connect(self.refresh)
        search_row.addWidget(self.search_edit)
        layout.addLayout(search_row)

        body = QHBoxLayout()
        self.list_widget = QListWidget()
        self.list_widget.setSelectionMode(
            QAbstractItemView.SelectionMode.ExtendedSelection
        )
        self.list_widget.currentItemChanged.connect(self._on_selection)
        body.addWidget(self.list_widget, 2)

        self.detail = QTextBrowser()
        body.addWidget(self.detail, 3)
        layout.addLayout(body)

        buttons = QHBoxLayout()
        self.new_button = QPushButton(self.tr("New entry"))
        self.new_button.clicked.connect(self.create_entry_interactive)
        self.note_button = QPushButton(self.tr("Add note"))
        self.note_button.clicked.connect(self.add_note_interactive)
        self.compare_button = QPushButton(self.tr("Compare selected"))
        self.compare_button.clicked.connect(self.compare_selected)
        self.export_button = QPushButton(self.tr("Export…"))
        self.export_button.clicked.connect(self.export_interactive)
        for button in (
            self.new_button,
            self.note_button,
            self.compare_button,
            self.export_button,
        ):
            buttons.addWidget(button)
        layout.addLayout(buttons)

        self.hint = QLabel(
            self.tr(
                "Negative experiments are kept on purpose: knowing what "
                "does NOT work is real research."
            )
        )
        self.hint.setWordWrap(True)
        layout.addWidget(self.hint)

        self.refresh()

    # -- data ------------------------------------------------------------

    def set_manager(self, manager: ExperimentManager) -> None:
        """Point the dialog at another manager and reload the list."""
        self._manager = manager
        self.refresh()

    def refresh(self) -> None:
        """Rebuild the list from the manager (search-aware)."""
        selected = self.selected_id()
        self.list_widget.clear()
        records = self._manager.search(self.search_edit.text())
        for record in records:
            item = QListWidgetItem(
                f"[{record.status.value}] {record.experiment_id[:8]} — "
                f"{record.hypothesis[:60]}"
            )
            item.setData(Qt.ItemDataRole.UserRole, record.experiment_id)
            self.list_widget.addItem(item)
        if selected:
            self.select_experiment(selected)
        elif self.list_widget.count():
            self.list_widget.setCurrentRow(0)

    def selected_id(self) -> str | None:
        item = self.list_widget.currentItem()
        if item is None:
            return None
        return item.data(Qt.ItemDataRole.UserRole)

    def select_experiment(self, experiment_id: str) -> None:
        for row in range(self.list_widget.count()):
            item = self.list_widget.item(row)
            if item.data(Qt.ItemDataRole.UserRole) == experiment_id:
                self.list_widget.setCurrentRow(row)
                return

    def detail_text(self, experiment_id: str) -> str:
        record = self._manager.get(experiment_id)
        if record is None:
            return self.tr("Experiment not found.")
        return render_experiment(record)

    # -- actions ---------------------------------------------------------

    def select_experiments(self, experiment_ids: list[str]) -> None:
        """Select the given ids by their stable item data (tests/UI)."""
        wanted = set(experiment_ids)
        first = True
        for row in range(self.list_widget.count()):
            item = self.list_widget.item(row)
            if item.data(Qt.ItemDataRole.UserRole) in wanted:
                item.setSelected(True)
                if first:
                    self.list_widget.setCurrentRow(row)
                    first = False

    def compare_selected(self) -> str:
        ids = [
            item.data(Qt.ItemDataRole.UserRole)
            for item in self.list_widget.selectedItems()
        ]
        text = render_comparison(self._manager.compare(ids))
        self.detail.setPlainText(text)
        return text

    def create_entry(self, hypothesis: str, notes: str = "") -> ExperimentRecord:
        """Create a draft experiment from the notebook (chapter 52)."""
        record = self._manager.create(
            hypothesis=hypothesis,
            strategy_name="draft",
            strategy_version="0.0.0",
            dataset_version="unassigned",
            parameters={},
            notes=notes,
            status=ExperimentStatus.DRAFT,
        )
        self.refresh()
        self.select_experiment(record.experiment_id)
        return record

    def create_entry_interactive(self) -> ExperimentRecord | None:
        hypothesis, accepted = QInputDialog.getText(
            self, self.tr("New entry"), self.tr("Hypothesis:")
        )
        if not accepted or not hypothesis.strip():
            return None
        return self.create_entry(hypothesis.strip())

    def add_note(self, note: str) -> ExperimentRecord | None:
        experiment_id = self.selected_id()
        if experiment_id is None:
            return None
        record = self._manager.add_note(experiment_id, note)
        if record is not None:
            self.detail.setPlainText(render_experiment(record))
        return record

    def add_note_interactive(self) -> None:
        if self.selected_id() is None:
            QMessageBox.information(
                self, self.tr("Notebook"), self.tr("Select an experiment first.")
            )
            return
        note, accepted = QInputDialog.getMultiLineText(
            self, self.tr("Add note"), self.tr("Note:")
        )
        if accepted and note.strip():
            self.add_note(note.strip())

    def export_to(self, path: Path | str) -> Path:
        target = Path(path)
        target.write_text(self._manager.export(), encoding="utf-8")
        return target

    def export_interactive(self) -> None:
        from PyQt6.QtWidgets import QFileDialog

        path, _ = QFileDialog.getSaveFileName(
            self, self.tr("Export experiments"), "experiments.json",
            self.tr("JSON (*.json)"),
        )
        if path:
            self.export_to(path)

    def _on_selection(self, current: QListWidgetItem | None, _prev) -> None:
        if current is None:
            return
        self.detail.setPlainText(
            self.detail_text(current.data(Qt.ItemDataRole.UserRole))
        )

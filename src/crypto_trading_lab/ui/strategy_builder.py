"""Strategy Builder UI (ROADMAP.md chapter 34).

A block-based rule editor backed by the real
:class:`~crypto_trading_lab.strategy_builder.StrategyBuilder`: it builds
blocks, validates the rule, explains it in plain language, and
exports/imports a versioned JSON schema. No ``eval`` and no code
execution anywhere.

The editor deliberately does **not** claim that a diagram is a tradable
strategy: rules become executable strategies only once the engine
supports rule evaluation, which is tracked as pending work. Saying so
is part of the project's honesty rules.
"""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QApplication,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QGroupBox,
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

from crypto_trading_lab.rule_strategy import (
    RuleError,
    RuleStrategy,
    RuleStrategySpec,
    spec_from_blocks,
)
from crypto_trading_lab.strategy_builder import (
    STRATEGY_BUILDER_WARNING,
    StrategyBuilder,
    StrategyRule,
)


class StrategyBuilderDialog(QDialog):
    """Visual, block-based strategy rule editor (chapter 34)."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._builder = StrategyBuilder()
        self._block_ids: list[str] = []
        self._rule: StrategyRule | None = None

        self.setWindowTitle(self.tr("Strategy Builder"))
        self.resize(860, 680)
        self._setup_ui()

    # -- construction ----------------------------------------------------

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)

        header = QLabel(self.tr("Visual strategy builder"))
        font = header.font()
        font.setBold(True)
        font.setPointSize(15)
        header.setFont(font)
        layout.addWidget(header)

        identity = QGroupBox(self.tr("Rule identity"))
        identity_layout = QVBoxLayout(identity)
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText(self.tr("Rule name, e.g. EMA+RSI"))
        self.description_edit = QLineEdit()
        self.description_edit.setPlaceholderText(
            self.tr("When does this rule enter and exit?")
        )
        identity_layout.addWidget(QLabel(self.tr("Name:")))
        identity_layout.addWidget(self.name_edit)
        identity_layout.addWidget(QLabel(self.tr("Description:")))
        identity_layout.addWidget(self.description_edit)
        layout.addWidget(identity)

        palette = QGroupBox(self.tr("Block palette"))
        palette_layout = QHBoxLayout(palette)
        for label, handler in (
            (self.tr("Indicator"), self._add_indicator),
            (self.tr("Value"), self._add_value),
            (self.tr("Crossover"), lambda: self.add_block("crossover")),
            (self.tr("Crossunder"), lambda: self.add_block("crossunder")),
            (self.tr("AND"), lambda: self.add_block("and")),
            (self.tr("OR"), lambda: self.add_block("or")),
            (self.tr("Entry"), lambda: self.add_block("entry")),
            (self.tr("Exit"), lambda: self.add_block("exit")),
            (self.tr("Stop-loss"), self._add_stop_loss),
            (self.tr("Take-profit"), self._add_take_profit),
        ):
            button = QPushButton(label)
            button.clicked.connect(handler)
            palette_layout.addWidget(button)
        layout.addWidget(palette)

        self.blocks_view = QListWidget()
        layout.addWidget(self.blocks_view)

        actions = QHBoxLayout()
        self.validate_button = QPushButton(self.tr("Validate"))
        self.validate_button.clicked.connect(self.validate)
        self.explain_button = QPushButton(self.tr("Explain"))
        self.explain_button.clicked.connect(self.explain)
        self.executable_button = QPushButton(self.tr("Check executability"))
        self.executable_button.clicked.connect(self.explain_executability)
        self.remove_button = QPushButton(self.tr("Remove selected"))
        self.remove_button.clicked.connect(self.remove_selected)
        self.export_button = QPushButton(self.tr("Export…"))
        self.export_button.clicked.connect(self._export_interactive)
        self.import_button = QPushButton(self.tr("Import…"))
        self.import_button.clicked.connect(self._import_interactive)
        for button in (
            self.validate_button,
            self.explain_button,
            self.executable_button,
            self.remove_button,
            self.export_button,
            self.import_button,
        ):
            actions.addWidget(button)
        layout.addLayout(actions)

        self.feedback = QTextBrowser()
        self.feedback.setPlainText(self.tr(STRATEGY_BUILDER_WARNING))
        layout.addWidget(self.feedback)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)
        buttons.accepted.connect(self.accept)
        layout.addWidget(buttons)

    # -- block editing ---------------------------------------------------

    def add_block(self, kind: str, **params) -> str | None:
        """Add a palette block; returns its block id (None if invalid)."""
        if kind == "indicator":
            block = self._builder.add_indicator(
                params.get("indicator_type", "ema"),
                params.get("params", {"period": 20}),
            )
        elif kind == "value":
            block = self._builder.add_value(params.get("value", 0))
        elif kind == "crossover":
            block = self._builder.add_operator("crossover")
        elif kind == "crossunder":
            block = self._builder.add_operator("crossunder")
        elif kind in {"and", "or", "not"}:
            block = self._builder.add_condition(kind)
        elif kind == "entry":
            block = self._builder.add_entry_signal()
        elif kind == "exit":
            block = self._builder.add_exit_signal()
        elif kind == "stop_loss":
            block = self._builder.add_stop_loss(params.get("value", 0.05))
        elif kind == "take_profit":
            block = self._builder.add_take_profit(params.get("value", 0.10))
        elif kind == "volatility_filter":
            block = self._builder.add_volatility_filter(
                params.get("threshold", 0.02)
            )
        elif kind == "cooldown":
            block = self._builder.add_cooldown(params.get("periods", 5))
        else:
            raise ValueError(f"unknown block kind {kind!r}")

        self._block_ids.append(block.block_id)
        item = QListWidgetItem(block.label)
        item.setData(Qt.ItemDataRole.UserRole, block.block_id)
        self.blocks_view.addItem(item)
        self._rule = None  # invalidate the cached rule
        return block.block_id

    def _add_indicator(self) -> None:
        options = ("sma", "ema", "rsi", "atr", "roc")
        indicator_type, accepted = QInputDialog.getItem(
            self, self.tr("Indicator"), self.tr("Indicator type:"),
            list(options), 0, False,
        )
        if not accepted:
            return
        period, accepted = QInputDialog.getInt(
            self, self.tr("Indicator"), self.tr("Period:"), 20, 2, 500
        )
        if not accepted:
            return
        self.add_block(
            "indicator",
            indicator_type=indicator_type,
            params={"period": period},
        )

    def _add_value(self) -> None:
        value, accepted = QInputDialog.getDouble(
            self, self.tr("Value"), self.tr("Value:"), 0.0, -1e9, 1e9, 4
        )
        if accepted:
            self.add_block("value", value=value)

    def _add_stop_loss(self) -> None:
        value, accepted = QInputDialog.getDouble(
            self, self.tr("Stop-loss"), self.tr("Fraction of price:"),
            0.05, 0.0, 1.0, 4,
        )
        if accepted:
            self.add_block("stop_loss", value=value)

    def _add_take_profit(self) -> None:
        value, accepted = QInputDialog.getDouble(
            self, self.tr("Take-profit"), self.tr("Fraction of price:"),
            0.10, 0.0, 5.0, 4,
        )
        if accepted:
            self.add_block("take_profit", value=value)

    def remove_selected(self) -> None:
        item = self.blocks_view.currentItem()
        if item is None:
            return
        block_id = item.data(Qt.ItemDataRole.UserRole)
        self._block_ids = [b for b in self._block_ids if b != block_id]
        self.blocks_view.takeItem(self.blocks_view.row(item))
        self._rule = None

    # -- rule operations -------------------------------------------------

    def build_rule(self) -> StrategyRule:
        """Create (or return the cached) rule from the current blocks."""
        if self._rule is None:
            self._rule = self._builder.create_rule(
                name=self.name_edit.text().strip() or self.tr("Untitled rule"),
                description=self.description_edit.text().strip(),
                block_ids=list(self._block_ids),
            )
        return self._rule

    def validate(self) -> list[str]:
        """Validate the rule and show the warnings; returns them."""
        rule = self.build_rule()
        warnings = self._builder.validate_rule(rule)
        warnings += self._builder.warn_overfitting(rule)
        if not self._block_ids:
            warnings.append(
                self.tr("The rule is empty: add at least one condition.")
            )
        has_entry = any(
            (block := self._builder.get_block(b)) is not None
            and block.type == "entry"
            for b in self._block_ids
        )
        has_exit = any(
            (block := self._builder.get_block(b)) is not None
            and block.type == "exit"
            for b in self._block_ids
        )
        if self._block_ids and not (has_entry and has_exit):
            warnings.append(
                self.tr(
                    "A tradable rule needs both an entry and an exit "
                    "signal. Until they exist, the rule is incomplete."
                )
            )
        text = "\n".join(f"- {w}" for w in warnings) if warnings else self.tr(
            "No problems found in the rule structure."
        )
        self.feedback.setPlainText(text)
        return warnings

    def explain(self) -> str:
        """Plain-language explanation of the current rule."""
        rule = self.build_rule()
        text = self._builder.explain_rule(rule)
        overfitting = self._builder.warn_overfitting(rule)
        if overfitting:
            text += "\n\n" + self.tr("Possible overfitting:") + "\n"
            text += "\n".join(f"- {w}" for w in overfitting)
        text += "\n\n" + self.tr(
            "This is a description of the rule, not evidence that it "
            "works. Test it and try to refute it."
        )
        self.feedback.setPlainText(text)
        return text

    def export_rule_text(self) -> str:
        """Versioned JSON of the current rule."""
        return self._builder.export_rule(self.build_rule())

    # -- executable rule (chapters 33, 77) -------------------------------

    def to_rule_spec(self) -> RuleStrategySpec:
        """Convert the current blocks into an executable rule.

        Raises :class:`RuleError` with a plain reason when the rule uses
        something the engine cannot execute yet.
        """
        rule = self.build_rule()
        return spec_from_blocks(rule.name, rule.blocks, version=rule.version)

    def to_rule_strategy(self) -> RuleStrategy:
        """An engine-ready strategy for the current rule."""
        return RuleStrategy(self.to_rule_spec())

    def explain_executability(self) -> tuple[bool, str]:
        """Report whether the current rule can run in the engine."""
        try:
            spec = self.to_rule_spec()
        except RuleError as error:
            message = self.tr(
                "This rule cannot run in the engine yet: {reason}"
            ).format(reason=error)
            self.feedback.setPlainText(message)
            return False, message
        message = self.tr(
            "Executable rule ready: {description}\n\n"
            "The engine will fill signals at the next candle's open. "
            "Stop-loss and take-profit are evaluated on candle closes, "
            "not intrabar."
        ).format(description=spec.describe())
        self.feedback.setPlainText(message)
        return True, message

    def import_rule_text(self, data: str) -> StrategyRule | None:
        """Import a rule from versioned JSON; rebuilds the block list."""
        rule = self._builder.import_rule(data)
        if rule is None:
            self.feedback.setPlainText(
                self.tr("The file is not a valid strategy rule.")
            )
            return None
        self.name_edit.setText(rule.name)
        self.description_edit.setText(rule.description)
        self.blocks_view.clear()
        self._block_ids = []
        for block in rule.blocks:
            self._block_ids.append(block.block_id)
            item = QListWidgetItem(block.label)
            item.setData(Qt.ItemDataRole.UserRole, block.block_id)
            self.blocks_view.addItem(item)
        self._rule = rule
        self.feedback.setPlainText(
            self.tr("Imported rule “{name}” (version {version}).").format(
                name=rule.name, version=rule.version
            )
        )
        return rule

    def _export_interactive(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self, self.tr("Export rule"), "strategy_rule.json",
            self.tr("JSON (*.json)"),
        )
        if not path:
            return
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(self.export_rule_text())

    def _import_interactive(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, self.tr("Import rule"), "", self.tr("JSON (*.json)")
        )
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as handle:
                self.import_rule_text(handle.read())
        except OSError as error:
            QMessageBox.warning(
                self, self.tr("Import rule"),
                self.tr("Could not read the file: {error}").format(error=error),
            )


def show_strategy_builder() -> None:
    """Launch the strategy builder dialog."""
    import sys

    QApplication.instance() or QApplication(sys.argv)
    dialog = StrategyBuilderDialog()
    dialog.exec()


__all__ = ["StrategyBuilderDialog", "show_strategy_builder"]

"""Research assistant UI (chapter 55).

Honest by construction: with no generative model configured, this is a
*local, deterministic* research assistant — it classifies the question,
answers from the project's own methodology, and says plainly that it is
not an LLM. A real model can be plugged in through the ``backend``
argument without changing the UI, and the chapter-55 restrictions still
apply (research only, never orders, always independently validated).

Conversations are persisted through :class:`AIAssistant`, so the
assistant has a real record instead of throwaway text.
"""

from __future__ import annotations

from typing import Any, Callable

from PyQt6.QtCore import QCoreApplication, Qt
from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QLabel,
    QMessageBox,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from crypto_trading_lab.ai_assistant import (
    AI_ASSISTANT_WARNING,
    AIAssistant,
    AssistantRole,
)

__all__ = [
    "LOCAL_BACKEND_NOTICE",
    "ResearchAssistant",
    "ResearchAssistantDialog",
    "CONTEXTS",
]

_CONTEXT = "ResearchAssistant"

#: UI contexts → assistant role. Order defines the combo order.
CONTEXTS: dict[str, AssistantRole] = {
    "Strategy development": AssistantRole.HYPOTHESIS_GENERATOR,
    "Data analysis": AssistantRole.DATA_ANALYST,
    "Performance evaluation": AssistantRole.STRATEGY_CRITIC,
    "Risk assessment": AssistantRole.STRATEGY_CRITIC,
    "Code review": AssistantRole.CODE_REVIEWER,
    "Documentation": AssistantRole.DOCUMENTATION,
}

LOCAL_BACKEND_NOTICE = (
    "This is the built-in, offline research assistant. It does not use "
    "a generative language model: it classifies your question and "
    "answers from the laboratory's own methodology and your recorded "
    "experiments. Treat every suggestion as a checklist to verify "
    "yourself, never as financial advice."
)


def _t(text: str) -> str:
    return QCoreApplication.translate(_CONTEXT, text)


#: Keyword → extra concrete checks the answer adds.
_TOPIC_CHECKS: tuple[tuple[tuple[str, ...], tuple[str, ...]], ...] = (
    (
        ("overfit", "overfitting", "curve fit", "too good"),
        (
            "Count how many configurations you tried; the best of many "
            "is often luck (multiple testing).",
            "Check the walk-forward analysis, not just the in-sample run.",
            "Make small parameter changes: if the result collapses, it "
            "was fitted to noise.",
        ),
    ),
    (
        ("data", "csv", "download", "dataset", "missing", "duplicate"),
        (
            "Download a versioned dataset so the run can be reproduced.",
            "Check the quality report: missing candles, duplicates and "
            "invalid rows must be zero to call the data ready.",
            "Remember the checksum: re-downloading may return different "
            "data later.",
        ),
    ),
    (
        ("risk", "drawdown", "ruin", "survive", "loss"),
        (
            "Protect living money first: never risk funds you need.",
            "Look at the maximum drawdown, not only the final return.",
            "Estimate the risk of ruin from the Monte Carlo report.",
        ),
    ),
    (
        ("strategy", "signal", "entry", "exit", "rule", "indicator"),
        (
            "State the hypothesis before looking at results.",
            "Keep the rule count low; simpler strategies are preferred "
            "when the evidence is comparable.",
            "Signals are decided at a candle's close and filled at the "
            "next open — never assume a same-candle fill.",
        ),
    ),
    (
        ("benchmark", "compare", "buy and hold", "beat"),
        (
            "Compare against buy and hold after costs, not before.",
            "A strategy that cannot beat the passive alternative added "
            "nothing.",
        ),
    ),
    (
        ("ai", "you", "model", "chatgpt", "llm"),
        (
            "I am a local rule-based assistant, not a language model.",
            "I cannot see the future and I cannot validate a strategy "
            "for you; run the validation steps and read their output.",
        ),
    ),
)

_BASE_STEPS: tuple[str, ...] = (
    "Write the hypothesis as a falsifiable sentence.",
    "Name the dataset (exchange, market, timeframe, period) and its checksum.",
    "Choose the costs (fee, spread, slippage) before running anything.",
    "Run the backtest, then compare it with buy and hold.",
    "Try to destroy the result: out-of-sample, walk-forward, Monte Carlo, "
    "cost and parameter changes.",
    "Qualify only what survived; record the experiment even if it failed.",
)


class ResearchAssistant:
    """Deterministic research assistant with an optional model backend."""

    def __init__(
        self,
        manager: Any | None = None,
        backend: Callable[[str, str], str] | None = None,
    ) -> None:
        self._manager = manager
        self._backend = backend

    @property
    def has_model_backend(self) -> bool:
        return self._backend is not None

    def answer(self, question: str, context: str) -> str:
        """Answer a research question with methodology, not predictions."""
        question = question.strip()
        if not question:
            return _t("Ask a concrete research question.")
        if self._backend is not None:
            return self._backend(question, context)

        lowered = question.lower()
        lines = [
            _t("Question: {q}").format(q=question),
            "",
            _t("Context: {c}").format(c=context),
            "",
            _t(LOCAL_BACKEND_NOTICE),
            "",
            _t("A disciplined path for this question:"),
        ]
        lines.extend(f"  {i}. {step}" for i, step in enumerate(_BASE_STEPS, 1))

        for keywords, checks in _TOPIC_CHECKS:
            if any(word in lowered for word in keywords):
                lines.append("")
                lines.append(_t("Specifically for what you asked:"))
                lines.extend(f"  - {check}" for check in checks)

        if self._manager is not None:
            experiments = self._manager.list_experiments()
            lines.append("")
            if experiments:
                lines.append(
                    _t(
                        "Your notebook already holds {n} experiment(s); "
                        "the most recent is “{h}”."
                    ).format(n=len(experiments), h=experiments[0].hypothesis[:80])
                )
            else:
                lines.append(
                    _t(
                        "Your notebook is empty: record the hypothesis "
                        "before you run anything."
                    )
                )
        lines.append("")
        lines.append(_t(AI_ASSISTANT_WARNING))
        return "\n".join(lines)


class ResearchAssistantDialog(QDialog):
    """Interactive research assistant dialog (chapter 55)."""

    def __init__(
        self,
        manager: Any | None = None,
        assistant: AIAssistant | None = None,
        backend: Callable[[str, str], str] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._engine = ResearchAssistant(manager=manager, backend=backend)
        self._store = assistant
        self._conversation_id: str | None = None
        self.setWindowTitle(self.tr("Research Assistant"))
        self.resize(760, 620)
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)

        notice = QLabel(
            self.tr(
                "Offline research assistant: a methodology checklist, "
                "not a prediction machine and not financial advice."
            )
        )
        notice.setWordWrap(True)
        notice.setAlignment(Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(notice)

        layout.addWidget(QLabel(self.tr("Research context:")))
        self.context_combo = QComboBox()
        for context in CONTEXTS:
            self.context_combo.addItem(self.tr(context), context)
        layout.addWidget(self.context_combo)

        layout.addWidget(QLabel(self.tr("Ask your research question:")))
        self.question_field = QTextEdit()
        self.question_field.setMaximumHeight(90)
        self.question_field.setPlaceholderText(
            self.tr("Describe your research question or task…")
        )
        layout.addWidget(self.question_field)

        layout.addWidget(QLabel(self.tr("Assistant response:")))
        self.response_field = QTextEdit()
        self.response_field.setReadOnly(True)
        layout.addWidget(self.response_field)

        buttons = QDialogButtonBox()
        self.ask_button = buttons.addButton(
            self.tr("Ask"), QDialogButtonBox.ButtonRole.AcceptRole
        )
        self.close_button = buttons.addButton(
            self.tr("Close"), QDialogButtonBox.ButtonRole.RejectRole
        )
        self.ask_button.clicked.connect(self.ask)
        self.close_button.clicked.connect(self.reject)
        layout.addWidget(buttons)

    def ask(self) -> str:
        """Produce (and persist) an answer; returns the response text."""
        question = self.question_field.toPlainText().strip()
        context = self.context_combo.currentData() or self.context_combo.currentText()
        try:
            response = self._engine.answer(question, context)
        except Exception as error:  # pragma: no cover - defensive UI guard
            QMessageBox.warning(
                self, self.tr("Error"),
                self.tr("Could not produce an answer: {error}").format(
                    error=error
                ),
            )
            return ""
        self.response_field.setPlainText(response)
        self._persist(question, context, response)
        return response

    def _persist(self, question: str, context: str, response: str) -> None:
        if self._store is None or not question:
            return
        if self._conversation_id is None:
            role = CONTEXTS.get(context, AssistantRole.HYPOTHESIS_GENERATOR)
            conversation = self._store.create_conversation(role)
            self._conversation_id = conversation.conversation_id
        self._store.add_message(self._conversation_id, "user", question)
        self._store.add_message(self._conversation_id, "assistant", response)

    @property
    def conversation_id(self) -> str | None:
        return self._conversation_id


def research_assistant(
    assistant: AIAssistant | None = None,
    manager: Any | None = None,
    backend: Callable[[str, str], str] | None = None,
) -> str | None:
    """Open the assistant dialog and return the last answer (or None)."""
    dialog = ResearchAssistantDialog(
        manager=manager, assistant=assistant, backend=backend
    )
    dialog.exec()
    return dialog.response_field.toPlainText() or None

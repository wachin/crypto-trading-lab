"""AI research assistant UI (Chapter 55).

Provides an interactive interface for the AI research assistant.
"""

from __future__ import annotations

from typing import Optional

from PyQt6.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)
from PyQt6.QtCore import Qt


class ResearchAssistantDialog(QDialog):
    """Interactive AI research assistant dialog."""

    def __init__(self, parent: QWidget = None):
        super().__init__(parent)
        self.setWindowTitle("AI Research Assistant")
        self.resize(700, 500)

        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout()

        # Context selector
        context_group = QWidget()
        context_layout = QHBoxLayout()
        context_label = QLabel("Research Context:")
        self.context_combo = QComboBox()
        self.context_combo.addItems([
            "Strategy Development",
            "Data Analysis",
            "Performance Evaluation",
            "Risk Assessment",
            "Portfolio Optimization",
        ])
        context_layout.addWidget(context_label)
        context_layout.addWidget(self.context_combo)
        context_layout.addStretch()
        context_group.setLayout(context_layout)
        layout.addWidget(context_group)

        # Question area
        question_group = QWidget()
        question_layout = QVBoxLayout()
        question_label = QLabel("Ask your research question:")
        question_label.setStyleSheet("font-weight: bold;")
        question_layout.addWidget(question_label)
        self.question_field = QTextEdit()
        self.question_field.setMaximumHeight(80)
        self.question_field.setPlaceholderText("Describe your research question or task...")
        question_layout.addWidget(self.question_field)
        question_group.setLayout(question_layout)
        layout.addWidget(question_group)

        # Response area
        response_group = QWidget()
        response_layout = QVBoxLayout()
        response_label = QLabel("AI Response:")
        response_label.setStyleSheet("font-weight: bold;")
        response_layout.addWidget(response_label)
        self.response_field = QTextEdit()
        self.response_field.setReadOnly(True)
        self.response_field.setPlaceholderText("AI response will appear here...")
        response_layout.addWidget(self.response_field)
        response_group.setLayout(response_layout)
        layout.addWidget(response_group)

        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.setLayout(layout)

    def get_response(self, assistant: Any) -> Optional[str]:
        """Get the AI response for the current question."""
        question = self.question_field.toPlainText().strip()
        if not question:
            return None

        try:
            response = assistant.analyze(
                question=question,
                context=self.context_combo.currentText(),
            )
            self.response_field.setPlainText(response)
            return response
        except Exception as e:
            QMessageBox.warning(
                self,
                "Error",
                f"Failed to get AI response: {str(e)}"
            )
            return None


def research_assistant(assistant: Any) -> Optional[str]:
    """Launch research assistant and get response."""
    import sys
    app = QApplication.instance() or QApplication(sys.argv)
    dialog = ResearchAssistantDialog()
    if dialog.exec():
        question = dialog.question_field.toPlainText().strip()
        if question:
            # Provide helpful guidance based on context
            context = dialog.context_combo.currentText()
            response = get_guidance(question, context)
            dialog.response_field.setPlainText(response)
            return response
    return None


def get_guidance(question: str, context: str) -> str:
    """Provide guidance based on question and context."""
    responses = {
        "Strategy Development": (
            "To develop a strategy:\n"
            "1. Define a clear hypothesis\n"
            "2. Use the Strategy Builder to construct rules\n"
            "3. Test with backtesting\n"
            "4. Validate with out-of-sample data\n"
            "5. Check complexity and overfitting"
        ),
        "Data Analysis": (
            "For data analysis:\n"
            "1. Import clean CSV data\n"
            "2. Check data quality\n"
            "3. Use indicators to extract features\n"
            "4. Split data properly (train/test)"
        ),
        "Performance Evaluation": (
            "Evaluate performance with:\n"
            "- Net profit and total return\n"
            "- Sharpe ratio (risk-adjusted return)\n"
            "- Maximum drawdown\n"
            "- Profit factor\n"
            "Compare against benchmarks"
        ),
        "Risk Assessment": (
            "Assess risk by:\n"
            "- Checking max drawdown\n"
            "- Calculating risk of ruin\n"
            "- Testing under different market conditions\n"
            "- Ensuring capital protection rules"
        ),
        "Portfolio Optimization": (
            "For portfolio optimization:\n"
            "- Use correlation analysis\n"
            "- Apply position sizing\n"
            "- Consider multiple assets\n"
            "- Check portfolio metrics"
        ),
    }
    
    return responses.get(context, 
        "Use the Learning Center for step-by-step guidance.\n"
        "Research tools help you:\n"
        "- Document experiments in the Notebook\n"
        "- Build strategies visually\n"
        "- Analyze complexity and benchmarks\n"
        "- Test with backtesting"
    )
    """Launch research assistant and get response."""
    import sys
    app = QApplication.instance() or QApplication(sys.argv)
    dialog = ResearchAssistantDialog()
    if dialog.exec():
        return dialog.get_response(assistant)
    return None


__all__ = [
    "ResearchAssistantDialog",
    "research_assistant",
]

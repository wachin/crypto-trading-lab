"""Learning Center screen (ROADMAP.md chapter 23, task 26).

A placeholder shell that already satisfies the structural requirements:
the 20-lesson learning path is listed, content is bundled (offline by
default), lessons can be marked completed, and the welcome guide is
reachable. Rich content, quizzes, and progress persistence arrive with
later phases.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

__all__ = ["LESSONS", "Lesson", "LearningCenterWidget"]

#: Bundled markdown directory — offline by design (chapter 23).
BEGINNERS_DIR = Path(__file__).resolve().parents[4] / "docs" / "en" / "beginners"


@dataclass(frozen=True)
class Lesson:
    number: int
    title: str


#: The chapter 23 learning path.
LESSONS: tuple[Lesson, ...] = (
    Lesson(1, "What is cryptocurrency?"),
    Lesson(2, "What is a market?"),
    Lesson(3, "What is a trading pair?"),
    Lesson(4, "What is a candlestick?"),
    Lesson(5, "What is volume?"),
    Lesson(6, "What is a market order?"),
    Lesson(7, "What is a limit order?"),
    Lesson(8, "What are fees?"),
    Lesson(9, "What is risk?"),
    Lesson(10, "What is paper trading?"),
    Lesson(11, "What is backtesting?"),
    Lesson(12, "Build your first simple strategy."),
    Lesson(13, "Run your first backtest."),
    Lesson(14, "Understand a loss."),
    Lesson(15, "Understand drawdown."),
    Lesson(16, "Learn why profits are never guaranteed."),
    Lesson(17, "Why most traders lose money."),
    Lesson(18, "Trading is not a reliable income."),
    Lesson(19, "When not to trade."),
    Lesson(20, "Protecting the money you need for living."),
)


class LearningCenterWidget(QWidget):
    """Placeholder Learning Center: lesson list + completed tracking."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._completed: set[int] = set()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)

        title = QLabel(self.tr("Learning Center"))
        font = title.font()
        font.setPointSize(16)
        font.setBold(True)
        title.setFont(font)
        layout.addWidget(title)

        intro = QLabel(
            self.tr(
                "Learn step by step, from zero. Everything here works "
                "offline and never risks money."
            )
        )
        intro.setWordWrap(True)
        layout.addWidget(intro)

        self.lesson_list = QListWidget()
        for lesson in LESSONS:
            item = QListWidgetItem(f"{lesson.number}. {lesson.title}")
            item.setData(Qt.ItemDataRole.UserRole, lesson.number)
            self.lesson_list.addItem(item)
        layout.addWidget(self.lesson_list)

        self.status_label = QLabel(self.tr("0 of 20 lessons completed"))
        layout.addWidget(self.status_label)

        self.start_button = QPushButton(self.tr("Start Here: Cryptocurrency for Complete Beginners."))
        layout.addWidget(self.start_button)

    def mark_completed(self, number: int) -> None:
        """Mark lesson ``number`` as completed and update the list view."""
        if not any(lesson.number == number for lesson in LESSONS):
            raise ValueError(f"Unknown lesson number: {number}")
        self._completed.add(number)
        for row in range(self.lesson_list.count()):
            item = self.lesson_list.item(row)
            lesson_number = item.data(Qt.ItemDataRole.UserRole)
            if lesson_number == number:
                text = item.text()
                if not text.startswith("[x]"):
                    item.setText(f"[x] {text}")
        self.status_label.setText(
            self.tr("{} of {} lessons completed").format(
                len(self._completed), len(LESSONS)
            )
        )

    def completed_lessons(self) -> set[int]:
        return set(self._completed)

    @staticmethod
    def guide_path() -> Path:
        """Bundled beginner guide (offline content, chapter 23)."""
        return BEGINNERS_DIR / "00-start-here.md"

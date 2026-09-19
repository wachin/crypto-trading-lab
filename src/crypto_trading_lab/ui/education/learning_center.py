"""Learning Center screen (ROADMAP.md chapter 23, task 26).

A placeholder shell that already satisfies the structural requirements:
the 20-lesson learning path is listed, content is bundled (offline by
default), lessons can be marked completed, and the welcome guide is
reachable. Rich content, quizzes, and progress persistence arrive with
later phases.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QGroupBox,
    QLayout,
    QRadioButton,
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

#: Quiz questions for each lesson (chapter 73).
QUIZ_QUESTIONS: dict[int, dict] = {
    1: {"question": "What is cryptocurrency?", "options": ["Digital money secured by cryptography", "A type of stock", "A physical coin"], "answer": 0},
    2: {"question": "What is a market?", "options": ["A place to buy and sell", "A type of bank", "A crypto wallet"], "answer": 0},
    3: {"question": "What is a trading pair?", "options": ["Two currencies traded against each other", "A pair of dice", "A trading strategy"], "answer": 0},
    4: {"question": "What is a candlestick?", "options": ["A price chart showing open, high, low, close", "A type of candle", "A trading signal"], "answer": 0},
    5: {"question": "What is volume?", "options": ["The number of shares/contracts traded", "The price change", "The market cap"], "answer": 0},
    6: {"question": "What is a market order?", "options": ["Buys/sells at current price", "Sets a price target", "Waits for a specific time"], "answer": 0},
    7: {"question": "What is a limit order?", "options": ["Buys/sells at a specific price or better", "Sets a time limit", "Uses market price"], "answer": 0},
    8: {"question": "What are fees?", "options": ["Costs for trading", "Taxes on profits", "Broker commissions"], "answer": 0},
    9: {"question": "What is risk?", "options": ["The chance of losing money", "The chance of making profit", "The market volatility"], "answer": 0},
    10: {"question": "What is paper trading?", "options": ["Trading with virtual money", "Trading on paper", "Trading without fees"], "answer": 0},
    11: {"question": "What is backtesting?", "options": ["Testing a strategy on historical data", "Backing up trades", "Testing internet connection"], "answer": 0},
    12: {"question": "Build your first simple strategy?", "options": ["Moving average crossover", "Buy and hold", "Day trading"], "answer": 0},
    13: {"question": "Run your first backtest?", "options": ["Using the Backtesting Lab", "Manual calculation", "Guessing prices"], "answer": 0},
    14: {"question": "Understand a loss?", "options": ["Losing money is bad", "Losses are part of trading", "Avoid trading entirely"], "answer": 1},
    15: {"question": "Understand drawdown?", "options": ["Peak-to-trough decline", "A type of profit", "A trading strategy"], "answer": 0},
    16: {"question": "Learn why profits are never guaranteed?", "options": ["Trading involves risk", "Always win", "Market is predictable"], "answer": 0},
    17: {"question": "Why most traders lose money?", "options": ["Lack of education", "Bad luck", "Market manipulation"], "answer": 0},
    18: {"question": "Trading is not a reliable income?", "options": ["True - high risk", "False - easy money", "Depends on capital"], "answer": 0},
    19: {"question": "When not to trade?", "options": ["When unsure", "When winning", "Never"], "answer": 0},
    20: {"question": "Protecting the money you need for living?", "options": ["Never borrow to trade", "Always borrow", "Only trade profits"], "answer": 0},
}


class LearningCenterWidget(QWidget):
    """Placeholder Learning Center: lesson list + completed tracking."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._completed: set[int] = set()
        self._quiz_scores: dict[int, bool] = {}

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

        self.status_label = QLabel(
            self.tr("0 of 20 lessons completed - 0 quizzes taken")
        )
        self.status_label.setText(
            self.tr("0 of 20 lessons completed")
        )  # will be updated later
        layout.addWidget(self.status_label)
        layout.addWidget(self.status_label)

        self.start_button = QPushButton(self.tr("Start Here: Cryptocurrency for Complete Beginners."))
        self.start_button.clicked.connect(self._show_first_lesson)
        layout.addWidget(self.start_button)

        self.lesson_list.itemClicked.connect(self._show_lesson_details)

    def _show_lesson_details(self, item):
        """Show details when a lesson is clicked."""
        lesson_number = item.data(Qt.ItemDataRole.UserRole)
        from PyQt6.QtWidgets import QMessageBox, QDialog, QVBoxLayout, QLabel, QPushButton, QGroupBox
        
        # Get the lesson info
        lesson = None
        for l in LESSONS:
            if l.number == lesson_number:
                lesson = l
                break
        
        if lesson:
            dialog = QDialog(self)
            dialog.setWindowTitle(f"Lesson {lesson.number}: {lesson.title}")
            dialog.setFixedSize(600, 400)
            layout = QVBoxLayout(dialog)
            
            # Title
            title = QLabel(f"Lesson {lesson.number}: {lesson.title}")
            title.setStyleSheet("font-size: 14px; font-weight: bold;")
            title.setAlignment(Qt.AlignCenter)
            layout.addWidget(title)
            
            # Description placeholder
            desc = QLabel(
                "Esta lección está en construcción. "
                "Mira el README para aprender los conceptos: "
                "https://github.com/wachin/crypto-trading-lab"
            )
            desc.setWordWrap(True)
            desc.setAlignment(Qt.AlignCenter)
            layout.addWidget(desc)
            
            # Quiz button
            quiz_btn = QPushButton("Tomar Quiz")
            quiz_btn.clicked.connect(lambda: self._take_quiz(lesson_number))
            layout.addWidget(quiz_btn)
            
            # Close button
            close_btn = QPushButton("Cerrar")
            close_btn.clicked.connect(dialog.close)
            layout.addWidget(close_btn)
            
            dialog.exec()
    
    def _show_first_lesson(self):
        """Show the first lesson."""
        for row in range(self.lesson_list.count()):
            item = self.lesson_list.item(row)
            self.lesson_list.setCurrentItem(item)
            self._show_lesson_details(item)
            break

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
        self._save_persistence()

    def take_quiz(self, lesson_number: int) -> bool:
        """Take a quiz for the specified lesson number.
        
        Returns True if the answer is correct, False otherwise.
        """
        from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton, QButtonGroup, QGroupBox, QHBoxBoxLayout
        from PyQt6.QtCore import Qt
        
        # Get the quiz question for this lesson
        question_data = QUIZ_QUESTIONS.get(lesson_number)
        if question_data is None:
            return False
        
        question = question_data["question"]
        options = question_data["options"]
        correct_answer = question_data["answer"]
        
        # Create quiz dialog
        dialog = QDialog(self)
        dialog.setWindowTitle(self.tr("Quiz - Lesson {}").format(lesson_number))
        dialog.setFixedSize(400, 300)
        
        layout = QVBoxLayout(dialog)
        
        # Question label
        question_label = QLabel(self.tr(question))
        question_label.setWordWrap(True)
        question_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        font = question_label.font()
        font.setPointSize(12)
        question_label.setFont(font)
        layout.addWidget(question_label)
        
        # Options group box
        group_box = QGroupBox()
        group_layout = QVBoxLayout(group_box)
        
        button_group = QButtonGroup(dialog)
        
        for i, option in enumerate(options):
            radio = QPushButton(self.tr(option))
            radio.setCheckable(True)
            radio.setProperty("answer_index", i)
            button_group.addButton(radio)
            group_layout.addWidget(radio)
        
        layout.addWidget(group_box)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        submit_btn = QPushButton(self.tr("Submit"))
        submit_btn.clicked.connect(lambda: self._check_quiz_answer(dialog, button_group, correct_answer, dialog))
        button_layout.addWidget(submit_btn)
        
        cancel_btn = QPushButton(self.tr("Cancel"))
        cancel_btn.clicked.connect(dialog.reject)
        button_layout.addWidget(cancel_btn)
        
        layout.addLayout(button_layout)
        
        dialog.exec()
        
        # Return result - this is simplified; in a full implementation
        # we'd track the result differently
        return False

    def _check_quiz_answer(self, dialog, button_group, correct_answer, dialog_ref):
        """Check the quiz answer and provide feedback."""
        selected_id = button_group.checkedId()
        
        if selected_id >= 0:
            # Get the text of the selected button
            selected_button = button_group.button(selected_id)
            selected_text = selected_button.text()
            
            if selected_id == correct_answer:
                # Correct answer
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.information(
                    dialog,
                    self.tr("Correct!"),
                    self.tr("That is the correct answer!")
                )
            else:
                # Wrong answer
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.warning(
                    dialog,
                    self.tr("Incorrect"),
                    self.tr("The correct answer was option {}").format(correct_answer + 1)
                )
        
        dialog.accept()


    def completed_lessons(self) -> set[int]:
        return set(self._completed)

    #: Persistence file for quiz and lesson progress (chapter 75)
    PERSISTENCE_FILE = Path(__file__).resolve().parents[3] / "data" / "learning_center_progress.json"

    def _load_persistence(self) -> None:
        """Load persisted progress from disk."""
        if self.PERSISTENCE_FILE.exists():
            try:
                with open(self.PERSISTENCE_FILE, 'r', encoding='utf-8') as f:
                    progress = json.load(f)
                self._completed.update(progress.get("completed_lessons", []))
            except (json.JSONDecodeError, KeyError, TypeError):
                pass

    def _save_persistence(self) -> None:
        """Save completed lessons and quiz scores to disk."""
        self.PERSISTENCE_FILE.parent.mkdir(parents=True, exist_ok=True)
        progress_data = {
            "completed_lessons": sorted(list(self._completed)),
            "quiz_scores": self._quiz_scores,
        }
        with open(self.PERSISTENCE_FILE, 'w', encoding='utf-8') as f:
            json.dump(progress_data, f, indent=2)

    @staticmethod
    def guide_path() -> Path:
        """Bundled beginner guide (offline content, chapter 23)."""
        return BEGINNERS_DIR / "00-start-here.md"

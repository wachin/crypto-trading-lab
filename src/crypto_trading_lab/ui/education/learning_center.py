"""Learning Center screen (ROADMAP.md chapters 23 and 80).

Three levels of offline lessons with a working quiz, completion
tracking, bookmarks and "continue where you left off". Content lives in
:mod:`crypto_trading_lab.education.curriculum`; the interface chrome is
translated with ``self.tr()`` and progress is stored under the user's
XDG data directory (injectable for tests).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QButtonGroup,
    QComboBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from crypto_trading_lab.configuration.xdg import AppPaths
from crypto_trading_lab.education.curriculum import (
    CURRICULUM,
    LEVEL_NAMES,
    LEVELS,
    get_lesson,
    lessons_for_level,
    total_lessons,
)

__all__ = ["LESSONS", "Lesson", "LearningCenterWidget"]

#: Bundled markdown directory — offline by design (chapter 23).
BEGINNERS_DIR = Path(__file__).resolve().parents[4] / "docs" / "en" / "beginners"


#: Lesson-to-screen mapping (chapter 80).
#: Maps lesson number -> (screen_name, action_callback_name)
LESSON_SCREEN_MAP: dict[int, tuple[str, str]] = {
    # Level 1 - Basics
    8: ("historical_data", "_open_historical_data"),    # What is an exchange
    9: ("historical_data", "_open_historical_data"),    # Centralized vs decentralized exchanges
    10: ("historical_data", "_open_historical_data"),   # Spot markets
    11: ("historical_data", "_open_historical_data"),   # Trading pairs
    13: ("historical_data", "_open_historical_data"),   # Order books
    14: ("historical_data", "_open_historical_data"),   # Market orders
    15: ("historical_data", "_open_historical_data"),   # Limit orders
    16: ("historical_data", "_open_historical_data"),   # Fees
    17: ("historical_data", "_open_historical_data"),   # Slippage
    18: ("historical_data", "_open_historical_data"),   # Liquidity
    19: ("historical_data", "_open_historical_data"),   # Volatility
    20: ("chart", "_open_chart"),                       # Candlestick charts
    21: ("historical_data", "_open_historical_data"),   # OHLCV data
    22: ("historical_data", "_open_historical_data"),   # Timeframes
    25: ("chart", "_open_chart"),                       # Technical indicators
    26: ("chart", "_open_chart"),                       # Moving averages
    27: ("chart", "_open_chart"),                       # RSI
    28: ("chart", "_open_chart"),                       # MACD
    29: ("chart", "_open_chart"),                       # Bollinger Bands
    30: ("chart", "_open_chart"),                       # ATR and volatility
    31: ("strategy_builder", "_open_strategy_builder"), # What is a trading strategy
    32: ("paper", "_open_paper"),                       # Risk management
    33: ("paper", "_open_paper"),                       # Position sizing
    34: ("paper", "_open_paper"),                       # Stop-loss
    35: ("paper", "_open_paper"),                       # Take-profit
    36: ("paper", "_open_paper"),                       # Drawdown
    37: ("paper", "_open_paper"),                       # Paper trading
    38: ("backtesting", "_open_backtesting"),           # Backtesting
    39: ("backtesting", "_open_backtesting"),           # Look-ahead bias
    40: ("backtesting", "_open_backtesting"),           # Overfitting
    41: ("backtesting", "_open_backtesting"),           # Train/validation/test
    42: ("backtesting", "_open_backtesting"),           # Why backtests can lie
    43: ("paper", "_open_paper"),                       # Why paper trading is different
    44: ("historical_data", "_open_historical_data"),   # API keys
    45: ("historical_data", "_open_historical_data"),   # API key security
    # Level 2 - Practical trading (lessons 48-67)
    48: ("historical_data", "_open_historical_data"),
    49: ("historical_data", "_open_historical_data"),
    50: ("chart", "_open_chart"),
    51: ("chart", "_open_chart"),
    52: ("chart", "_open_chart"),
    53: ("chart", "_open_chart"),
    54: ("chart", "_open_chart"),
    55: ("chart", "_open_chart"),
    56: ("chart", "_open_chart"),
    57: ("chart", "_open_chart"),
    58: ("chart", "_open_chart"),
    59: ("chart", "_open_chart"),
    60: ("chart", "_open_chart"),
    61: ("strategy_builder", "_open_strategy_builder"),
    62: ("strategy_builder", "_open_strategy_builder"),
    63: ("backtesting", "_open_backtesting"),
    64: ("backtesting", "_open_backtesting"),
    65: ("backtesting", "_open_backtesting"),
    66: ("backtesting", "_open_backtesting"),
    67: ("paper", "_open_paper"),
    # Level 3 - Quantitative research (lessons 68-87)
    68: ("wizard", "_open_research_wizard"),
    69: ("wizard", "_open_research_wizard"),
    70: ("wizard", "_open_research_wizard"),
    71: ("wizard", "_open_research_wizard"),
    72: ("backtesting", "_open_backtesting"),
    73: ("backtesting", "_open_backtesting"),
    74: ("backtesting", "_open_backtesting"),
    75: ("backtesting", "_open_backtesting"),
    76: ("backtesting", "_open_backtesting"),
    77: ("backtesting", "_open_backtesting"),
    78: ("backtesting", "_open_backtesting"),
    79: ("backtesting", "_open_backtesting"),
    80: ("backtesting", "_open_backtesting"),
    81: ("wizard", "_open_research_wizard"),
    82: ("wizard", "_open_research_wizard"),
    83: ("wizard", "_open_research_wizard"),
    84: ("wizard", "_open_research_wizard"),
    85: ("backtesting", "_open_backtesting"),
    86: ("backtesting", "_open_backtesting"),
    87: ("backtesting", "_open_backtesting"),
}


@dataclass(frozen=True)
class Lesson:
    """Level-1 lesson header kept for the chapter-23 learning path."""

    number: int
    title: str


#: The original chapter 23 path (Level 1), 20 lessons.
LESSONS: tuple[Lesson, ...] = tuple(
    Lesson(lesson.number, lesson.title) for lesson in lessons_for_level(1)
)


class LearningCenterWidget(QWidget):
    """Offline, three-level course with quizzes and progress tracking."""

    def __init__(
        self,
        paths: AppPaths | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._paths = paths or AppPaths()
        self._completed: set[int] = set()
        self._bookmarks: set[int] = set()
        self._quiz_results: dict[int, bool] = {}
        self._last_lesson: int | None = None
        self._current: int | None = None
        self._load_progress()

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

        level_row = QHBoxLayout()
        level_row.addWidget(QLabel(self.tr("Level:")))
        self.level_combo = QComboBox()
        for level in LEVELS:
            self.level_combo.addItem(self.tr(LEVEL_NAMES[level]), level)
        self.level_combo.currentIndexChanged.connect(self._on_level_changed)
        level_row.addWidget(self.level_combo)
        self.resume_button = QPushButton(self.tr("Continue where I left off"))
        self.resume_button.clicked.connect(self.resume)
        level_row.addWidget(self.resume_button)
        layout.addLayout(level_row)

        body = QHBoxLayout()
        self.lesson_list = QListWidget()
        self.lesson_list.currentItemChanged.connect(self._on_lesson_selected)
        body.addWidget(self.lesson_list, 2)

        detail_column = QVBoxLayout()
        self.lesson_view = QTextBrowser()
        self.lesson_view.setOpenExternalLinks(False)
        detail_column.addWidget(self.lesson_view)

        self.quiz_group_box = QGroupBox(self.tr("Quiz"))
        quiz_layout = QVBoxLayout(self.quiz_group_box)
        self.quiz_question = QLabel("")
        self.quiz_question.setWordWrap(True)
        quiz_layout.addWidget(self.quiz_question)
        self.quiz_button_group = QButtonGroup(self)
        self._quiz_buttons: list[QRadioButton] = []
        for _ in range(4):
            button = QRadioButton("")
            self.quiz_button_group.addButton(button)
            quiz_layout.addWidget(button)
            self._quiz_buttons.append(button)
        self.submit_button = QPushButton(self.tr("Submit answer"))
        self.submit_button.clicked.connect(self._submit_quiz)
        quiz_layout.addWidget(self.submit_button)
        self.quiz_feedback = QLabel("")
        self.quiz_feedback.setWordWrap(True)
        quiz_layout.addWidget(self.quiz_feedback)
        detail_column.addWidget(self.quiz_group_box)
        body.addLayout(detail_column, 3)
        layout.addLayout(body)

        actions = QHBoxLayout()
        self.complete_button = QPushButton(self.tr("Mark lesson as completed"))
        self.complete_button.clicked.connect(self._complete_current)
        self.bookmark_button = QPushButton(self.tr("Bookmark this lesson"))
        self.bookmark_button.clicked.connect(self.toggle_bookmark_current)
        self.open_tool_button = QPushButton(self.tr("Open related tool…"))
        self.open_tool_button.clicked.connect(self._open_lesson_tool)
        self.open_tool_button.setEnabled(False)
        actions.addWidget(self.complete_button)
        actions.addWidget(self.bookmark_button)
        actions.addWidget(self.open_tool_button)
        layout.addLayout(actions)

        self.status_label = QLabel("")
        layout.addWidget(self.status_label)

        self.start_button = QPushButton(
            self.tr("Start Here: Cryptocurrency for Complete Beginners.")
        )
        self.start_button.clicked.connect(self._show_first_lesson)
        layout.addWidget(self.start_button)

        self.set_level(1)
        self._update_status()

    # -- level and list ---------------------------------------------------

    def set_level(self, level: int, *, show_first: bool = True) -> None:
        """Populate the list with the lessons of ``level``."""
        self.lesson_list.blockSignals(True)
        self.lesson_list.clear()
        for lesson in lessons_for_level(level):
            item = QListWidgetItem(f"{lesson.number}. {lesson.title}")
            item.setData(Qt.ItemDataRole.UserRole, lesson.number)
            self.lesson_list.addItem(item)
        self.lesson_list.blockSignals(False)
        if show_first and self.lesson_list.count():
            self.lesson_list.setCurrentRow(0)

    def _on_level_changed(self) -> None:
        self.set_level(self.current_level())

    def current_level(self) -> int:
        return int(self.level_combo.currentData() or 1)

    # -- lesson display ---------------------------------------------------

    def lesson_text(self, number: int) -> str:
        """Render one lesson for the detail pane."""
        lesson = get_lesson(number)
        if lesson is None:
            return self.tr("Lesson not found.")
        state = self.tr("completed") if number in self._completed else self.tr(
            "not completed yet"
        )
        body = lesson.body
        # Keep the transcript readable but preserve intended paragraphs.
        body = "\n\n".join(part.strip() for part in body.split(". "))
        return "\n".join(
            [
                f"== {self.tr('Lesson')} {lesson.number}: {lesson.title} ==",
                f"({self.tr('Level')} {lesson.level}, {state})",
                "",
                body,
            ]
        )

    def show_lesson(self, number: int) -> str:
        """Show a lesson and load its quiz; returns the rendered text."""
        lesson = get_lesson(number)
        if lesson is None:
            raise ValueError(f"Unknown lesson number: {number}")
        self._current = number
        self._last_lesson = number
        self.lesson_view.setPlainText(self.lesson_text(number))
        self._load_quiz(lesson)
        
        # Enable/disable "Open related tool" button based on lesson mapping
        has_tool = number in LESSON_SCREEN_MAP
        self.open_tool_button.setEnabled(has_tool)
        if has_tool:
            screen_name, _ = LESSON_SCREEN_MAP[number]
            self.open_tool_button.setToolTip(
                self.tr("Open {screen} for this lesson").format(screen=screen_name)
            )
        else:
            self.open_tool_button.setToolTip("")
        
        self._save_progress()
        return self.lesson_view.toPlainText()

    def _load_quiz(self, lesson) -> None:
        quiz = lesson.quiz
        self.quiz_question.setText(quiz.question)
        for index, button in enumerate(self._quiz_buttons):
            if index < len(quiz.options):
                button.setText(quiz.options[index])
                button.setVisible(True)
                button.setChecked(False)
            else:
                button.setVisible(False)
        self.quiz_group_box.setEnabled(True)
        previous = self._quiz_results.get(lesson.number)
        if previous is True:
            self.quiz_feedback.setText(
                self.tr("You already answered this quiz correctly.")
            )
        elif previous is False:
            self.quiz_feedback.setText(
                self.tr("Your previous answer was wrong — try again.")
            )
        else:
            self.quiz_feedback.setText("")

    def _on_lesson_selected(self, current: QListWidgetItem | None, _prev) -> None:
        if current is None:
            return
        self.show_lesson(current.data(Qt.ItemDataRole.UserRole))

    def _show_first_lesson(self) -> None:
        if self.lesson_list.count():
            self.lesson_list.setCurrentRow(0)

    # -- quiz -------------------------------------------------------------

    def answer_quiz(self, number: int, choice: int) -> bool:
        """Grade one quiz answer and remember the result.

        This is the testable core; the buttons call it through
        :meth:`_submit_quiz`.
        """
        lesson = get_lesson(number)
        if lesson is None:
            raise ValueError(f"Unknown lesson number: {number}")
        correct = lesson.quiz.is_correct(choice)
        self._quiz_results[number] = correct
        self._save_progress()
        return correct

    def _selected_choice(self) -> int:
        # ``isVisible()`` is False for every child of a window that has
        # not been shown (e.g. in headless tests), so rely on the quiz's
        # own option count instead.
        if self._current is None:
            return -1
        lesson = get_lesson(self._current)
        if lesson is None:
            return -1
        for index in range(len(lesson.quiz.options)):
            if self._quiz_buttons[index].isChecked():
                return index
        return -1

    def _submit_quiz(self) -> None:
        if self._current is None:
            return
        choice = self._selected_choice()
        lesson = get_lesson(self._current)
        if lesson is None:
            return
        if choice < 0:
            self.quiz_feedback.setText(
                self.tr("Choose one answer before submitting.")
            )
            return
        correct = self.answer_quiz(self._current, choice)
        if correct:
            self.quiz_feedback.setText(
                self.tr("Correct. {why}").format(why=lesson.quiz.explanation)
            )
            self.mark_completed(self._current)
        else:
            self.quiz_feedback.setText(
                self.tr(
                    "Not correct. Re-read the lesson and try again. "
                    "The right answer is worth understanding, not guessing."
                )
            )

    # -- progress ---------------------------------------------------------

    def mark_completed(self, number: int) -> None:
        """Mark lesson ``number`` as completed and update the list view."""
        if get_lesson(number) is None:
            raise ValueError(f"Unknown lesson number: {number}")
        self._completed.add(number)
        for row in range(self.lesson_list.count()):
            item = self.lesson_list.item(row)
            if item.data(Qt.ItemDataRole.UserRole) == number:
                text = item.text()
                if not text.startswith("[x]"):
                    item.setText(f"[x] {text}")
        self._update_status()
        self._save_progress()

    def _complete_current(self) -> None:
        """Mark the lesson currently open in the detail pane."""
        if self._current is None:
            return
        self.mark_completed(self._current)
        self.lesson_view.setPlainText(self.lesson_text(self._current))

    def _open_lesson_tool(self) -> None:
        """Open the related tool for the current lesson (chapter 80)."""
        if self._current is None:
            return
        mapping = LESSON_SCREEN_MAP.get(self._current)
        if not mapping:
            return
        screen_name, action_name = mapping
        
        # Find the main window to call the action
        from PyQt6.QtWidgets import QApplication
        main_window = None
        for widget in QApplication.topLevelWidgets():
            if hasattr(widget, action_name):
                main_window = widget
                break
        
        if main_window is not None:
            action = getattr(main_window, action_name)
            action()
        else:
            # Fallback: show a helpful message
            self.lesson_view.setPlainText(
                self.tr(
                    "Lesson {number} relates to {screen}.\n\n"
                    "Open the {screen} from the main menu to try it."
                ).format(
                    number=self._current,
                    screen=screen_name.replace("_", " ").title()
                )
            )

    def completed_lessons(self) -> set[int]:
        return set(self._completed)

    def bookmarked_lessons(self) -> set[int]:
        return set(self._bookmarks)

    def toggle_bookmark_current(self) -> None:
        number = self._current
        if number is None:
            return
        if number in self._bookmarks:
            self._bookmarks.discard(number)
        else:
            self._bookmarks.add(number)
        self._update_status()
        self._save_progress()

    def next_lesson(self) -> int | None:
        """First lesson not yet completed, in curriculum order."""
        for lesson in CURRICULUM:
            if lesson.number not in self._completed:
                return lesson.number
        return None

    def resume(self) -> str | None:
        """Jump to the first uncompleted lesson (chapter 23)."""
        number = self.next_lesson()
        if number is None:
            self.lesson_view.setPlainText(
                self.tr("Every lesson is completed. Well done.")
            )
            return None
        lesson = get_lesson(number)
        assert lesson is not None
        self.level_combo.setCurrentIndex(LEVELS.index(lesson.level))
        self.select_lesson(number)
        return self.show_lesson(number)

    def select_lesson(self, number: int) -> None:
        """Select a lesson in the current list if present."""
        for row in range(self.lesson_list.count()):
            item = self.lesson_list.item(row)
            if item.data(Qt.ItemDataRole.UserRole) == number:
                self.lesson_list.setCurrentRow(row)
                return

    def _update_status(self) -> None:
        self.status_label.setText(
            self.tr("{done} of {total} lessons completed · {bookmarks} bookmarked").format(
                done=len(self._completed),
                total=total_lessons(),
                bookmarks=len(self._bookmarks),
            )
        )

    # -- persistence ------------------------------------------------------

    def progress_path(self) -> Path:
        return self._paths.data_dir / "learning" / "progress.json"

    def _load_progress(self) -> None:
        path = self.progress_path()
        if not path.exists():
            return
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return
        self._completed.update(
            number
            for number in data.get("completed_lessons", [])
            if get_lesson(number) is not None
        )
        self._bookmarks.update(
            number
            for number in data.get("bookmarked_lessons", [])
            if get_lesson(number) is not None
        )
        self._quiz_results.update(
            {
                int(number): bool(result)
                for number, result in data.get("quiz_results", {}).items()
            }
        )
        self._last_lesson = data.get("last_lesson")

    def _save_progress(self) -> None:
        path = self.progress_path()
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                json.dumps(
                    {
                        "completed_lessons": sorted(self._completed),
                        "bookmarked_lessons": sorted(self._bookmarks),
                        "quiz_results": {
                            str(k): v for k, v in self._quiz_results.items()
                        },
                        "last_lesson": self._last_lesson,
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )
        except OSError:
            # Progress is a convenience, never a reason to crash the UI.
            return

    @property
    def last_lesson(self) -> int | None:
        return self._last_lesson

    @staticmethod
    def guide_path() -> Path:
        """Bundled beginner guide (offline content, chapter 23)."""
        return BEGINNERS_DIR / "00-start-here.md"

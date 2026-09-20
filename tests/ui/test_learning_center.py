"""Tests for the Learning Center (ROADMAP.md chapters 23 and 80).

The previous version of this suite only checked the lesson list; the
screen used to crash on a lesson click and on the quiz. These tests
exercise the real interactions.
"""

from __future__ import annotations

import pytest

pytest.importorskip("PyQt6")

from crypto_trading_lab.configuration.xdg import AppPaths  # noqa: E402
from crypto_trading_lab.education.curriculum import (  # noqa: E402
    CURRICULUM,
    get_lesson,
    lessons_for_level,
    total_lessons,
)
from crypto_trading_lab.ui.education.learning_center import (  # noqa: E402
    LESSONS,
    LearningCenterWidget,
)


def _paths(tmp_path) -> AppPaths:
    return AppPaths(
        config_dir=tmp_path / "c",
        data_dir=tmp_path / "d",
        cache_dir=tmp_path / "k",
        log_dir=tmp_path / "l",
    )


@pytest.fixture()
def center(qapp, tmp_path):
    widget = LearningCenterWidget(paths=_paths(tmp_path))
    yield widget
    widget.close()


def test_learning_path_has_twenty_lessons():
    assert len(LESSONS) == 20
    numbers = [lesson.number for lesson in LESSONS]
    assert numbers == list(range(1, 21))


def test_path_includes_survival_lessons():
    titles = " ".join(lesson.title for lesson in LESSONS)
    assert "profits are never guaranteed" in titles
    assert "money you need for living" in titles


def test_curriculum_has_three_levels_with_real_quizzes():
    assert total_lessons() == len(CURRICULUM) >= 48
    assert len(lessons_for_level(1)) == 20
    assert len(lessons_for_level(2)) >= 16
    assert len(lessons_for_level(3)) >= 12
    for lesson in CURRICULUM:
        assert len(lesson.body) > 80
        assert 2 <= len(lesson.quiz.options) <= 4
        assert 0 <= lesson.quiz.answer_index < len(lesson.quiz.options)
        assert lesson.quiz.explanation


def test_lesson_list_shows_all_level_one_lessons(center):
    assert center.lesson_list.count() == 20


def test_clicking_a_lesson_shows_its_content(center):
    """Regression: the old code raised AttributeError on Qt.AlignHCenter."""
    text = center.show_lesson(1)

    assert "What is cryptocurrency?" in text
    assert "Lesson 1" in text


def test_quiz_grades_and_marks_completion(center):
    """Regression: the old quiz always returned False and crashed."""
    lesson = get_lesson(1)

    correct = center.answer_quiz(1, lesson.quiz.answer_index)
    wrong = center.answer_quiz(
        1, (lesson.quiz.answer_index + 1) % len(lesson.quiz.options)
    )

    assert correct is True
    assert wrong is False


def test_submit_quiz_marks_the_lesson_completed(center):
    lesson = get_lesson(2)
    center.show_lesson(2)
    center._quiz_buttons[lesson.quiz.answer_index].setChecked(True)

    center._submit_quiz()

    assert 2 in center.completed_lessons()
    assert "Correct" in center.quiz_feedback.text()


def test_mark_completed_updates_view_and_count(center):
    center.mark_completed(1)
    center.mark_completed(2)
    assert center.completed_lessons() == {1, 2}
    assert center.status_label.text().startswith(
        f"2 of {total_lessons()} lessons completed"
    )
    first_item = center.lesson_list.item(0)
    assert first_item.text().startswith("[x]")


def test_mark_completed_rejects_unknown_lesson(center):
    with pytest.raises(ValueError):
        center.mark_completed(999)


def test_progress_persists_across_instances(qapp, tmp_path):
    paths = _paths(tmp_path)
    first = LearningCenterWidget(paths=paths)
    first.mark_completed(3)
    first.toggle_bookmark_current()  # bookmarks lesson 1 (list starts there)
    first.close()

    second = LearningCenterWidget(paths=paths)
    assert 3 in second.completed_lessons()
    assert second.bookmarked_lessons()
    second.close()


def test_resume_points_to_the_first_uncompleted_lesson(center):
    center.mark_completed(1)
    center.mark_completed(2)

    text = center.resume()

    assert center.next_lesson() == 3
    assert text is not None
    assert "Lesson 3" in text


def test_level_switching_changes_the_list(center):
    center.level_combo.setCurrentIndex(1)  # Level 2
    assert center.lesson_list.count() == len(lessons_for_level(2))
    assert center.current_level() == 2


def test_guide_path_points_to_bundled_offline_guide():
    path = LearningCenterWidget.guide_path()
    assert path.exists()
    assert path.name == "00-start-here.md"


def test_main_window_opens_learning_center(qapp, window, monkeypatch, tmp_path):
    monkeypatch.setattr(
        window, "_paths", lambda: _paths(tmp_path), raising=False
    )
    window._open_learning_center()
    assert window._learning_center.isVisible()
    assert window._learning_center.lesson_list.count() == 20
    window._learning_center.close()


def test_learning_center_has_no_hardcoded_ui_strings():
    """AGENTS.md rule 7: UI chrome must be translatable."""
    from pathlib import Path

    source = Path(
        "src/crypto_trading_lab/ui/education/learning_center.py"
    ).read_text(encoding="utf-8")
    assert "self.tr(" in source
    for forbidden in ("Tomar Quiz", "Cerrar", "en construcción"):
        assert forbidden not in source

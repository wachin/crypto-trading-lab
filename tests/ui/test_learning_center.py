"""Tests for the Learning Center placeholder (chapter 23, task 26)."""

from __future__ import annotations

import pytest

pytest.importorskip("PyQt6")

from crypto_trading_lab.ui.education.learning_center import (  # noqa: E402
    LESSONS,
    LearningCenterWidget,
)


@pytest.fixture()
def center(qapp):
    widget = LearningCenterWidget()
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


def test_lesson_list_shows_all_lessons(center):
    assert center.lesson_list.count() == 20


def test_mark_completed_updates_view_and_count(center):
    center.mark_completed(1)
    center.mark_completed(2)
    assert center.completed_lessons() == {1, 2}
    assert center.status_label.text() == "2 of 20 lessons completed"
    first_item = center.lesson_list.item(0)
    assert first_item.text().startswith("[x]")


def test_mark_completed_rejects_unknown_lesson(center):
    with pytest.raises(ValueError):
        center.mark_completed(99)


def test_guide_path_points_to_bundled_offline_guide():
    path = LearningCenterWidget.guide_path()
    assert path.exists()
    assert path.name == "00-start-here.md"


def test_main_window_opens_learning_center(qapp, window):
    window.learning_center_button.click()
    assert window._learning_center.isVisible()
    assert window._learning_center.lesson_list.count() == 20
    window._learning_center.close()

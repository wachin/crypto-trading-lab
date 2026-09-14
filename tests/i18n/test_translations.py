"""Tests for the translation infrastructure (chapters 20-21, tasks 15-17)."""

from __future__ import annotations

import pytest

from crypto_trading_lab.i18n.translations import (
    DEFAULT_LANGUAGE,
    SUPPORTED_LANGUAGES,
    apply_language,
    qt_translation_files,
    translation_file,
)


def test_english_is_default_and_source():
    assert DEFAULT_LANGUAGE == "en"
    assert SUPPORTED_LANGUAGES[0] == DEFAULT_LANGUAGE


def test_translation_file_layout():
    path = translation_file("es")
    assert path.name == "crypto_trading_lab_es.qm"
    assert "i18n" in str(path) and "translations" in str(path)


def test_spanish_qm_file_exists_and_is_listed():
    files = qt_translation_files()
    names = [f.name for f in files]
    assert "crypto_trading_lab_es.qm" in names


def test_apply_language_rejects_unknown_language(qapp):
    with pytest.raises(ValueError):
        apply_language(qapp, "fr")


def test_english_needs_no_translator(qapp):
    assert apply_language(qapp, "en") is False


def test_spanish_translator_installs_and_removes(qapp):
    installed = apply_language(qapp, "es")
    assert installed is True
    assert getattr(qapp, "_lab_translator", None) is not None
    # Switching back to English removes the translator.
    assert apply_language(qapp, "en") is False
    assert getattr(qapp, "_lab_translator", None) is None

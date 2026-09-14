"""Translation infrastructure (ROADMAP.md chapters 20-21, tasks 15-17).

English is the source and default language; Spanish is the second
language. ``.ts`` files live under ``i18n/translations`` and compiled
``.qm`` files are loaded via ``QTranslator``. Strings are marked with
``self.tr()`` so ``pylupdate6`` can extract them.
"""

from __future__ import annotations

import logging
from pathlib import Path

from PyQt6.QtCore import QLocale, QTranslator, qVersion  # noqa: F401

__all__ = [
    "DEFAULT_LANGUAGE",
    "SUPPORTED_LANGUAGES",
    "TRANSLATION_DIR",
    "translation_file",
    "apply_language",
    "qt_translation_files",
]

DEFAULT_LANGUAGE = "en"
SUPPORTED_LANGUAGES = ("en", "es")

#: Source tree location for .ts/.qm files (chapter 20.2).
TRANSLATION_DIR = Path(__file__).resolve().parent.parent / "i18n" / "translations"


def translation_file(language: str) -> Path:
    """Path of the compiled ``.qm`` file for ``language``."""
    return TRANSLATION_DIR / f"crypto_trading_lab_{language}.qm"


def apply_language(app, language: str) -> bool:
    """Install the translator for ``language`` on ``app``.

    English needs no translation file (source language, chapter 20.2).
    Returns whether a translation was installed.
    """
    if language not in SUPPORTED_LANGUAGES:
        raise ValueError(f"Unsupported language {language!r}")
    # Remove any previously installed lab translator.
    previous = getattr(app, "_lab_translator", None)
    if previous is not None:
        app.removeTranslator(previous)
        app._lab_translator = None  # noqa: SLF001
    if language == DEFAULT_LANGUAGE:
        return False
    file = translation_file(language)
    if not file.exists():
        logging.getLogger("crypto_trading_lab.app").warning(
            "translation file missing for %s: %s", language, file
        )
        return False
    translator = QTranslator(app)
    if not translator.load(str(file)):
        logging.getLogger("crypto_trading_lab.app").warning(
            "failed to load translation file %s", file
        )
        return False
    app.installTranslator(translator)
    app._lab_translator = translator  # noqa: SLF001
    return True


def qt_translation_files() -> list[Path]:
    """List compiled translation files present on disk."""
    if not TRANSLATION_DIR.exists():
        return []
    return sorted(TRANSLATION_DIR.glob("crypto_trading_lab_*.qm"))

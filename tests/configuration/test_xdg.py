"""Tests for XDG configuration handling (chapter 71.1, task 18)."""

from __future__ import annotations

import json

from crypto_trading_lab.configuration.xdg import (
    DEFAULT_LANGUAGE,
    SUPPORTED_LANGUAGES,
    AppPaths,
    Settings,
    SettingsStore,
    default_settings,
)


def test_paths_follow_xdg_layout(tmp_path):
    paths = AppPaths(
        config_dir=tmp_path / "config",
        data_dir=tmp_path / "data",
        cache_dir=tmp_path / "cache",
        log_dir=tmp_path / "logs",
    )
    assert paths.settings_file == tmp_path / "config" / "settings.json"
    assert paths.database_file == tmp_path / "data" / "crypto-trading-lab.db"
    paths.ensure_dirs()
    for directory in (paths.config_dir, paths.data_dir, paths.cache_dir, paths.log_dir):
        assert directory.exists()


def test_default_settings_english_paper_trading():
    settings = default_settings()
    assert settings.language == "en"  # chapter 20.1: English first
    assert settings.paper_trading_enabled is True  # chapter 3: default mode
    assert settings.real_trading_enabled is False


def test_settings_reject_unknown_language():
    try:
        Settings(language="fr")
    except ValueError as exc:
        assert "Unsupported language" in str(exc)
    else:
        raise AssertionError("unsupported language must be rejected")


def test_real_trading_never_enabled_via_settings_file(tmp_path):
    # Chapter 3/21: configuration import must never enable real trading.
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "settings.json").write_text(
        json.dumps({"real_trading_enabled": True, "language": "en"}),
        encoding="utf-8",
    )
    store = SettingsStore(AppPaths(config_dir=config_dir, data_dir=tmp_path / "data"))
    settings = store.load()
    assert settings.real_trading_enabled is False


def test_save_and_load_roundtrip(tmp_path):
    paths = AppPaths(config_dir=tmp_path / "config", data_dir=tmp_path / "data")
    store = SettingsStore(paths)
    settings = default_settings()
    settings.language = "es"
    store.save(settings)

    reloaded = store.load()
    assert reloaded.language == "es"
    # No secret-like keys ever appear in the settings file.
    content = (tmp_path / "config" / "settings.json").read_text(encoding="utf-8")
    for forbidden in ("api_key", "secret", "token", "password"):
        assert forbidden not in content.lower()


def test_corrupt_settings_fall_back_to_defaults(tmp_path):
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "settings.json").write_text("{ not json", encoding="utf-8")
    store = SettingsStore(AppPaths(config_dir=config_dir, data_dir=tmp_path / "data"))
    settings = store.load()
    assert settings.language == DEFAULT_LANGUAGE


def test_settings_from_dict_ignores_unknown_keys():
    settings = Settings.from_dict(
        {"language": "es", "surprise_key": "ignored"}
    )
    assert settings.language == "es"
    assert not hasattr(settings, "surprise_key")


def test_supported_languages_order():
    assert SUPPORTED_LANGUAGES[0] == "en"  # English first, Spanish second
    assert "es" in SUPPORTED_LANGUAGES

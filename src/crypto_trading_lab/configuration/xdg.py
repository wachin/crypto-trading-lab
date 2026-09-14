"""XDG-compliant application configuration (ROADMAP.md chapter 71.1, task 18).

User data lives under XDG directories (via ``platformdirs``): non-secret
settings under the config dir, databases and logs under the data dir.
API keys never appear in any of these files (chapter 8/9).
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any

import platformdirs

__all__ = [
    "APP_NAME",
    "DEFAULT_LANGUAGE",
    "SUPPORTED_LANGUAGES",
    "AppPaths",
    "Settings",
    "SettingsStore",
    "default_settings",
]

APP_NAME = "crypto-trading-lab"

#: English is the source/default language; Spanish second (chapter 20.1).
DEFAULT_LANGUAGE = "en"
SUPPORTED_LANGUAGES = ("en", "es")


def _logger() -> logging.Logger:
    return logging.getLogger("crypto_trading_lab.app")


class AppPaths:
    """Resolved XDG paths for config, data, cache, and logs (chapter 8/10)."""

    def __init__(
        self,
        config_dir: Path | None = None,
        data_dir: Path | None = None,
        cache_dir: Path | None = None,
        log_dir: Path | None = None,
    ) -> None:
        self._config_dir = Path(
            config_dir or platformdirs.user_config_dir(APP_NAME)
        )
        self._data_dir = Path(data_dir or platformdirs.user_data_dir(APP_NAME))
        self._cache_dir = Path(
            cache_dir or platformdirs.user_cache_dir(APP_NAME)
        )
        self._log_dir = Path(log_dir or self._data_dir / "logs")

    @property
    def config_dir(self) -> Path:
        return self._config_dir

    @property
    def data_dir(self) -> Path:
        return self._data_dir

    @property
    def cache_dir(self) -> Path:
        return self._cache_dir

    @property
    def log_dir(self) -> Path:
        return self._log_dir

    @property
    def settings_file(self) -> Path:
        """Non-secret settings as JSON (chapter 8: "non-secret configuration")."""
        return self._config_dir / "settings.json"

    @property
    def database_file(self) -> Path:
        return self._data_dir / "crypto-trading-lab.db"

    def ensure_dirs(self) -> None:
        """Create the XDG directories on first use."""
        for directory in (
            self._config_dir,
            self._data_dir,
            self._cache_dir,
            self._log_dir,
        ):
            directory.mkdir(parents=True, exist_ok=True)


@dataclass
class Settings:
    """Non-secret application settings (chapter 8).

    Only values safe to show on screen live here. Credentials go to
    the CredentialStore (chapter 9), never to this file.
    """

    language: str = DEFAULT_LANGUAGE
    theme: str = "system"
    paper_trading_enabled: bool = True
    real_trading_enabled: bool = False

    def __post_init__(self) -> None:
        if self.real_trading_enabled:
            # Chapter 3: real trading must never be enabled merely by
            # constructing/importing settings. Force it off here too.
            self.real_trading_enabled = False
        self.validate()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "Settings":
        known = {f for f in cls.__dataclass_fields__}
        clean = {key: value for key, value in payload.items() if key in known}
        settings = cls(**clean)
        settings.validate()
        return settings

    def validate(self) -> None:
        if self.language not in SUPPORTED_LANGUAGES:
            raise ValueError(
                f"Unsupported language {self.language!r}; "
                f"expected one of {SUPPORTED_LANGUAGES}"
            )


class SettingsStore:
    """Load/save Settings as JSON under the XDG config dir."""

    def __init__(self, paths: AppPaths | None = None) -> None:
        self._paths = paths or AppPaths()

    def load(self) -> Settings:
        file = self._paths.settings_file
        if not file.exists():
            return default_settings()
        try:
            payload = json.loads(file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            _logger().warning("settings unreadable (%s); using defaults", exc)
            return default_settings()
        return Settings.from_dict(payload)

    def save(self, settings: Settings) -> None:
        self._paths.ensure_dirs()
        target = self._paths.settings_file
        temporary = target.with_suffix(".json.tmp")
        temporary.write_text(
            json.dumps(settings.to_dict(), indent=2, sort_keys=True),
            encoding="utf-8",
        )
        temporary.replace(target)


def default_settings() -> Settings:
    """Chapter 20.1: start in English; chapter 3: paper trading default."""
    settings = Settings()
    settings.validate()
    return settings

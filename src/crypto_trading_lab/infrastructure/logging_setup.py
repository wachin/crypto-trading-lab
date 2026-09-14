"""Central logging setup with secret redaction (ROADMAP.md chapter 10).

Separate loggers for application, networking, trading, auditing, and
errors. A redaction filter strips API keys, tokens, signatures, JWTs,
and authorization headers from every record before formatting, so no
secret value ever reaches a log file (chapters 9 and 10).
"""

from __future__ import annotations

import json
import logging
import logging.handlers
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

__all__ = [
    "RedactionFilter",
    "JsonFormatter",
    "LoggingConfig",
    "AuditEvent",
    "AuditLogger",
    "configure_logging",
    "get_logger",
    "reset_logging",
]


class _Redactor:
    """Regex-based redaction of secret-looking values (chapter 9)."""

    #: Patterns applied to the rendered message; each replaces with ``***``.
    MESSAGE_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
        # Authorization: Bearer <jwt>  /  X-MBX-APIKEY headers (any case)
        (
            re.compile(
                r"(?i)\b(authorization|x-mbx-apikey|api-key|apikey)"
                r"(\s*[:=]\s*)(\S+)(\s+(\S+))*"
            ),
            r"\1\2***",
        ),
        # key=value style params that smell like secrets
        (
            re.compile(
                r"(?i)\b(api[_-]?key|secret|token|signature|password|passphrase|jwt)"
                r"(\s*[:=]\s*)(\S+)"
            ),
            r"\1\2***",
        ),
        # Raw JWTs (three dot-separated base64url segments)
        (
            re.compile(
                r"\beyJ[A-Za-z0-9_-]{4,}\.[A-Za-z0-9_-]{4,}\.[A-Za-z0-9_-]{4,}\b"
            ),
            "***",
        ),
    )

    #: Keys whose *values* are redacted when present in structured extras.
    SENSITIVE_KEYS: tuple[str, ...] = (
        "api_key",
        "apikey",
        "secret",
        "token",
        "signature",
        "password",
        "passphrase",
        "jwt",
        "authorization",
    )

    @classmethod
    def redact_message(cls, message: str) -> str:
        for pattern, replacement in cls.MESSAGE_PATTERNS:
            message = pattern.sub(replacement, message)
        return message

    @classmethod
    def redact_mapping(cls, mapping: dict[str, Any]) -> dict[str, Any]:
        redacted: dict[str, Any] = {}
        for key, value in mapping.items():
            if any(sensitive in str(key).lower() for sensitive in cls.SENSITIVE_KEYS):
                redacted[str(key)] = "***"
            elif isinstance(value, dict):
                redacted[str(key)] = cls.redact_mapping(value)
            else:
                redacted[str(key)] = value
        return redacted


class RedactionFilter(logging.Filter):
    """Logging filter that redacts secrets from messages and extras.

    Chapter 9: "Add a logging filter that redacts: API keys; tokens;
    signatures; JWTs; secrets; sensitive parameters; authorization
    headers."
    """

    def filter(self, record: logging.LogRecord) -> bool:
        message = record.getMessage()
        record.msg = _Redactor.redact_message(message)
        record.args = ()
        for name in ("api_key", "secret", "token", "signature"):
            if hasattr(record, name):
                setattr(record, name, "***")
        return True


class JsonFormatter(logging.Formatter):
    """Optional JSON log format (chapter 10)."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": self.formatTime(record, datefmt="%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        extras = getattr(record, "extras", None)
        if extras is not None:
            payload.update(_Redactor.redact_mapping(dict(extras)))
        return json.dumps(payload, sort_keys=True, default=str)


@dataclass(frozen=True)
class LoggingConfig:
    """Configuration for :func:`configure_logging` (chapter 10).

    Rotation, configurable levels, size limits, and a retention
    policy (max_files) are all chapter 10 requirements.
    """

    level: int = logging.INFO
    log_dir: Path | None = None
    filename: str = "crypto-trading-lab.log"
    json_format: bool = False
    max_bytes: int = 1_000_000
    max_files: int = 5
    quiet: bool = False


_LOGGERS = (
    "crypto_trading_lab.app",
    "crypto_trading_lab.networking",
    "crypto_trading_lab.trading",
    "crypto_trading_lab.audit",
    "crypto_trading_lab.errors",
)

_configured = False


def configure_logging(config: LoggingConfig | None = None) -> None:
    """Configure application-wide logging once (idempotent)."""
    global _configured
    if _configured:
        return
    config = config or LoggingConfig()

    formatter: logging.Formatter
    if config.json_format:
        formatter = JsonFormatter()
    else:
        formatter = logging.Formatter(
            "%(asctime)s %(levelname)-8s %(name)s: %(message)s"
        )

    handlers: list[logging.Handler] = []
    if config.log_dir is not None:
        config.log_dir.mkdir(parents=True, exist_ok=True)
        rotating = logging.handlers.RotatingFileHandler(
            config.log_dir / config.filename,
            maxBytes=config.max_bytes,
            backupCount=config.max_files,
            encoding="utf-8",
        )
        handlers.append(rotating)
    if not config.quiet:
        handlers.append(logging.StreamHandler())

    root = logging.getLogger("crypto_trading_lab")
    root.setLevel(config.level)
    for handler in handlers:
        handler.setFormatter(formatter)
        handler.addFilter(RedactionFilter())
        root.addHandler(handler)

    # Separate error log capture (chapter 10: "errors" log).
    errors_logger = logging.getLogger("crypto_trading_lab.errors")
    errors_logger.setLevel(logging.ERROR)
    errors_logger.propagate = True

    _configured = True


def get_logger(name: str) -> logging.Logger:
    """Return a logger under the project namespace."""
    return logging.getLogger(f"crypto_trading_lab.{name}")


def reset_logging() -> None:
    """Tear down handlers (used by tests)."""
    global _configured
    root = logging.getLogger("crypto_trading_lab")
    for handler in list(root.handlers):
        root.removeHandler(handler)
    _configured = False


# --- Audit log (chapter 10) -------------------------------------------------

#: Events the audit log must record, per chapter 10.
AUDIT_EVENTS = (
    "mode_change",
    "risk_setting_change",
    "strategy_created",
    "backtest_started",
    "backtest_completed",
    "experiment_started",
    "experiment_completed",
    "kill_switch_activated",
    "real_trading_attempt",
    "order_created",
    "order_canceled",
    "credential_changed",
    "critical_error",
)


@dataclass(frozen=True)
class AuditEvent:
    """One immutable audit record."""

    event: str
    timestamp: str
    detail: dict[str, Any] = field(default_factory=dict)
    correlation_id: str | None = None


class AuditLogger:
    """Writes audit events to a dedicated, redacted audit logger.

    Chapter 10: "The audit log must record: mode changes;
    risk-setting changes; ... Do not log secret values."
    """

    def __init__(self, correlation_id: str | None = None) -> None:
        self._logger = logging.getLogger("crypto_trading_lab.audit")
        self._correlation_id = correlation_id

    @property
    def correlation_id(self) -> str | None:
        return self._correlation_id

    @correlation_id.setter
    def correlation_id(self, value: str | None) -> None:
        self._correlation_id = value

    def record(self, event: str, **detail: Any) -> AuditEvent:
        if event not in AUDIT_EVENTS:
            raise ValueError(f"Unknown audit event: {event!r}")
        clean = _Redactor.redact_mapping(detail)
        audit_event = AuditEvent(
            event=event,
            timestamp=__import__("datetime").datetime.now(
                __import__("datetime").timezone.utc
            ).isoformat(),
            detail=clean,
            correlation_id=self._correlation_id,
        )
        self._logger.info(
            "event=%s%s %s",
            event,
            f" cid={audit_event.correlation_id}"
            if audit_event.correlation_id
            else "",
            json.dumps(audit_event.detail, sort_keys=True, default=str),
        )
        return audit_event

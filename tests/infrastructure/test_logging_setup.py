"""Tests for logging with secret redaction (ROADMAP.md chapters 9-10)."""

from __future__ import annotations

import json
import logging

from crypto_trading_lab.infrastructure.logging_setup import (
    AUDIT_EVENTS,
    AuditLogger,
    JsonFormatter,
    LoggingConfig,
    RedactionFilter,
    configure_logging,
    get_logger,
    reset_logging,
)


def _records_via_handler(logger_name: str, message: str):
    """Send ``message`` through the configured root and capture output."""
    captured: list[str] = []

    class Capture(logging.Handler):
        def emit(self, record):
            self.format(record)
            captured.append(record.getMessage())

    root = logging.getLogger("crypto_trading_lab")
    previous_level = root.level
    root.setLevel(logging.DEBUG)
    handler = Capture()
    handler.setFormatter(logging.Formatter("%(message)s"))
    handler.addFilter(RedactionFilter())
    root.addHandler(handler)
    try:
        logging.getLogger(logger_name).info(message)
    finally:
        root.removeHandler(handler)
        root.setLevel(previous_level)
    return captured[0]


def test_redaction_filter_strips_api_key_assignment():
    assert (
        _records_via_handler(
            "crypto_trading_lab.app",
            "connect failed api_key=AbCdEf123456 timeout=30",
        )
        == "connect failed api_key=*** timeout=30"
    )


def test_redaction_filter_strips_authorization_header():
    assert (
        _records_via_handler(
            "crypto_trading_lab.networking",
            "request headers Authorization: Bearer eyJabc.def.ghi",
        )
        == "request headers Authorization: ***"
    )


def test_redaction_filter_strips_raw_jwt():
    assert (
        _records_via_handler(
            "crypto_trading_lab.app",
            "token eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.SflKxwRJSMeKKF2QT4",
        )
        == "token ***"
    )


def test_redaction_filter_strips_signature_and_secret():
    assert (
        _records_via_handler(
            "crypto_trading_lab.trading",
            "signed payload signature=deadbeefcafe1234",
        )
        == "signed payload signature=***"
    )


def test_redaction_leaves_normal_messages_untouched():
    assert (
        _records_via_handler(
            "crypto_trading_lab.app", "order filled quantity=0.5 price=42000.10"
        )
        == "order filled quantity=0.5 price=42000.10"
    )


def test_json_formatter_redacts_sensitive_extras():
    record = logging.LogRecord(
        name="crypto_trading_lab.app",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="connect",
        args=(),
        exc_info=None,
    )
    record.extras = {"api_key": "super-secret", "latency_ms": 42}
    formatted = JsonFormatter().format(record)
    payload = json.loads(formatted)
    assert payload["api_key"] == "***"
    assert payload["latency_ms"] == 42


def test_configure_logging_writes_redacted_json(tmp_path):
    reset_logging()
    configure_logging(
        LoggingConfig(
            level=logging.DEBUG,
            log_dir=tmp_path,
            filename="test.log",
            json_format=True,
            quiet=True,
        )
    )
    logger = get_logger("app")
    logger.info("login attempt secret=hunter2 user=beginner")
    for handler in logging.getLogger("crypto_trading_lab").handlers:
        handler.flush()
    content = (tmp_path / "test.log").read_text(encoding="utf-8")
    assert "hunter2" not in content
    assert "secret=***" in content
    assert "user=beginner" in content
    reset_logging()


def test_audit_logger_records_known_events_only():
    audit = AuditLogger(correlation_id="cid-123")
    event = audit.record("order_created", symbol="BTC/USDT", quantity="0.5")
    assert event.event == "order_created"
    assert event.correlation_id == "cid-123"
    assert event.detail == {"symbol": "BTC/USDT", "quantity": "0.5"}


def test_audit_logger_rejects_unknown_events():
    audit = AuditLogger()
    try:
        audit.record("totally_made_up_event")
    except ValueError as exc:
        assert "Unknown audit event" in str(exc)
    else:
        raise AssertionError("expected ValueError for unknown audit event")


def test_audit_logger_redacts_secret_detail():
    audit = AuditLogger()
    event = audit.record("credential_changed", api_key="topsecret123")
    assert event.detail == {"api_key": "***"}


def test_audit_event_list_covers_chapter_10_requirements():
    required = {
        "mode_change",
        "risk_setting_change",
        "strategy_created",
        "backtest_started",
        "backtest_completed",
        "kill_switch_activated",
        "order_created",
        "order_canceled",
        "credential_changed",
        "critical_error",
    }
    assert required.issubset(set(AUDIT_EVENTS))

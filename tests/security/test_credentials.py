"""Tests for the credential store abstraction (ROADMAP.md chapter 9)."""

from __future__ import annotations

from datetime import datetime

from crypto_trading_lab.security.credentials import (
    Credential,
    InMemoryCredentialStore,
    MemoryCredentialStore,
)


def test_save_and_load_roundtrip():
    store = InMemoryCredentialStore()
    store.save("binance", "testnet", "SECRET-1", key_id="abc123")
    assert store.load("binance", "testnet") == "SECRET-1"


def test_load_records_last_use_timestamp():
    store = InMemoryCredentialStore()
    store.save("binance", "testnet", "SECRET-1")
    assert store.last_used("binance", "testnet") is None
    store.load("binance", "testnet")
    used = store.last_used("binance", "testnet")
    assert isinstance(used, datetime)


def test_load_missing_credential_returns_none():
    store = InMemoryCredentialStore()
    assert store.load("binance", "nope") is None


def test_delete_removes_credential():
    store = InMemoryCredentialStore()
    store.save("binance", "testnet", "SECRET-1")
    assert store.delete("binance", "testnet") is True
    assert store.load("binance", "testnet") is None
    assert store.delete("binance", "testnet") is False


def test_list_exposes_metadata_without_secret():
    store = InMemoryCredentialStore()
    store.save(
        "binance", "testnet", "SECRET-1", key_id="abc", permissions=("read",)
    )
    listed = store.list()
    assert len(listed) == 1
    credential = listed[0]
    assert isinstance(credential, Credential)
    assert credential.key_id == "abc"
    assert not hasattr(credential, "secret")


def test_withdrawal_permission_is_rejected():
    store = InMemoryCredentialStore()
    try:
        store.save("binance", "danger", "SECRET", permissions=("withdraw",))
    except PermissionError as exc:
        assert "withdrawal" in str(exc).lower()
    else:
        raise AssertionError("withdrawal permission must be rejected")


def test_validate_permissions_rejects_withdrawal():
    store = InMemoryCredentialStore()
    ok, explanation = store.validate_permissions(("canWithdraw",))
    assert ok is False
    assert "withdraw" in explanation.lower()


def test_validate_permissions_warns_on_trading():
    store = InMemoryCredentialStore()
    ok, explanation = store.validate_permissions(("read", "trade"))
    assert ok is True
    assert explanation  # a warning the UI must surface


def test_validate_permissions_allows_readonly():
    store = InMemoryCredentialStore()
    ok, explanation = store.validate_permissions(("read",))
    assert ok is True
    assert explanation == ""


def test_credential_flags_excessive_permissions():
    trading = Credential("b", "t", "k", permissions=("read", "trade"))
    readonly = Credential("b", "t", "k", permissions=("read",))
    assert trading.has_excessive_permissions is True
    assert readonly.has_excessive_permissions is False


def test_credential_detects_withdrawal_in_compound_permission():
    credential = Credential("b", "t", "k", permissions=("read,withdraw",))
    assert credential.has_withdrawal_permission is True


def test_mock_alias_matches_in_memory_store():
    assert MemoryCredentialStore is InMemoryCredentialStore


def test_save_rejects_blank_labels():
    store = InMemoryCredentialStore()
    try:
        store.save("binance", "", "SECRET")
    except ValueError:
        pass
    else:
        raise AssertionError("blank label must be rejected")


def test_simulated_load_failure_returns_none():
    store = InMemoryCredentialStore()
    store.save("binance", "testnet", "SECRET")
    store.simulate_load_failure("binance", "testnet")
    assert store.load("binance", "testnet") is None

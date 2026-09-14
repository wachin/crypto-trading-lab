"""Credential storage abstraction (ROADMAP.md chapter 9).

An abstract ``CredentialStore`` with three initial implementations:
system keyring, in-memory storage for tests, and a mock. Secrets are
never written to disk, logs, or the database. Withdrawal permissions
are blocked and excessive permissions warned about (chapter 9).
"""

from __future__ import annotations

import abc
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable
from urllib.parse import urlparse

__all__ = [
    "Credential",
    "CredentialStore",
    "InMemoryCredentialStore",
    "KeyringCredentialStore",
    "MemoryCredentialStore",
]


#: Permissions that must never be granted to an API key (chapter 9).
FORBIDDEN_PERMISSIONS = ("withdraw",)

#: Permissions that trigger a warning when granted (chapter 9).
WARNING_PERMISSIONS = ("trade",)


@dataclass(frozen=True)
class Credential:
    """A stored credential plus safe-to-display metadata (chapter 9)."""

    exchange: str
    label: str
    key_id: str
    permissions: tuple[str, ...] = ()

    @property
    def has_withdrawal_permission(self) -> bool:
        """True when the credential can move funds off the exchange."""
        return any(
            forbidden in permission.lower()
            for permission in self.permissions
            for forbidden in FORBIDDEN_PERMISSIONS
        )

    @property
    def has_excessive_permissions(self) -> bool:
        """True when the credential grants more than read-only access."""
        return any(
            warned in permission.lower()
            for permission in self.permissions
            for warned in WARNING_PERMISSIONS
        )


class CredentialStore(abc.ABC):
    """Abstract secret storage (chapter 9).

    Implementations must never log secret values and must return
    metadata (``list``) that is safe to display on screen.
    """

    @abc.abstractmethod
    def save(
        self,
        exchange: str,
        label: str,
        secret: str,
        *,
        key_id: str = "",
        permissions: tuple[str, ...] = (),
    ) -> Credential:
        """Store a secret under ``exchange``/``label``."""

    @abc.abstractmethod
    def load(self, exchange: str, label: str) -> str | None:
        """Return the secret, or ``None`` when absent. Never logged."""

    @abc.abstractmethod
    def delete(self, exchange: str, label: str) -> bool:
        """Delete a credential; return whether it existed."""

    @abc.abstractmethod
    def list(self) -> list[Credential]:
        """List credentials without exposing secret values."""

    @abc.abstractmethod
    def last_used(self, exchange: str, label: str) -> datetime | None:
        """Last-use date, shown without the secret (chapter 9)."""

    # --- shared policy helpers ------------------------------------------

    def validate_permissions(
        self, permissions: tuple[str, ...]
    ) -> tuple[bool, str]:
        """Enforce the chapter 9 permission rules.

        Returns ``(ok, explanation)``. Withdrawal permissions are
        always rejected; trading permissions produce a warning the UI
        must surface.
        """
        lowered = tuple(p.lower() for p in permissions)
        for forbidden in FORBIDDEN_PERMISSIONS:
            for permission in lowered:
                if forbidden in permission:
                    return (
                        False,
                        "API keys with withdrawal permissions are "
                        "rejected: keys that can withdraw funds are "
                        "never safe to give to a trading application.",
                    )
        for warned in WARNING_PERMISSIONS:
            for permission in lowered:
                if warned in permission:
                    return (
                        True,
                        "This key can place orders. Use it only on a "
                        "testnet account while learning.",
                    )
        return True, ""


class InMemoryCredentialStore(CredentialStore):
    """In-memory storage used by automated tests (chapter 9).

    Secrets live only in process memory; ``list`` exposes metadata
    without secret values.
    """

    def __init__(self) -> None:
        self._secrets: dict[tuple[str, str], str] = {}
        self._meta: dict[tuple[str, str], Credential] = {}
        self._used: dict[tuple[str, str], datetime] = {}
        self._deny: set[tuple[str, str]] = set()

    def save(
        self,
        exchange: str,
        label: str,
        secret: str,
        *,
        key_id: str = "",
        permissions: tuple[str, ...] = (),
    ) -> Credential:
        ok, _explanation = self.validate_permissions(permissions)
        if not ok:
            raise PermissionError(
                "Credential with withdrawal permission rejected"
            )
        if not exchange or not label:
            raise ValueError("exchange and label are required")
        key = (exchange.lower(), label)
        credential = Credential(
            exchange=exchange,
            label=label,
            key_id=key_id or "stored",
            permissions=permissions,
        )
        self._secrets[key] = secret
        self._meta[key] = credential
        return credential

    def load(self, exchange: str, label: str) -> str | None:
        key = (exchange.lower(), label)
        if key not in self._secrets or key in self._deny:
            return None
        self._used[key] = datetime.now(tz=timezone.utc)
        return self._secrets[key]

    def delete(self, exchange: str, label: str) -> bool:
        key = (exchange.lower(), label)
        existed = key in self._secrets
        self._secrets.pop(key, None)
        self._meta.pop(key, None)
        self._used.pop(key, None)
        return existed

    def list(self) -> list[Credential]:
        return list(self._meta.values())

    def last_used(self, exchange: str, label: str) -> datetime | None:
        return self._used.get((exchange.lower(), label))

    # -- test helper ------------------------------------------------------

    def simulate_load_failure(self, exchange: str, label: str) -> None:
        """Simulate a broken credential for testing failure paths."""
        self._deny.add((exchange.lower(), label))


# Backwards-friendly alias matching chapter 9's "mock implementation
# for unit tests" wording.
MemoryCredentialStore = InMemoryCredentialStore


class KeyringCredentialStore(CredentialStore):
    """System keyring backend (chapter 9: "system keyring").

    The keyring library is imported lazily so environments without a
    secret service (headless CI) can still use the in-memory store.
    """

    SERVICE = "crypto-trading-lab"

    def __init__(self) -> None:
        try:
            import keyring  # type: ignore[import-not-found]

            self._keyring = keyring
        except ImportError as exc:  # pragma: no cover - environment
            raise RuntimeError(
                "python3-keyring is not available; use the in-memory "
                "store for tests and install python3-keyring for real "
                "credential storage"
            ) from exc

    def _k(self, exchange: str, label: str) -> str:
        return f"{exchange.lower()}:{label}"

    def save(
        self,
        exchange: str,
        label: str,
        secret: str,
        *,
        key_id: str = "",
        permissions: tuple[str, ...] = (),
    ) -> Credential:
        ok, _explanation = self.validate_permissions(permissions)
        if not ok:
            raise PermissionError(
                "Credential with withdrawal permission rejected"
            )
        self._keyring.set_password(self.SERVICE, self._k(exchange, label), secret)
        credential = Credential(
            exchange=exchange,
            label=label,
            key_id=key_id or "keyring",
            permissions=permissions,
        )
        # Store display metadata (no secret) for listing.
        self._keyring.set_password(
            f"{self.SERVICE}-meta",
            self._k(exchange, label),
            f"{key_id or 'keyring'};{','.join(permissions)}",
        )
        return credential

    def load(self, exchange: str, label: str) -> str | None:
        secret = self._keyring.get_password(
            self.SERVICE, self._k(exchange, label)
        )
        return secret

    def delete(self, exchange: str, label: str) -> bool:
        key = self._k(exchange, label)
        existed = (
            self._keyring.get_password(self.SERVICE, key) is not None
        )
        try:
            self._keyring.delete_password(self.SERVICE, key)
            self._keyring.delete_password(f"{self.SERVICE}-meta", key)
        except Exception:  # pragma: no cover - backend specific
            pass
        return existed

    def list(self) -> list[Credential]:
        # The keyring backend exposes no enumeration API; track nothing
        # beyond what the GUI itself saved. Listing is best-effort.
        return []

    def last_used(self, exchange: str, label: str) -> datetime | None:
        # Keyring offers no timestamps; report unknown.
        return None

"""Errors raised by exchange adapters.

Owns the adapter-side error taxonomy (chapter 26) that translates
exchange/CCXT errors into domain errors; chapter 27's connection state
machine consumes these to move between states such as ``RATE_LIMITED``
and ``ERROR``.
"""

from __future__ import annotations

from crypto_trading_lab.domain.models import ConnectionState

__all__ = [
    "AdapterError",
    "AdapterNotSupported",
    "AdapterConnectionError",
    "AdapterAuthenticationError",
    "AdapterRateLimited",
    "AdapterNetworkError",
    "AdapterRequestError",
    "AdapterInvalidOrder",
    "AdapterInsufficientFunds",
    "AdapterDataError",
    "suggest_connection_state",
]


class AdapterError(Exception):
    """Base class for every exchange-adapter error."""


class AdapterNotSupported(AdapterError):
    """The adapter does not support the requested operation."""


class AdapterConnectionError(AdapterError):
    """Generic connection-level failure (maps to ``ERROR`` state)."""


class AdapterAuthenticationError(AdapterConnectionError):
    """Credentials missing, wrong, or lacking permissions."""


class AdapterRateLimited(AdapterError):
    """The exchange asked us to slow down (maps to ``RATE_LIMITED``)."""


class AdapterNetworkError(AdapterConnectionError):
    """Network-level failure such as timeout or unreachable host."""


class AdapterRequestError(AdapterError):
    """The exchange rejected a request for a generic reason."""


class AdapterInvalidOrder(AdapterRequestError):
    """The order was rejected as invalid (size, price, precision...)."""


class AdapterInsufficientFunds(AdapterRequestError):
    """The account lacks funds for the request."""


class AdapterDataError(AdapterError):
    """A response could not be normalized into a domain model."""


def suggest_connection_state(error: AdapterError) -> ConnectionState:
    """Map an adapter error to the connection state it implies (chapter 27)."""
    if isinstance(error, AdapterRateLimited):
        return ConnectionState.RATE_LIMITED
    if isinstance(error, AdapterAuthenticationError):
        return ConnectionState.ERROR
    if isinstance(error, AdapterConnectionError):
        return ConnectionState.RECONNECTING
    return ConnectionState.ERROR

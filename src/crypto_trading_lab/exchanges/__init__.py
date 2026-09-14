"""Exchange adapters: ports and implementations (ROADMAP.md chapter 6.2).

Layout:

- ``base/``     — the ``ExchangeAdapter`` port owned by the application.
- ``mock/``     — fully local provider for tests, demos, and replay (26.1).
- ``ccxt/``     — CCXT-backed implementation (study: Part D of
  ``docs/en/developers/reference-projects.md``).
- ``binance/``  — endpoint configuration, centralized (26.2).

Rules enforced here:

- Exchange-specific data never leaks past this package: every adapter
  normalizes into ``crypto_trading_lab.domain.models`` (chapter 7).
- CCXT (or any third-party library) is injected as a dependency; this
  package must remain importable without it installed.
"""

from crypto_trading_lab.exchanges.base.adapter import ExchangeAdapter, Capability
from crypto_trading_lab.exchanges.errors import (
    AdapterError,
    AdapterAuthenticationError,
    AdapterConnectionError,
    AdapterDataError,
    AdapterInsufficientFunds,
    AdapterInvalidOrder,
    AdapterNetworkError,
    AdapterNotSupported,
    AdapterRateLimited,
    AdapterRequestError,
    suggest_connection_state,
)

__all__ = [
    "ExchangeAdapter",
    "Capability",
    "AdapterError",
    "AdapterAuthenticationError",
    "AdapterConnectionError",
    "AdapterDataError",
    "AdapterInsufficientFunds",
    "AdapterInvalidOrder",
    "AdapterNetworkError",
    "AdapterNotSupported",
    "AdapterRateLimited",
    "AdapterRequestError",
    "suggest_connection_state",
]

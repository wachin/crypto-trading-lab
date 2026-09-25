"""Centralized Coinbase endpoint configuration (ROADMAP.md chapter 26.3).

Chapter 26.3 requires that endpoints be configurable and that endpoint
strings never be scattered throughout the codebase.

Public market data only - no authenticated trading (chapter 26.3:
"Initially add public market data; an architecture prepared for
Advanced Trade; clearly labeled experimental support").

Do not implement Coinbase Futures.
"""

from __future__ import annotations

from dataclasses import dataclass

__all__ = ["CoinbaseEndpoints", "COINBASE_SPOT_ENDPOINTS"]


@dataclass(frozen=True)
class CoinbaseEndpoints:
    """Endpoint set for one Coinbase environment."""

    environment: str
    rest_base_url: str
    websocket_base_url: str

    def __post_init__(self) -> None:
        if not self.rest_base_url.startswith(("https://", "http://")):
            raise ValueError("rest_base_url must be an http(s) URL")


#: Production spot endpoints (public market data only).
COINBASE_SPOT_ENDPOINTS = CoinbaseEndpoints(
    environment="production",
    rest_base_url="https://api.coinbase.com",
    websocket_base_url="wss://ws-feed.pro.coinbase.com",
)

#: Coinbase Sandbox (experimental, chapter 26.3).
#: WARNING: The sandbox may return static or predefined data and must not
#: be treated as a realistic profitability simulation.
COINBASE_SANDBOX_ENDPOINTS = CoinbaseEndpoints(
    environment="sandbox",
    rest_base_url="https://api-public.sandbox.pro.coinbase.com",
    websocket_base_url="wss://ws-feed-public.sandbox.pro.coinbase.com",
)


def endpoints_for(environment: str) -> CoinbaseEndpoints:
    """Return the endpoint set registered for ``environment``."""
    registry: dict[str, CoinbaseEndpoints] = {
        "production": COINBASE_SPOT_ENDPOINTS,
        "sandbox": COINBASE_SANDBOX_ENDPOINTS,
    }
    try:
        return registry[environment]
    except KeyError as exc:
        raise ValueError(
            f"unknown Coinbase environment {environment!r}; "
            f"known: {sorted(registry)}"
        ) from exc
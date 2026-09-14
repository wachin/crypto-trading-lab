"""Centralized Binance endpoint configuration (ROADMAP.md chapter 26.2).

Chapter 26.2 requires that endpoints be configurable and that endpoint
strings never be scattered throughout the codebase. Every Binance URL
used by this application must live here.

Spot-only scope: futures endpoints are intentionally absent (chapter
26.2: "Do not implement Binance Futures").
"""

from __future__ import annotations

from dataclasses import dataclass, field

__all__ = ["BinanceEndpoints", "BINANCE_SPOT_ENDPOINTS"]


@dataclass(frozen=True)
class BinanceEndpoints:
    """Endpoint set for one Binance environment."""

    environment: str
    rest_base_url: str
    websocket_base_url: str

    def __post_init__(self) -> None:
        if not self.rest_base_url.startswith(("https://", "http://")):
            raise ValueError("rest_base_url must be an http(s) URL")


#: Production spot endpoints (used only with explicit user credentials).
BINANCE_SPOT_ENDPOINTS = BinanceEndpoints(
    environment="production",
    rest_base_url="https://api.binance.com",
    websocket_base_url="wss://stream.binance.com:9443",
)

#: Binance Spot Testnet (chapter 26.2 target environment).
BINANCE_SPOT_TESTNET_ENDPOINTS = BinanceEndpoints(
    environment="spot-testnet",
    rest_base_url="https://testnet.binance.vision",
    websocket_base_url="wss://stream.testnet.binance.vision:9443",
)


def endpoints_for(environment: str) -> BinanceEndpoints:
    """Return the endpoint set registered for ``environment``."""
    registry: dict[str, BinanceEndpoints] = {
        "production": BINANCE_SPOT_ENDPOINTS,
        "spot-testnet": BINANCE_SPOT_TESTNET_ENDPOINTS,
    }
    try:
        return registry[environment]
    except KeyError as exc:
        raise ValueError(
            f"unknown Binance environment {environment!r}; "
            f"known: {sorted(registry)}"
        ) from exc

"""Centralized Binance endpoint configuration (ROADMAP.md chapter 26.2).

Chapter 26.2 requires that endpoints be configurable and that endpoint
strings never be scattered throughout the codebase. Every Binance URL
used by this application must live here.

Spot-only scope: futures endpoints are intentionally absent (chapter
26.2: "Do not implement Binance Futures").
"""

from __future__ import annotations

from dataclasses import dataclass, field

__all__ = [
    "BinanceEndpoints",
    "BINANCE_SPOT_ENDPOINTS",
    "BINANCE_SPOT_TESTNET_ENDPOINTS",
    "BINANCE_INTERVALS",
    "endpoints_for",
]


#: Every kline interval the Spot API serves, in the order it documents
#: them. This is the *streaming* vocabulary: ``1s`` is usable live, but a
#: day of it is 86,400 candles, so the historical downloader keeps its own
#: shorter list (``market_data.historical.TIMEFRAMES``).
BINANCE_INTERVALS: tuple[str, ...] = (
    "1s",
    "1m",
    "3m",
    "5m",
    "15m",
    "30m",
    "1h",
    "2h",
    "4h",
    "6h",
    "8h",
    "12h",
    "1d",
    "3d",
    "1w",
    "1M",
)


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

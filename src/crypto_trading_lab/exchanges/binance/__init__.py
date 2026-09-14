"""Binance adapter package (chapter 26.2): centralized endpoint config."""

from crypto_trading_lab.exchanges.binance.config import (
    BINANCE_SPOT_ENDPOINTS,
    BINANCE_SPOT_TESTNET_ENDPOINTS,
    BinanceEndpoints,
    endpoints_for,
)

__all__ = [
    "BinanceEndpoints",
    "BINANCE_SPOT_ENDPOINTS",
    "BINANCE_SPOT_TESTNET_ENDPOINTS",
    "endpoints_for",
]

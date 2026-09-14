"""Binance endpoint configuration tests (ROADMAP.md chapter 26.2)."""

import pytest

from crypto_trading_lab.exchanges.binance import (
    BINANCE_SPOT_ENDPOINTS,
    BINANCE_SPOT_TESTNET_ENDPOINTS,
    endpoints_for,
)


class TestBinanceEndpoints:
    def test_testnet_endpoints_are_official_spot_testnet(self):
        assert (
            BINANCE_SPOT_TESTNET_ENDPOINTS.rest_base_url
            == "https://testnet.binance.vision"
        )

    def test_production_endpoints_differ_from_testnet(self):
        assert (
            BINANCE_SPOT_ENDPOINTS.rest_base_url
            != BINANCE_SPOT_TESTNET_ENDPOINTS.rest_base_url
        )

    def test_endpoints_registry_lookup(self):
        assert (
            endpoints_for("spot-testnet") is BINANCE_SPOT_TESTNET_ENDPOINTS
        )
        assert endpoints_for("production") is BINANCE_SPOT_ENDPOINTS

    def test_unknown_environment_rejected(self):
        with pytest.raises(ValueError):
            endpoints_for("futures-testnet")

    def test_no_futures_environment_exists(self):
        # Chapter 26.2: "Do not implement Binance Futures."
        with pytest.raises(ValueError):
            endpoints_for("futures")

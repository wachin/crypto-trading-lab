"""Domain model tests (ROADMAP.md chapters 7 and 27)."""

from datetime import datetime, timezone
from decimal import Decimal

import pytest

from crypto_trading_lab.domain.models import (
    Balance,
    Candle,
    ConnectionState,
    Market,
    OrderRequest,
    OrderSide,
    OrderStatus,
    OrderType,
    Symbol,
    Ticker,
    utc_now,
)


class TestSymbol:
    def test_accepts_base_quote(self):
        assert Symbol("btc/usdt") == "BTC/USDT"

    def test_rejects_single_asset(self):
        with pytest.raises(ValueError):
            Symbol("BTCUSDT")

    def test_rejects_extra_slash(self):
        with pytest.raises(ValueError):
            Symbol("BTC/US/DT")

    def test_base_quote_properties(self):
        symbol = Symbol("ETH/USDT")
        assert symbol.base == "ETH"
        assert symbol.quote == "USDT"


class TestUtcNow:
    def test_returns_aware_utc(self):
        now = utc_now()
        assert now.tzinfo is timezone.utc


class TestCandleValidation:
    def _candle(self, **overrides):
        defaults = dict(
            symbol=Symbol("BTC/USDT"),
            interval="1h",
            open_time=datetime(2024, 1, 1, tzinfo=timezone.utc),
            close_time=datetime(2024, 1, 1, 1, tzinfo=timezone.utc),
            open=Decimal("100"),
            high=Decimal("110"),
            low=Decimal("95"),
            close=Decimal("105"),
            volume=Decimal("12.5"),
        )
        defaults.update(overrides)
        return Candle(**defaults)

    def test_valid_candle_passes(self):
        candle = self._candle()
        assert candle.close == Decimal("105")

    def test_rejects_high_below_low(self):
        with pytest.raises(ValueError):
            self._candle(high=Decimal("90"), low=Decimal("95"))

    def test_rejects_close_outside_range(self):
        with pytest.raises(ValueError):
            self._candle(close=Decimal("120"))

    def test_rejects_negative_volume(self):
        with pytest.raises(ValueError):
            self._candle(volume=Decimal("-1"))

    def test_rejects_inverted_times(self):
        with pytest.raises(ValueError):
            self._candle(
                open_time=datetime(2024, 1, 2, tzinfo=timezone.utc),
                close_time=datetime(2024, 1, 1, tzinfo=timezone.utc),
            )

    def test_rejects_naive_timestamps(self):
        # Chapter 7: UTC internally. Naive datetimes are rejected
        # explicitly instead of silently introducing timezone bugs.
        with pytest.raises(TypeError, match="timezone-aware"):
            self._candle(
                open_time=datetime(2024, 1, 1),
                close_time=datetime(2024, 1, 1, 1),
            )

    def test_rejects_non_utc_offsets(self):
        from datetime import timedelta as td

        cet = timezone(td(hours=1))
        with pytest.raises(ValueError, match="UTC"):
            self._candle(open_time=datetime(2024, 1, 1, tzinfo=cet))


class TestMoneyIsDecimal:
    def test_market_minima_are_decimal(self):
        market = Market(
            exchange="test",
            symbol=Symbol("BTC/USDT"),
            base="BTC",
            quote="USDT",
            price_precision=2,
            quantity_precision=6,
            min_quantity=Decimal("0.0001"),
            min_notional=Decimal("10"),
        )
        assert isinstance(market.min_quantity, Decimal)

    def test_market_rejects_negative_fee(self):
        with pytest.raises(ValueError):
            Market(
                exchange="test",
                symbol=Symbol("BTC/USDT"),
                base="BTC",
                quote="USDT",
                price_precision=2,
                quantity_precision=6,
                maker_fee=Decimal("-0.001"),
            )

    def test_balance_total_sums_components(self):
        balance = Balance(asset="BTC", free=Decimal("1.5"), locked=Decimal("0.5"))
        assert balance.total == Decimal("2")

    def test_balance_rejects_negative(self):
        with pytest.raises(ValueError):
            Balance(asset="BTC", free=Decimal("-1"), locked=Decimal("0"))

    def test_ticker_rejects_bid_above_ask(self):
        with pytest.raises(ValueError):
            Ticker(
                symbol=Symbol("BTC/USDT"),
                timestamp=utc_now(),
                last=Decimal("100"),
                bid=Decimal("101"),
                ask=Decimal("100"),
            )


class TestOrderRequestValidation:
    def test_limit_requires_price(self):
        with pytest.raises(ValueError):
            OrderRequest(
                symbol=Symbol("BTC/USDT"),
                side=OrderSide.BUY,
                order_type=OrderType.LIMIT,
                quantity=Decimal("1"),
            )

    def test_market_without_price_ok(self):
        request = OrderRequest(
            symbol=Symbol("BTC/USDT"),
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=Decimal("1"),
        )
        assert request.price is None

    def test_rejects_non_positive_quantity(self):
        with pytest.raises(ValueError):
            OrderRequest(
                symbol=Symbol("BTC/USDT"),
                side=OrderSide.SELL,
                order_type=OrderType.MARKET,
                quantity=Decimal("0"),
            )


class TestConnectionStatesChapter27:
    def test_all_ten_states_exist(self):
        expected = {
            "DISCONNECTED",
            "CONNECTING",
            "AUTHENTICATING",
            "SUBSCRIBING",
            "CONNECTED",
            "DEGRADED",
            "RECONNECTING",
            "RATE_LIMITED",
            "ERROR",
            "STOPPED",
        }
        assert {state.name for state in ConnectionState} == expected

    def test_every_state_has_beginner_explanation(self):
        for state in ConnectionState:
            text = state.beginner_explanation
            assert text, f"{state} lacks a beginner explanation"
            assert len(text) > 20

    def test_order_status_covers_rejection_paths(self):
        names = {status.name for status in OrderStatus}
        assert {"REJECTED", "CANCELED", "EXPIRED", "PARTIALLY_FILLED"} <= names

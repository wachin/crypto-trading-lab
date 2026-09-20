"""Tests for historical download and dataset identity (chapters 26-29, 53).

No test touches the network: the Binance page reader is a fake that
serves deterministic klines.
"""

from __future__ import annotations

import json
import urllib.parse
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from crypto_trading_lab.domain.models import Candle, Symbol
from crypto_trading_lab.market_data.historical import (
    BINANCE_PAGE_LIMIT,
    BinanceKlinesSource,
    DatasetVersion,
    HistoricalDataError,
    HistoricalRequest,
    build_dataset_id,
    compute_dataset_checksum,
    download_dataset,
    validate_candles,
)

HOUR = timedelta(hours=1)


def _kline(open_time: datetime, price: str = "100") -> list[object]:
    close_time = open_time + HOUR - timedelta(milliseconds=1)
    return [
        int(open_time.timestamp() * 1000),
        price,
        price,
        price,
        price,
        "12.5",
        int(close_time.timestamp() * 1000),
        "1250",
        10,
        "6.0",
        "600",
        "0",
    ]


class FakeBinance:
    """Serve pages of pre-built klines from memory."""

    def __init__(self, rows: list[list[object]]) -> None:
        self.rows = rows
        self.calls: list[str] = []
        self.base_url = "https://fake.local"

    def __call__(self, url: str) -> object:
        self.calls.append(url)
        query = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
        start = int(query["startTime"][0])
        end = int(query["endTime"][0])
        limit = int(query["limit"][0])
        page = [r for r in self.rows if start <= int(r[0]) <= end][:limit]
        return page


def _rows(count: int, start: datetime | None = None) -> list[list[object]]:
    start = start or datetime(2024, 1, 1, tzinfo=timezone.utc)
    return [_kline(start + i * HOUR) for i in range(count)]


def test_fetch_single_page_builds_decimal_candles():
    start = datetime(2024, 1, 1, tzinfo=timezone.utc)
    fake = FakeBinance(_rows(5, start))
    source = BinanceKlinesSource(opener=fake, pause_seconds=0)
    request = HistoricalRequest(
        "binance", "BTC/USDT", "1h", start, start + 24 * HOUR
    )

    candles = source.fetch(request)

    assert len(candles) == 5
    assert candles[0].open == Decimal("100")
    assert candles[0].symbol == Symbol("BTC/USDT")
    assert candles[0].open_time.tzinfo is not None
    assert candles == sorted(candles, key=lambda c: c.open_time)


def test_fetch_paginates_until_the_end():
    start = datetime(2024, 1, 1, tzinfo=timezone.utc)
    total = BINANCE_PAGE_LIMIT + 50
    fake = FakeBinance(_rows(total, start))
    source = BinanceKlinesSource(opener=fake, pause_seconds=0)
    request = HistoricalRequest(
        "binance", "BTC/USDT", "1h", start, start + total * HOUR
    )

    candles = source.fetch(request)

    assert len(candles) == total
    assert len(fake.calls) >= 2


def test_fetch_drops_candles_outside_the_window():
    start = datetime(2024, 1, 1, tzinfo=timezone.utc)
    fake = FakeBinance(_rows(10, start))
    source = BinanceKlinesSource(opener=fake, pause_seconds=0)
    request = HistoricalRequest(
        "binance",
        "BTC/USDT",
        "1h",
        start + 2 * HOUR,
        start + 5 * HOUR,
    )

    candles = source.fetch(request)

    assert len(candles) == 4
    assert candles[0].open_time == start + 2 * HOUR


def test_fetch_rejects_unsupported_interval():
    start = datetime(2024, 1, 1, tzinfo=timezone.utc)
    with pytest.raises(ValueError):
        HistoricalRequest("binance", "BTC/USDT", "7m", start, start + HOUR)


def test_fetch_wraps_transport_failures():
    def broken(_url: str) -> object:
        raise HistoricalDataError("HTTP 500 from the exchange")

    start = datetime(2024, 1, 1, tzinfo=timezone.utc)
    source = BinanceKlinesSource(opener=broken, pause_seconds=0)
    request = HistoricalRequest("binance", "BTC/USDT", "1h", start, start + HOUR)

    with pytest.raises(HistoricalDataError) as error:
        source.fetch(request)

    assert "HTTP 500" in str(error.value)
    assert "could not be downloaded" in error.value.beginner_explanation()


def test_transport_rejects_non_list_payload():
    start = datetime(2024, 1, 1, tzinfo=timezone.utc)
    source = BinanceKlinesSource(opener=lambda url: {"code": -1121}, pause_seconds=0)
    request = HistoricalRequest("binance", "BTC/USDT", "1h", start, start + HOUR)

    with pytest.raises(HistoricalDataError):
        source.fetch(request)


def test_validate_detects_gaps_and_duplicates():
    start = datetime(2024, 1, 1, tzinfo=timezone.utc)
    rows = _rows(5, start)
    del rows[2]  # create a one-candle gap
    rows.append(rows[0])  # duplicate the first candle
    source = BinanceKlinesSource(opener=FakeBinance(rows), pause_seconds=0)
    request = HistoricalRequest(
        "binance", "BTC/USDT", "1h", start, start + 5 * HOUR
    )

    candles = source.fetch(request)
    validation = validate_candles(candles, "1h")

    # The duplicate is collapsed by open_time, so we see a gap only.
    assert validation.candle_count == 4
    assert validation.missing == 1
    assert validation.ok is False
    assert "status: not ready" in validation.beginner_explanation().lower()


def test_validate_clean_series_is_ready():
    start = datetime(2024, 1, 1, tzinfo=timezone.utc)
    candles = [
        Candle(
            symbol=Symbol("BTC/USDT"),
            interval="1h",
            open_time=start + i * HOUR,
            close_time=start + i * HOUR + HOUR - timedelta(milliseconds=1),
            open=Decimal("100"),
            high=Decimal("101"),
            low=Decimal("99"),
            close=Decimal("100"),
            volume=Decimal("1"),
        )
        for i in range(10)
    ]

    validation = validate_candles(candles, "1h")

    assert validation.ok is True
    assert validation.missing == 0
    assert "ready for research" in validation.beginner_explanation()


def test_validate_reports_invalid_rows():
    validation = validate_candles([], "1h", invalid=3)
    assert validation.candle_count == 0
    assert not validation.ok
    assert validation.invalid == 3


def test_checksum_is_order_independent_and_content_sensitive():
    start = datetime(2024, 1, 1, tzinfo=timezone.utc)
    source = BinanceKlinesSource(opener=FakeBinance(_rows(4, start)), pause_seconds=0)
    request = HistoricalRequest("binance", "BTC/USDT", "1h", start, start + 4 * HOUR)
    candles = source.fetch(request)

    assert compute_dataset_checksum(candles) == compute_dataset_checksum(
        list(reversed(candles))
    )

    rows = _rows(4, start)
    rows[1][5] = "13.0"  # change one volume
    other = BinanceKlinesSource(
        opener=FakeBinance(rows), pause_seconds=0
    ).fetch(request)
    assert compute_dataset_checksum(candles) != compute_dataset_checksum(other)


def test_build_dataset_id_is_human_readable():
    start = datetime(2020, 1, 1, tzinfo=timezone.utc)
    end = datetime(2026, 9, 1, tzinfo=timezone.utc)
    assert (
        build_dataset_id("binance", "BTC/USDT", "1h", start, end)
        == "BINANCE_BTCUSDT_1H_2020-01-01_2026-09-01_V1"
    )


def test_dataset_version_round_trip():
    start = datetime(2024, 1, 1, tzinfo=timezone.utc)
    version = DatasetVersion(
        dataset_id="D1",
        exchange="binance",
        symbol="BTC/USDT",
        interval="1h",
        start=start,
        end=start + 10 * HOUR,
        candle_count=10,
        missing=0,
        duplicates=0,
        invalid=0,
        checksum="abc",
        source="binance-spot-rest",
        downloaded_at=start,
    )
    restored = DatasetVersion.from_dict(version.to_dict())
    assert restored == version
    assert "Dataset: D1" in restored.beginner_explanation()


def test_download_dataset_end_to_end_offline():
    start = datetime(2024, 1, 1, tzinfo=timezone.utc)
    fake = FakeBinance(_rows(24, start))
    source = BinanceKlinesSource(opener=fake, pause_seconds=0)
    request = HistoricalRequest(
        "binance", "BTC/USDT", "1h", start, start + 24 * HOUR
    )

    candles, version, validation = download_dataset(request, source=source)

    assert validation.ok
    assert version.candle_count == 24
    assert version.checksum == compute_dataset_checksum(candles)
    assert version.source.startswith("binance-spot-rest")
    assert version.dataset_id == "BINANCE_BTCUSDT_1H_2024-01-01_2024-01-02_V1"


def test_real_binance_payload_shape_is_understood():
    """The parser must accept the real 12-column kline layout."""
    start = datetime(2024, 1, 1, tzinfo=timezone.utc)
    row = json.loads(json.dumps(_kline(start, "42000.5")))
    source = BinanceKlinesSource(opener=lambda url: [row], pause_seconds=0)
    request = HistoricalRequest("binance", "BTC/USDT", "1h", start, start + HOUR)

    candles = source.fetch(request)

    assert len(candles) == 1
    assert candles[0].open == Decimal("42000.5")
    assert candles[0].volume == Decimal("12.5")

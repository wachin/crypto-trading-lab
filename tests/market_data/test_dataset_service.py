"""Tests for the download-and-store service (chapters 28, 29 and 53)."""

from __future__ import annotations

import urllib.parse
from datetime import datetime, timedelta, timezone

from crypto_trading_lab.configuration.xdg import AppPaths
from crypto_trading_lab.domain.models import Symbol
from crypto_trading_lab.market_data.dataset_service import download_and_store
from crypto_trading_lab.market_data.historical import (
    BinanceKlinesSource,
    HistoricalRequest,
)
from crypto_trading_lab.persistence.candles import CandleRepository
from crypto_trading_lab.persistence.database import (
    create_database,
    database_engine,
    make_session_factory,
)
from crypto_trading_lab.persistence.datasets import DatasetRepository

HOUR = timedelta(hours=1)


def _kline(open_time: datetime) -> list[object]:
    close_time = open_time + HOUR - timedelta(milliseconds=1)
    return [
        int(open_time.timestamp() * 1000),
        "100",
        "101",
        "99",
        "100",
        "5",
        int(close_time.timestamp() * 1000),
        "500",
        3,
        "2",
        "200",
        "0",
    ]


def _fake_source(rows):
    def opener(url: str) -> object:
        query = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
        start = int(query["startTime"][0])
        end = int(query["endTime"][0])
        limit = int(query["limit"][0])
        return [r for r in rows if start <= int(r[0]) <= end][:limit]

    return BinanceKlinesSource(opener=opener, pause_seconds=0)


def _paths(tmp_path) -> AppPaths:
    return AppPaths(
        config_dir=tmp_path / "config",
        data_dir=tmp_path / "data",
        cache_dir=tmp_path / "cache",
        log_dir=tmp_path / "logs",
    )


def test_download_and_store_persists_candles_and_identity(tmp_path):
    start = datetime(2024, 1, 1, tzinfo=timezone.utc)
    rows = [_kline(start + i * HOUR) for i in range(24)]
    request = HistoricalRequest(
        "binance", "BTC/USDT", "1h", start, start + 24 * HOUR
    )

    outcome = download_and_store(
        request, source=_fake_source(rows), paths=_paths(tmp_path)
    )

    assert outcome.ok is True
    assert outcome.saved is True
    assert outcome.version.candle_count == 24
    assert "Saved dataset" in outcome.message

    engine = database_engine(tmp_path / "data" / "crypto-trading-lab.db")
    create_database(engine)
    session = make_session_factory(engine)()
    try:
        stored = CandleRepository(session).count(
            Symbol("BTC/USDT"), "1h", exchange_name="binance"
        )
        card = DatasetRepository(session).get(outcome.version.dataset_id)
    finally:
        session.close()
        engine.dispose()

    assert stored == 24
    assert card is not None
    assert card.checksum == outcome.version.checksum
    assert card.ready is True


def test_validation_failure_is_visible_not_hidden(tmp_path):
    start = datetime(2024, 1, 1, tzinfo=timezone.utc)
    rows = [_kline(start + i * HOUR) for i in range(5)]
    del rows[2]  # gap
    request = HistoricalRequest(
        "binance", "BTC/USDT", "1h", start, start + 5 * HOUR
    )

    outcome = download_and_store(
        request, source=_fake_source(rows), paths=_paths(tmp_path)
    )

    assert outcome.saved is True
    assert outcome.version.ready is False
    assert outcome.ok is False
    assert "NOT ready" in outcome.message

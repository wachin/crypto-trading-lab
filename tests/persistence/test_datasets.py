"""Tests for the dataset repository (chapters 29 and 53)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import text

from crypto_trading_lab.market_data.historical import DatasetVersion
from crypto_trading_lab.persistence.database import (
    create_database,
    database_engine,
    make_session_factory,
)
from crypto_trading_lab.persistence.datasets import DatasetRepository


def _version(dataset_id: str = "BINANCE_BTCUSDT_1H_2024_V1", **overrides):
    start = datetime(2024, 1, 1, tzinfo=timezone.utc)
    data = dict(
        dataset_id=dataset_id,
        exchange="binance",
        symbol="BTC/USDT",
        interval="1h",
        start=start,
        end=start,
        candle_count=24,
        missing=0,
        duplicates=0,
        invalid=0,
        checksum="deadbeef",
        source="binance-spot-rest",
        downloaded_at=start,
    )
    data.update(overrides)
    return DatasetVersion(**data)


def _repository():
    engine = database_engine(":memory:")
    create_database(engine)
    session = make_session_factory(engine)()
    return DatasetRepository(session)


def test_save_and_get_round_trip():
    repo = _repository()
    repo.save(_version())

    loaded = repo.get("BINANCE_BTCUSDT_1H_2024_V1")

    assert loaded is not None
    assert loaded.symbol == "BTC/USDT"
    assert loaded.candle_count == 24
    assert loaded.checksum == "deadbeef"


def test_save_is_an_upsert():
    repo = _repository()
    repo.save(_version())
    repo.save(_version(checksum="cafebabe", candle_count=48))

    datasets = repo.list_datasets()

    assert len(datasets) == 1
    assert datasets[0].checksum == "cafebabe"
    assert datasets[0].candle_count == 48


def test_list_filters_by_symbol_and_interval():
    repo = _repository()
    repo.save(_version("D1"))
    repo.save(_version("D2", symbol="ETH/USDT"))
    repo.save(_version("D3", interval="4h"))

    assert len(repo.list_datasets()) == 3
    assert len(repo.list_datasets(symbol="BTC/USDT")) == 2
    assert len(repo.list_datasets(interval="4h")) == 1
    assert repo.latest(symbol="BTC/USDT") is not None


def test_delete_removes_the_identity_only():
    repo = _repository()
    repo.save(_version())
    assert repo.delete("BINANCE_BTCUSDT_1H_2024_V1") is True
    assert repo.get("BINANCE_BTCUSDT_1H_2024_V1") is None
    assert repo.delete("missing") is False


def test_list_datasets_is_newest_first():
    repo = _repository()
    base = datetime(2024, 1, 1, tzinfo=timezone.utc)
    repo.save(_version("D1", downloaded_at=base))
    repo.save(_version("D2", downloaded_at=base + timedelta(days=1)))
    repo.save(_version("D3", downloaded_at=base + timedelta(days=2)))

    assert [d.dataset_id for d in repo.list_datasets()] == ["D3", "D2", "D1"]


def test_latest_returns_the_most_recent_download():
    repo = _repository()
    base = datetime(2024, 1, 1, tzinfo=timezone.utc)
    repo.save(_version("OLD", downloaded_at=base))
    repo.save(_version("NEW", downloaded_at=base + timedelta(days=1)))

    latest = repo.latest(symbol="BTC/USDT")

    assert latest is not None
    assert latest.dataset_id == "NEW"


def test_naive_stored_timestamp_is_read_as_utc():
    # A legacy or hand-edited row may lack the tz suffix; read it as UTC.
    engine = database_engine(":memory:")
    create_database(engine)
    repo = DatasetRepository(make_session_factory(engine)())
    repo.save(_version())
    with engine.begin() as connection:
        connection.execute(
            text("UPDATE datasets SET start = '2024-01-01T00:00:00'")
        )

    loaded = repo.get("BINANCE_BTCUSDT_1H_2024_V1")

    assert loaded is not None
    assert loaded.start == datetime(2024, 1, 1, tzinfo=timezone.utc)

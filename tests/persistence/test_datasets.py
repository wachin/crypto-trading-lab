"""Tests for the dataset repository (chapters 29 and 53)."""

from __future__ import annotations

from datetime import datetime, timezone

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

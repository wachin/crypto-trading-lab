"""Tests for the candle repository (chapters 8 and 28)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import text

from crypto_trading_lab.domain.models import Candle, Symbol
from crypto_trading_lab.persistence.database import (
    create_database,
    database_engine,
    make_session_factory,
)
from crypto_trading_lab.persistence.candles import CandleRepository


SYMBOL = Symbol("BTC/USDT")


def _candle(minute, close="105", interval="1m"):
    start = datetime(2024, 1, 1, tzinfo=timezone.utc) + timedelta(
        minutes=minute
    )
    close_dec = Decimal(close)
    return Candle(
        symbol=SYMBOL,
        interval=interval,
        open_time=start,
        close_time=start + timedelta(minutes=1),
        open=Decimal("100"),
        high=max(Decimal("110"), close_dec + Decimal("1")),
        low=min(Decimal("90"), close_dec - Decimal("1")),
        close=close_dec,
        volume=Decimal("10"),
    )


def _repo():
    engine = database_engine(":memory:")
    create_database(engine)
    return CandleRepository(make_session_factory(engine)())


def test_save_and_load_roundtrip():
    repo = _repo()
    repo.save_candles([_candle(0), _candle(1), _candle(2)])
    loaded = repo.load_candles(SYMBOL, "1m")
    assert len(loaded) == 3
    assert [c.open_time.minute for c in loaded] == [0, 1, 2]
    assert loaded[0].close == Decimal("105")


def test_reimport_replaces_without_duplicates():
    repo = _repo()
    repo.save_candles([_candle(0), _candle(1)])
    # Re-import with a changed close: replace must update, not duplicate.
    repo.save_candles([_candle(0, close="999"), _candle(1, close="999")])
    assert repo.count(SYMBOL, "1m") == 2
    loaded = repo.load_candles(SYMBOL, "1m")
    assert loaded[0].close == Decimal("999")


def test_reimport_without_replace_skips_existing():
    repo = _repo()
    repo.save_candles([_candle(0), _candle(1)])
    added = repo.save_candles(
        [_candle(0, close="999"), _candle(2)], replace=False
    )
    # candle(2) is new; candle(0) exists and was skipped.
    assert added == 1
    loaded = repo.load_candles(SYMBOL, "1m")
    assert len(loaded) == 3
    assert loaded[0].close == Decimal("105")  # unchanged


def test_range_queries():
    repo = _repo()
    repo.save_candles([_candle(m) for m in range(10)])
    start = datetime(2024, 1, 1, 0, 3, tzinfo=timezone.utc)
    end = datetime(2024, 1, 1, 0, 6, tzinfo=timezone.utc)
    window = repo.load_candles(SYMBOL, "1m", start=start, end=end)
    assert [c.open_time.minute for c in window] == [3, 4, 5, 6]


def test_decimal_precision_survives_roundtrip():
    repo = _repo()
    repo.save_candles([_candle(0)])
    loaded = repo.load_candles(SYMBOL, "1m")
    # Exact decimal equality — no float drift in the critical path.
    assert loaded[0].open == Decimal("100")


def test_intervals_are_isolated():
    repo = _repo()
    candle_1m = _candle(0)
    candle_5m = Candle(
        symbol=candle_1m.symbol,
        interval="5m",
        open_time=candle_1m.open_time,
        close_time=candle_1m.close_time,
        open=candle_1m.open,
        high=candle_1m.high,
        low=candle_1m.low,
        close=candle_1m.close,
        volume=candle_1m.volume,
    )
    repo.save_candles([candle_1m, candle_5m])
    assert repo.count(SYMBOL, "1m") == 1
    assert repo.count(SYMBOL, "5m") == 1


def test_replace_false_does_not_skip_another_interval():
    # Regression: the "already stored" check used to key on open_time
    # alone, so a new 5m candle was dropped when a stored 1m candle
    # shared its open_time.
    repo = _repo()
    repo.save_candles([_candle(0)])
    added = repo.save_candles(
        [_candle(0), _candle(0, interval="5m")], replace=False
    )
    assert added == 1
    assert repo.count(SYMBOL, "1m") == 1
    assert repo.count(SYMBOL, "5m") == 1


def test_save_empty_batch_writes_nothing():
    repo = _repo()
    assert repo.save_candles([]) == 0
    assert repo.load_candles(SYMBOL, "1m") == []


def test_loaded_timestamps_are_utc_aware():
    repo = _repo()
    repo.save_candles([_candle(0)])
    loaded = repo.load_candles(SYMBOL, "1m")
    assert loaded[0].open_time.tzinfo is not None
    assert loaded[0].open_time.utcoffset() == timedelta(0)


def test_count_of_unknown_market_is_zero():
    repo = _repo()
    assert repo.count(Symbol("ETH/USDT"), "1m") == 0


def test_new_exchange_is_created_on_first_write():
    repo = _repo()
    repo.save_candles([_candle(0)], exchange_name="binance")
    assert repo.count(SYMBOL, "1m", exchange_name="binance") == 1
    # Candles are scoped per exchange; the default market stays empty.
    assert repo.count(SYMBOL, "1m") == 0


def test_naive_stored_timestamp_is_read_as_utc():
    # A legacy or hand-edited row may lack the tz suffix; read it as UTC
    # rather than returning a naive datetime into the engine.
    engine = database_engine(":memory:")
    create_database(engine)
    repo = CandleRepository(make_session_factory(engine)())
    repo.save_candles([_candle(0)])
    with engine.begin() as connection:
        connection.execute(
            text("UPDATE candles SET open_time = '2024-01-01T00:00:00'")
        )
    loaded = repo.load_candles(SYMBOL, "1m")
    assert loaded[0].open_time == datetime(2024, 1, 1, tzinfo=timezone.utc)

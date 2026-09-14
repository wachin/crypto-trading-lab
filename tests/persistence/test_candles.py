"""Tests for the candle repository (chapters 8 and 28)."""

from __future__ import annotations

from decimal import Decimal

from crypto_trading_lab.domain.models import Candle, Symbol
from crypto_trading_lab.persistence.database import (
    create_database,
    database_engine,
    make_session_factory,
)
from crypto_trading_lab.persistence.candles import CandleRepository


SYMBOL = Symbol("BTC/USDT")


def _candle(minute, close="105"):
    from datetime import datetime, timedelta, timezone

    start = datetime(2024, 1, 1, tzinfo=timezone.utc) + timedelta(
        minutes=minute
    )
    close_dec = Decimal(close)
    return Candle(
        symbol=SYMBOL,
        interval="1m",
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
    from datetime import datetime, timezone

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

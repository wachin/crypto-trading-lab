"""Candle repository (ROADMAP.md chapters 8 and 28).

Persists parsed candles into SQLite with upsert semantics (importing
the same file twice must not fail with duplicates) and range queries
for charts and backtests. Timestamps are stored as canonical UTC
ISO-8601 strings (SQLite drops tzinfo on DateTime columns).
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from crypto_trading_lab.domain.models import Candle, Symbol
from crypto_trading_lab.persistence.database import (
    CandleRecord,
    ExchangeRecord,
    MarketRecord,
)

__all__ = ["CandleRepository"]


def _iso(moment: datetime) -> str:
    """Canonical UTC ISO string (sortable, tz-safe)."""
    return moment.astimezone(timezone.utc).isoformat()


def _parse(iso: str) -> datetime:
    parsed = datetime.fromisoformat(iso)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


class CandleRepository:
    """Store and query candles for one exchange/market/interval."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def _market_id(self, symbol: Symbol, exchange_name: str = "mock") -> int:
        """Find or create the exchange+market rows for ``symbol``."""
        exchange = self._session.scalar(
            select(ExchangeRecord).where(ExchangeRecord.name == exchange_name)
        )
        if exchange is None:
            exchange = ExchangeRecord(name=exchange_name)
            self._session.add(exchange)
            self._session.flush()

        market = self._session.scalar(
            select(MarketRecord).where(
                MarketRecord.exchange_id == exchange.id,
                MarketRecord.symbol == str(symbol),
            )
        )
        if market is None:
            market = MarketRecord(
                exchange_id=exchange.id,
                symbol=str(symbol),
                base=symbol.base,
                quote=symbol.quote,
                tick_size=Decimal("0.01"),
                step_size=Decimal("0.000001"),
                min_quantity=Decimal("0"),
                min_notional=Decimal("0"),
                maker_fee=Decimal("0"),
                taker_fee=Decimal("0"),
            )
            self._session.add(market)
            self._session.flush()
        return market.id

    def save_candles(
        self,
        candles: list[Candle],
        *,
        exchange_name: str = "mock",
        replace: bool = True,
    ) -> int:
        """Persist candles; returns the number of rows affected.

        ``replace=True`` re-imports cleanly (OR REPLACE on the unique
        key); ``replace=False`` skips candles that already exist.
        """
        if not candles:
            return 0
        first = candles[0]
        market_id = self._market_id(first.symbol, exchange_name)

        existing: set[datetime] = set()
        if not replace:
            rows = self._session.execute(
                select(CandleRecord.open_time).where(
                    CandleRecord.market_id == market_id,
                    CandleRecord.interval == first.interval,
                )
            ).scalars()
            existing = {_parse(value) for value in rows}
        added = 0
        for candle in candles:
            if not replace and candle.open_time in existing:
                continue  # chapter 28: skip rows that already exist
            open_iso = _iso(candle.open_time)
            existing_record = self._session.scalar(
                select(CandleRecord).where(
                    CandleRecord.market_id == market_id,
                    CandleRecord.interval == candle.interval,
                    CandleRecord.open_time == open_iso,
                )
            )
            if existing_record is not None:
                # Upsert: update values in place (re-import is safe).
                existing_record.close_time = _iso(candle.close_time)
                existing_record.open = candle.open
                existing_record.high = candle.high
                existing_record.low = candle.low
                existing_record.close = candle.close
                existing_record.volume = candle.volume
            else:
                self._session.add(
                    CandleRecord(
                        market_id=market_id,
                        interval=candle.interval,
                        open_time=open_iso,
                        close_time=_iso(candle.close_time),
                        open=candle.open,
                        high=candle.high,
                        low=candle.low,
                        close=candle.close,
                        volume=candle.volume,
                    )
                )
            added += 1
        self._session.commit()
        return added

    def load_candles(
        self,
        symbol: Symbol,
        interval: str,
        *,
        start: datetime | None = None,
        end: datetime | None = None,
        exchange_name: str = "mock",
    ) -> list[Candle]:
        """Chronologically ordered candles in the given range."""
        market_id = self._market_id(symbol, exchange_name)
        statement = (
            select(CandleRecord)
            .where(
                CandleRecord.market_id == market_id,
                CandleRecord.interval == interval,
            )
            .order_by(CandleRecord.open_time.asc())
        )
        if start is not None:
            statement = statement.where(
                CandleRecord.open_time >= _iso(start)
            )
        if end is not None:
            statement = statement.where(CandleRecord.open_time <= _iso(end))
        records = self._session.scalars(statement).all()
        return [
            Candle(
                symbol=symbol,
                interval=record.interval,
                open_time=_parse(record.open_time),
                close_time=_parse(record.close_time),
                open=Decimal(str(record.open)),
                high=Decimal(str(record.high)),
                low=Decimal(str(record.low)),
                close=Decimal(str(record.close)),
                volume=Decimal(str(record.volume)),
            )
            for record in records
        ]

    def count(
        self,
        symbol: Symbol,
        interval: str,
        *,
        exchange_name: str = "mock",
    ) -> int:
        """Number of stored candles for the market/interval."""
        market_id = self._market_id(symbol, exchange_name)
        from sqlalchemy import func

        return int(
            self._session.scalar(
                select(func.count())
                .select_from(CandleRecord)
                .where(
                    CandleRecord.market_id == market_id,
                    CandleRecord.interval == interval,
                )
            )
        )

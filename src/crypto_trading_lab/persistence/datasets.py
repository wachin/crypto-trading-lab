"""Dataset repository (ROADMAP.md chapters 29 and 53).

Stores the identity card of every dataset: what was downloaded, when,
from where, with which checksum and how clean it was. Candles
themselves live in the ``candles`` table and are linked by
exchange + symbol + interval + period.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from crypto_trading_lab.market_data.historical import DatasetVersion
from crypto_trading_lab.persistence.database import DatasetRecord

__all__ = ["DatasetRepository"]


def _parse(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


class DatasetRepository:
    """Store and query dataset identity cards."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def save(self, version: DatasetVersion) -> DatasetVersion:
        """Insert or update a dataset identity card."""
        record = self._session.get(DatasetRecord, version.dataset_id)
        if record is None:
            record = DatasetRecord(dataset_id=version.dataset_id)
            self._session.add(record)
        record.exchange = version.exchange
        record.symbol = version.symbol
        record.interval = version.interval
        record.start = version.start.isoformat()
        record.end = version.end.isoformat()
        record.candle_count = version.candle_count
        record.missing = version.missing
        record.duplicates = version.duplicates
        record.invalid = version.invalid
        record.checksum = version.checksum
        record.source = version.source
        record.timezone_name = version.timezone_name
        record.version = version.version
        record.ready = version.ready
        record.downloaded_at = version.downloaded_at.isoformat()
        self._session.commit()
        return version

    def get(self, dataset_id: str) -> DatasetVersion | None:
        """Fetch one dataset by its identity."""
        record = self._session.get(DatasetRecord, dataset_id)
        return _to_version(record) if record is not None else None

    def list_datasets(
        self,
        *,
        symbol: str | None = None,
        interval: str | None = None,
    ) -> list[DatasetVersion]:
        """All datasets, newest first, optionally filtered."""
        statement = select(DatasetRecord).order_by(
            DatasetRecord.downloaded_at.desc()
        )
        if symbol is not None:
            statement = statement.where(DatasetRecord.symbol == symbol)
        if interval is not None:
            statement = statement.where(DatasetRecord.interval == interval)
        return [
            _to_version(record)
            for record in self._session.scalars(statement).all()
        ]

    def latest(
        self,
        *,
        symbol: str | None = None,
        interval: str | None = None,
    ) -> DatasetVersion | None:
        """Most recently downloaded dataset matching the filters."""
        datasets = self.list_datasets(symbol=symbol, interval=interval)
        return datasets[0] if datasets else None

    def delete(self, dataset_id: str) -> bool:
        """Remove a dataset *identity* (the candles are left untouched)."""
        record = self._session.get(DatasetRecord, dataset_id)
        if record is None:
            return False
        self._session.delete(record)
        self._session.commit()
        return True


def _to_version(record: DatasetRecord) -> DatasetVersion:
    return DatasetVersion(
        dataset_id=record.dataset_id,
        exchange=record.exchange,
        symbol=record.symbol,
        interval=record.interval,
        start=_parse(record.start),
        end=_parse(record.end),
        candle_count=record.candle_count,
        missing=record.missing,
        duplicates=record.duplicates,
        invalid=record.invalid,
        checksum=record.checksum,
        source=record.source,
        downloaded_at=_parse(record.downloaded_at),
        timezone_name=record.timezone_name,
        version=record.version,
        ready=record.ready,
    )

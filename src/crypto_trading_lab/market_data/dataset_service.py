"""Download-and-store orchestration for datasets (chapters 28, 29 and 53).

One function, used by both the GUI and the CLI, so a dataset downloaded
from either place is identical: candles persisted, identity card
stored, checksum recorded.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from crypto_trading_lab.configuration.xdg import AppPaths
from crypto_trading_lab.domain.models import Candle
from crypto_trading_lab.market_data.historical import (
    BinanceKlinesSource,
    DatasetValidation,
    DatasetVersion,
    HistoricalRequest,
    download_dataset,
)
from crypto_trading_lab.persistence.candles import CandleRepository
from crypto_trading_lab.persistence.database import (
    create_database,
    database_engine,
    make_session_factory,
)
from crypto_trading_lab.persistence.datasets import DatasetRepository

__all__ = ["DownloadOutcome", "download_and_store"]


@dataclass
class DownloadOutcome:
    """Everything the UI/CLI needs to report a download honestly."""

    request: HistoricalRequest
    candles: list[Candle]
    version: DatasetVersion
    validation: DatasetValidation
    saved: bool
    message: str

    @property
    def ok(self) -> bool:
        return self.saved and self.version.ready


def download_and_store(
    request: HistoricalRequest,
    *,
    source: BinanceKlinesSource | None = None,
    paths: AppPaths | None = None,
    progress: Callable[[int], None] | None = None,
) -> DownloadOutcome:
    """Download ``request``, validate it, and persist it.

    Validation failure is *not* hidden: the dataset is still saved (so
    the user can inspect it) but its identity card is marked
    ``ready=False`` and the message says why. Nothing is written when
    the download itself fails.
    """
    candles, version, validation = download_dataset(
        request, source=source, progress=progress
    )

    paths = paths or AppPaths()
    engine = database_engine(paths.database_file)
    create_database(engine)
    session = make_session_factory(engine)()
    try:
        CandleRepository(session).save_candles(
            candles, exchange_name=request.exchange
        )
        DatasetRepository(session).save(version)
    finally:
        session.close()
        engine.dispose()

    if version.ready:
        message = (
            f"Saved dataset {version.dataset_id} "
            f"({version.candle_count} candles)."
        )
    else:
        message = (
            f"Saved dataset {version.dataset_id} but it is NOT ready "
            "for research:\n" + validation.beginner_explanation()
        )
    return DownloadOutcome(
        request=request,
        candles=candles,
        version=version,
        validation=validation,
        saved=True,
        message=message,
    )

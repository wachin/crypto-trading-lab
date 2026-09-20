"""Historical market data acquisition and dataset identity (chapters 26-29, 53).

This module turns "I want to research BTC/USDT" into a *dataset*: a
downloaded, validated, checksummed, identified slice of history. It
exists because a backtest that says only "BTC/USDT" is not
reproducible: six months later the exchange may serve different
candles (chapter 53.2 requires a checksum per dataset).

Design constraints:

* **No new dependencies.** The Binance Spot public REST endpoint is
  called with :mod:`urllib` from the standard library. HTTP
  ``urllib`` and JSON parsing are enough for public klines.
* **No network in tests.** The transport is injectable
  (:class:`BinanceKlinesSource` takes an ``opener``); production uses
  the real endpoint, tests use a fake page source.
* **Public data only.** The klines endpoint needs no API key and the
  code never sends credentials anywhere.
"""

from __future__ import annotations

import hashlib
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from typing import Callable, Iterable, Sequence

from crypto_trading_lab.domain.models import Candle, Symbol

__all__ = [
    "TIMEFRAMES",
    "SUPPORTED_INTERVALS",
    "DEFAULT_BINANCE_BASE_URL",
    "HistoricalDataError",
    "HistoricalRequest",
    "BinanceKlinesSource",
    "DatasetValidation",
    "validate_candles",
    "compute_dataset_checksum",
    "build_dataset_id",
    "DatasetVersion",
    "download_dataset",
]


#: Binance Spot interval → duration in seconds.
TIMEFRAMES: dict[str, int] = {
    "1m": 60,
    "5m": 5 * 60,
    "15m": 15 * 60,
    "1h": 60 * 60,
    "4h": 4 * 60 * 60,
    "1d": 24 * 60 * 60,
}

SUPPORTED_INTERVALS: tuple[str, ...] = tuple(TIMEFRAMES)

DEFAULT_BINANCE_BASE_URL = "https://api.binance.com"

#: Binance caps one klines request at 1000 candles.
BINANCE_PAGE_LIMIT = 1000

#: Hard stop so a mistaken date range cannot download forever.
MAX_CANDLES_PER_DOWNLOAD = 2_000_000


class HistoricalDataError(RuntimeError):
    """A download failed in a way the user must be told about."""

    def beginner_explanation(self) -> str:
        """Plain-language explanation for the UI (chapter 30 spirit)."""
        return (
            "The historical data could not be downloaded. The most "
            "common causes are: no internet connection, the exchange "
            "is temporarily unavailable, the requested period is "
            "outside the exchange's history, or the symbol/timeframe "
            "combination does not exist. Nothing was saved, so you can "
            "safely try again. Details: " + str(self)
        )


def _utc(moment: datetime) -> datetime:
    if moment.tzinfo is None:
        raise TypeError(
            "historical requests must use timezone-aware UTC datetimes"
        )
    return moment.astimezone(timezone.utc)


@dataclass(frozen=True)
class HistoricalRequest:
    """What the user asked to download."""

    exchange: str
    symbol: str
    interval: str
    start: datetime
    end: datetime

    def __post_init__(self) -> None:
        _utc(self.start)
        _utc(self.end)
        if self.start >= self.end:
            raise ValueError("start must be earlier than end")
        if self.interval not in TIMEFRAMES:
            raise ValueError(
                f"unsupported interval {self.interval!r}; "
                f"choose one of {', '.join(SUPPORTED_INTERVALS)}"
            )
        # Validates BASE/QUOTE form.
        Symbol(self.symbol)

    @property
    def binance_symbol(self) -> str:
        """``BTC/USDT`` → ``BTCUSDT`` (the REST symbol form)."""
        return str(Symbol(self.symbol)).replace("/", "")


class BinanceKlinesSource:
    """Public Binance Spot klines reader (chapters 26.2, 28).

    ``opener`` is injectable: it receives a URL and returns decoded
    JSON. Tests pass a fake so the suite never touches the network.
    """

    def __init__(
        self,
        base_url: str = DEFAULT_BINANCE_BASE_URL,
        timeout: float = 20.0,
        opener: Callable[[str], object] | None = None,
        pause_seconds: float = 0.05,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._opener = opener or self._urllib_opener
        self._pause_seconds = pause_seconds

    # -- transport -------------------------------------------------------

    def _urllib_opener(self, url: str) -> object:
        request = urllib.request.Request(
            url,
            headers={
                # A descriptive agent is polite and helps the exchange
                # operator understand the traffic.
                "User-Agent": "CryptoTradingLab/1.0 (research; public data)"
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                payload = response.read()
        except urllib.error.HTTPError as error:
            raise HistoricalDataError(
                f"HTTP {error.code} from the exchange: {error.reason}"
            ) from error
        except urllib.error.URLError as error:
            raise HistoricalDataError(
                f"network error contacting the exchange: {error.reason}"
            ) from error
        try:
            return json.loads(payload.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise HistoricalDataError(
                f"unreadable response from the exchange: {error}"
            ) from error

    def _fetch_page(
        self,
        request: HistoricalRequest,
        start_ms: int,
        end_ms: int,
    ) -> list[list[object]]:
        query = urllib.parse.urlencode(
            {
                "symbol": request.binance_symbol,
                "interval": request.interval,
                "startTime": start_ms,
                "endTime": end_ms,
                "limit": BINANCE_PAGE_LIMIT,
            }
        )
        url = f"{self.base_url}/api/v3/klines?{query}"
        payload = self._opener(url)
        if not isinstance(payload, list):
            raise HistoricalDataError(
                "the exchange returned an unexpected payload"
            )
        return payload

    # -- public API ------------------------------------------------------

    def fetch(
        self,
        request: HistoricalRequest,
        *,
        max_candles: int = MAX_CANDLES_PER_DOWNLOAD,
        progress: Callable[[int], None] | None = None,
    ) -> list[Candle]:
        """Download candles for ``request`` in chronological order.

        Pages forward from ``start`` and stops on the first empty page,
        when ``end`` is reached, or when ``max_candles`` is exceeded
        (a safety valve, not a target).
        """
        start = _utc(request.start)
        end = _utc(request.end)
        cursor = start
        candles: list[Candle] = []
        seen: set[datetime] = set()

        while cursor < end:
            page = self._fetch_page(
                request, _to_millis(cursor), _to_millis(end)
            )
            if not page:
                break
            added_this_page = 0
            last_open = cursor
            for row in page:
                candle = _candle_from_kline(row, request)
                if candle.open_time < start or candle.open_time > end:
                    continue
                last_open = candle.open_time
                if candle.open_time in seen:
                    continue
                seen.add(candle.open_time)
                candles.append(candle)
                added_this_page += 1
                if len(candles) > max_candles:
                    raise HistoricalDataError(
                        f"refusing to download more than {max_candles} "
                        "candles; narrow the period or raise the limit "
                        "deliberately"
                    )
            if progress is not None:
                progress(len(candles))
            # Advance past the last candle of the page.
            next_cursor = last_open + timedelta(
                seconds=TIMEFRAMES[request.interval]
            )
            if next_cursor <= cursor:
                break
            cursor = next_cursor
            if len(page) < BINANCE_PAGE_LIMIT:
                break
            if self._pause_seconds:
                time.sleep(self._pause_seconds)

        candles.sort(key=lambda c: c.open_time)
        return candles


def _to_millis(moment: datetime) -> int:
    return int(moment.timestamp() * 1000)


def _candle_from_kline(row: Sequence[object], request: HistoricalRequest) -> Candle:
    """Convert one Binance kline row into the domain ``Candle``."""
    try:
        open_time = datetime.fromtimestamp(int(row[0]) / 1000, tz=timezone.utc)
        close_time = datetime.fromtimestamp(int(row[6]) / 1000, tz=timezone.utc)
        return Candle(
            symbol=Symbol(request.symbol),
            interval=request.interval,
            open_time=open_time,
            close_time=close_time,
            open=Decimal(str(row[1])),
            high=Decimal(str(row[2])),
            low=Decimal(str(row[3])),
            close=Decimal(str(row[4])),
            volume=Decimal(str(row[5])),
        )
    except (IndexError, TypeError, ValueError, InvalidOperation) as error:
        raise HistoricalDataError(
            f"malformed candle row from the exchange: {error}"
        ) from error


@dataclass(frozen=True)
class DatasetValidation:
    """Quality report for a downloaded/imported candle series (chapter 29)."""

    candle_count: int
    first_open: datetime | None
    last_close: datetime | None
    missing: int
    duplicates: int
    invalid: int
    issues: tuple[str, ...] = ()

    @property
    def ok(self) -> bool:
        """Ready for research when nothing structural is wrong."""
        return (
            self.candle_count > 0
            and self.duplicates == 0
            and self.invalid == 0
            and self.missing == 0
        )

    def beginner_explanation(self) -> str:
        """Plain-language summary for the data screen (chapter 29)."""
        if self.candle_count == 0:
            return (
                "No candles were found for this market and period. "
                "Check the symbol, the timeframe and the dates."
            )
        lines = [
            f"Candles: {self.candle_count}",
            f"Missing candles: {self.missing}",
            f"Duplicates: {self.duplicates}",
            f"Invalid candles: {self.invalid}",
        ]
        if self.ok:
            lines.append("Status: ready for research.")
        else:
            lines.append(
                "Status: NOT ready — fix the issues below before "
                "trusting any result built on this data."
            )
            lines.extend(f"  - {issue}" for issue in self.issues)
        return "\n".join(lines)


def validate_candles(
    candles: Sequence[Candle],
    interval: str,
    *,
    invalid: int = 0,
) -> DatasetValidation:
    """Check a candle series for gaps, duplicates and bad values.

    ``Candle`` refuses to exist with impossible values, so ``invalid``
    is passed by the downloader as the count of raw rows it rejected
    before construction (a real, measurable number rather than a guess).
    """
    if interval not in TIMEFRAMES:
        raise ValueError(f"unsupported interval {interval!r}")
    if not candles:
        return DatasetValidation(0, None, None, 0, 0, invalid)

    step = timedelta(seconds=TIMEFRAMES[interval])
    ordered = sorted(candles, key=lambda c: c.open_time)
    duplicates = 0
    missing = 0
    issues: list[str] = []

    previous: datetime | None = None
    for candle in ordered:
        if previous is not None:
            delta = candle.open_time - previous
            if delta == timedelta(0):
                duplicates += 1
            elif delta > step:
                gap = int(delta / step) - 1
                if gap > 0:
                    missing += gap
            elif delta < step:
                issues.append(
                    "candles overlap or are out of order around "
                    f"{candle.open_time.isoformat()}"
                )
        previous = candle.open_time

    # Timestamp regularity: a candle must open on the interval grid.
    for candle in ordered:
        if int(candle.open_time.timestamp()) % TIMEFRAMES[interval] != 0:
            issues.append(
                f"candle at {candle.open_time.isoformat()} is not "
                "aligned with the timeframe grid"
            )
            break

    if duplicates:
        issues.append(f"{duplicates} duplicate timestamps")
    if missing:
        issues.append(
            f"{missing} missing candles (exchange downtime or a gap "
            "in the market's history)"
        )
    if invalid:
        issues.append(f"{invalid} invalid rows were discarded")

    return DatasetValidation(
        candle_count=len(ordered),
        first_open=ordered[0].open_time,
        last_close=ordered[-1].close_time,
        missing=missing,
        duplicates=duplicates,
        invalid=invalid,
        issues=tuple(issues),
    )


def compute_dataset_checksum(candles: Iterable[Candle]) -> str:
    """Stable SHA-256 over the canonical candle rows (chapter 53.2).

    Two datasets with identical candles produce the identical
    checksum regardless of download time or row ordering.
    """
    digest = hashlib.sha256()
    for candle in sorted(candles, key=lambda c: c.open_time):
        digest.update(
            "|".join(
                [
                    candle.open_time.astimezone(timezone.utc).isoformat(),
                    candle.close_time.astimezone(timezone.utc).isoformat(),
                    format(candle.open, "f"),
                    format(candle.high, "f"),
                    format(candle.low, "f"),
                    format(candle.close, "f"),
                    format(candle.volume, "f"),
                ]
            ).encode("utf-8")
        )
        digest.update(b"\n")
    return digest.hexdigest()


def build_dataset_id(
    exchange: str,
    symbol: str,
    interval: str,
    start: datetime,
    end: datetime,
    version: int = 1,
) -> str:
    """Human-readable, stable dataset identity (chapter 29/53).

    Example: ``BINANCE_BTCUSDT_1H_2020-01-01_2026-09-01_V1``.
    """
    return "_".join(
        [
            exchange.upper(),
            str(Symbol(symbol)).replace("/", ""),
            interval.upper(),
            _utc(start).strftime("%Y-%m-%d"),
            _utc(end).strftime("%Y-%m-%d"),
            f"V{version}",
        ]
    )


@dataclass(frozen=True)
class DatasetVersion:
    """Immutable identity card of one stored dataset (chapters 29/53)."""

    dataset_id: str
    exchange: str
    symbol: str
    interval: str
    start: datetime
    end: datetime
    candle_count: int
    missing: int
    duplicates: int
    invalid: int
    checksum: str
    source: str
    downloaded_at: datetime
    timezone_name: str = "UTC"
    version: int = 1
    ready: bool = True

    def to_dict(self) -> dict[str, object]:
        return {
            "dataset_id": self.dataset_id,
            "exchange": self.exchange,
            "symbol": self.symbol,
            "interval": self.interval,
            "start": self.start.isoformat(),
            "end": self.end.isoformat(),
            "candle_count": self.candle_count,
            "missing": self.missing,
            "duplicates": self.duplicates,
            "invalid": self.invalid,
            "checksum": self.checksum,
            "source": self.source,
            "downloaded_at": self.downloaded_at.isoformat(),
            "timezone": self.timezone_name,
            "version": self.version,
            "ready": self.ready,
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> "DatasetVersion":
        def _dt(key: str) -> datetime:
            value = data[key]
            assert isinstance(value, str)
            parsed = datetime.fromisoformat(value)
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return parsed

        return cls(
            dataset_id=str(data["dataset_id"]),
            exchange=str(data["exchange"]),
            symbol=str(data["symbol"]),
            interval=str(data["interval"]),
            start=_dt("start"),
            end=_dt("end"),
            candle_count=int(data["candle_count"]),  # type: ignore[arg-type]
            missing=int(data.get("missing", 0)),  # type: ignore[arg-type]
            duplicates=int(data.get("duplicates", 0)),  # type: ignore[arg-type]
            invalid=int(data.get("invalid", 0)),  # type: ignore[arg-type]
            checksum=str(data["checksum"]),
            source=str(data.get("source", "")),
            downloaded_at=_dt("downloaded_at"),
            timezone_name=str(data.get("timezone", "UTC")),
            version=int(data.get("version", 1)),  # type: ignore[arg-type]
            ready=bool(data.get("ready", True)),
        )

    def beginner_explanation(self) -> str:
        """Plain-language identity card for the data screen."""
        return "\n".join(
            [
                f"Dataset: {self.dataset_id}",
                f"Exchange: {self.exchange}",
                f"Symbol: {self.symbol}",
                f"Timeframe: {self.interval}",
                f"First candle: {self.start.isoformat()}",
                f"Last candle: {self.end.isoformat()}",
                f"Number of candles: {self.candle_count}",
                f"Missing: {self.missing}",
                f"Duplicates: {self.duplicates}",
                f"Timezone: {self.timezone_name}",
                f"Downloaded: {self.downloaded_at.isoformat()}",
                f"Source: {self.source}",
                f"Checksum: {self.checksum[:16]}…",
                "Status: "
                + ("ready for research" if self.ready else "NOT ready"),
            ]
        )


def download_dataset(
    request: HistoricalRequest,
    *,
    source: BinanceKlinesSource | None = None,
    progress: Callable[[int], None] | None = None,
) -> tuple[list[Candle], DatasetVersion, DatasetValidation]:
    """Download, validate and identify a dataset in one call.

    Returns ``(candles, dataset_version, validation)``. The caller
    decides whether to persist; nothing is written here, so a failed
    download never leaves a half-saved dataset behind.
    """
    source = source or BinanceKlinesSource()
    candles = source.fetch(request, progress=progress)
    validation = validate_candles(candles, request.interval)
    version = DatasetVersion(
        dataset_id=build_dataset_id(
            request.exchange,
            request.symbol,
            request.interval,
            request.start,
            request.end,
        ),
        exchange=request.exchange,
        symbol=str(Symbol(request.symbol)),
        interval=request.interval,
        start=request.start.astimezone(timezone.utc),
        end=request.end.astimezone(timezone.utc),
        candle_count=validation.candle_count,
        missing=validation.missing,
        duplicates=validation.duplicates,
        invalid=validation.invalid,
        checksum=compute_dataset_checksum(candles),
        source=f"binance-spot-rest:{source.base_url}",
        downloaded_at=datetime.now(timezone.utc),
        ready=validation.ok,
    )
    return candles, version, validation

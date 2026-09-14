"""CSV candle import with full validation (ROADMAP.md chapter 28).

Reads OHLCV CSV files, maps columns (timestamp/open/high/low/close/
volume/symbol/interval), and validates everything the chapter
requires: duplicate and unordered timestamps, irregular intervals,
negative values, high/low consistency, missing values, unknown
timezones, and unrecognized columns. A summary is produced before any
database write, and every error carries a beginner-readable
explanation.
"""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Sequence

from crypto_trading_lab.domain.models import Candle, Symbol, utc_now

__all__ = [
    "REQUIRED_COLUMNS",
    "COLUMN_ALIASES",
    "ImportError_",
    "ImportSummary",
    "CandleParser",
    "parse_csv",
    "detect_interval",
]


#: Column aliases so common CSV layouts map without configuration.
COLUMN_ALIASES: dict[str, tuple[str, ...]] = {
    "timestamp": ("timestamp", "time", "date", "datetime", "open_time", "date_time"),
    "open": ("open", "o"),
    "high": ("high", "h"),
    "low": ("low", "l"),
    "close": ("close", "c"),
    "volume": ("volume", "vol", "v"),
    "symbol": ("symbol", "pair"),
    "interval": ("interval", "timeframe", "period", "resolution"),
}

REQUIRED_COLUMNS = ("timestamp", "open", "high", "low", "close", "volume")

#: Interval string -> approximate timedelta, for regularity checks.
INTERVAL_DELTAS: dict[str, timedelta] = {
    "1m": timedelta(minutes=1),
    "5m": timedelta(minutes=5),
    "15m": timedelta(minutes=15),
    "30m": timedelta(minutes=30),
    "1h": timedelta(hours=1),
    "4h": timedelta(hours=4),
    "1d": timedelta(days=1),
    "1w": timedelta(weeks=1),
}


class ImportError_(ValueError):
    """A CSV import problem with a beginner-readable explanation."""

    def __init__(self, line: int, reason: str) -> None:
        self.line = line
        self.reason = reason
        super().__init__(f"line {line}: {reason}")

    def __str__(self) -> str:
        return f"line {self.line}: {self.reason}"


@dataclass
class ImportSummary:
    """Pre-import summary shown to the user (chapter 28)."""

    rows_read: int = 0
    rows_valid: int = 0
    errors: list[ImportError_] = None  # type: ignore[assignment]
    symbol: str = ""
    interval: str = ""
    first_time: datetime | None = None
    last_time: datetime | None = None
    candles: list[Candle] = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if self.errors is None:
            self.errors = []
        if self.candles is None:
            self.candles = []

    @property
    def ok(self) -> bool:
        return self.rows_valid > 0 and not self.errors

    def beginner_explanation(self) -> str:
        """Plain-language summary for the pre-import dialog."""
        if self.errors:
            first = self.errors[0]
            return (
                f"The file has problems: {len(self.errors)} row(s) could "
                f"not be read. First problem: {first}. Fix the file and "
                "try again, or import only the valid rows."
            )
        return (
            f"Ready to import {self.rows_valid} candles for "
            f"{self.symbol} on the {self.interval} interval, covering "
            f"{self.first_time} to {self.last_time}. Nothing has been "
            "saved yet — confirm to continue."
        )


def _normalize_header(name: str) -> str:
    return name.strip().lower().replace(" ", "_").replace("-", "_")


def _map_columns(header: Sequence[str], line: int) -> dict[str, str]:
    """Map CSV header names to canonical columns (chapter 28 wizard)."""
    mapping: dict[str, str] = {}
    unknown: list[str] = []
    for name in header:
        key = _normalize_header(name)
        matched = False
        for canonical, aliases in COLUMN_ALIASES.items():
            if key in aliases and canonical not in mapping:
                mapping[canonical] = name
                matched = True
                break
        if not matched:
            unknown.append(name)
    for required in REQUIRED_COLUMNS:
        if required not in mapping:
            raise ImportError_(
                line,
                f"could not find the '{required}' column. "
                f"Columns found: {', '.join(header)}",
            )
    if unknown:
        raise ImportError_(
            line,
            f"unrecognized column(s): {', '.join(unknown)}. "
            "Rename them (timestamp, open, high, low, close, volume) "
            "or remove them.",
        )
    return mapping


def _parse_timestamp(raw: str, line: int) -> datetime:
    """Parse ISO timestamps, epoch seconds, or epoch milliseconds."""
    text = raw.strip()
    if not text:
        raise ImportError_(line, "timestamp is empty")
    # Epoch seconds / milliseconds (pure digits).
    if text.isdigit():
        number = int(text)
        # Heuristic: 10 digits = seconds, 13 = milliseconds.
        if number > 10**12:
            number //= 1000
        return datetime.fromtimestamp(number, tz=timezone.utc)
    # ISO with 'Z' shorthand.
    normalized = text[:-1] + "+00:00" if text.endswith("Z") else text
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise ImportError_(
            line,
            f"could not understand the timestamp '{raw}'. "
            "Use ISO format (2024-01-15T00:00:00+00:00) or epoch seconds.",
        ) from exc
    if parsed.tzinfo is None:
        # Chapter 28: "unknown timezone" — naive timestamps are rejected.
        raise ImportError_(
            line,
            f"the timestamp '{raw}' has no timezone. Add '+00:00' for UTC "
            "or the timezone you want.",
        )
    return parsed.astimezone(timezone.utc)


def _parse_decimal(raw: str, column: str, line: int) -> Decimal:
    text = raw.strip()
    if text == "":
        raise ImportError_(line, f"{column} value is missing")
    try:
        value = Decimal(text)
    except InvalidOperation as exc:
        raise ImportError_(
            line, f"the {column} value '{raw}' is not a number"
        ) from exc
    if value < 0:
        raise ImportError_(
            line, f"the {column} value '{raw}' is negative — prices and "
            "volumes cannot be negative"
        )
    return value


def detect_interval(times: Sequence[datetime]) -> str | None:
    """Infer the interval from the most common gap between candles."""
    if len(times) < 2:
        return None
    deltas: dict[str, int] = {}
    previous = times[0]
    for current in times[1:]:
        gap = current - previous
        for name, delta in INTERVAL_DELTAS.items():
            if gap == delta:
                deltas[name] = deltas.get(name, 0) + 1
        previous = current
    if not deltas:
        return None
    return max(deltas, key=deltas.get)


def parse_csv(
    content: str | bytes | Path,
    *,
    symbol_default: str = "BTC/USDT",
    interval_default: str = "1m",
    max_errors: int = 100,
) -> ImportSummary:
    """Parse and validate a CSV of candles (chapter 28).

    Returns an :class:`ImportSummary` with candles ready to persist and
    a beginner explanation; nothing is written to the database until
    the caller confirms.
    """
    if isinstance(content, Path):
        content = content.read_text(encoding="utf-8-sig")
    elif isinstance(content, bytes):
        content = content.decode("utf-8-sig")

    summary = ImportSummary()
    reader = csv.reader(io.StringIO(content))
    try:
        header = next(reader)
    except StopIteration as exc:
        raise ImportError_(1, "the file is empty") from exc

    try:
        mapping = _map_columns(header, 1)
    except ImportError_ as exc:
        summary.errors.append(exc)
        return summary

    times: list[datetime] = []
    seen_times: set[datetime] = set()
    for line_number, row in enumerate(reader, start=2):
        if not row or all(not cell.strip() for cell in row):
            continue
        summary.rows_read += 1
        if len(summary.errors) >= max_errors:
            summary.errors.append(
                ImportError_(line_number, "too many errors; import stopped")
            )
            break

        position = {
            canonical: header.index(mapping[canonical])
            for canonical in REQUIRED_COLUMNS
        }
        try:
            timestamp = _parse_timestamp(
                row[position["timestamp"]], line_number
            )
            open_ = _parse_decimal(row[position["open"]], "open", line_number)
            high = _parse_decimal(row[position["high"]], "high", line_number)
            low = _parse_decimal(row[position["low"]], "low", line_number)
            close = _parse_decimal(row[position["close"]], "close", line_number)
            volume = _parse_decimal(row[position["volume"]], "volume", line_number)
        except IndexError:
            summary.errors.append(
                ImportError_(line_number, "the row has fewer columns than the header")
            )
            continue
        except ImportError_ as error:
            summary.errors.append(error)
            continue

        # Cross-field validation (chapter 28).
        if timestamp in seen_times:
            summary.errors.append(
                ImportError_(
                    line_number,
                    f"duplicate timestamp {timestamp.isoformat()} — "
                    "each candle must appear only once",
                )
            )
            continue
        if high < low:
            summary.errors.append(
                ImportError_(
                    line_number,
                    f"high ({high}) is below low ({low}) — that is impossible",
                )
            )
            continue
        if not (low <= open_ <= high):
            summary.errors.append(
                ImportError_(
                    line_number,
                    f"open ({open_}) is outside the high-low range "
                    f"({low} to {high})",
                )
            )
            continue
        if not (low <= close <= high):
            summary.errors.append(
                ImportError_(
                    line_number,
                    f"close ({close}) is outside the high-low range "
                    f"({low} to {high})",
                )
            )
            continue

        seen_times.add(timestamp)
        times.append(timestamp)
        symbol = Symbol(symbol_default)
        interval = interval_default
        delta = INTERVAL_DELTAS.get(interval)
        if delta is None:
            summary.errors.append(
                ImportError_(
                    line_number,
                    f"unknown interval '{interval}' — use one of: "
                    + ", ".join(sorted(INTERVAL_DELTAS)),
                )
            )
            continue
        candle = Candle(
            symbol=symbol,
            interval=interval,
            open_time=timestamp,
            close_time=timestamp + delta,
            open=open_,
            high=high,
            low=low,
            close=close,
            volume=volume,
        )
        summary.candles.append(candle)
        summary.rows_valid += 1
        if summary.first_time is None or timestamp < summary.first_time:
            summary.first_time = timestamp
        if summary.last_time is None or timestamp > summary.last_time:
            summary.last_time = timestamp

    summary.symbol = symbol_default
    summary.interval = interval_default

    # Chronology validation (chapter 28): unordered timestamps.
    if times != sorted(times):
        summary.errors.append(
            ImportError_(
                1,
                "timestamps are out of order — candles must be sorted "
                "oldest to newest",
            )
        )
    # Interval regularity (chapter 28): irregular intervals.
    detected = detect_interval(times)
    if detected is not None and detected != interval_default:
        summary.errors.append(
            ImportError_(
                1,
                f"the file looks like {detected} candles but was declared "
                f"as {interval_default}",
            )
        )

    return summary

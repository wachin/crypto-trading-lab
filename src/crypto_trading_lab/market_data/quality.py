"""Data quality validation and reporting (ROADMAP.md Chapter 29).

Centralizes validation of *historical* datasets (ROADMAP ch. 29 extended). Reuses
:func:`crypto_trading_lab.market_data.historical.validate_candles`
for the mechanical checks (gaps, duplicates, grid alignment) and adds
the Chapter 29 requirements that module does not cover:

- a serializable, per-dataset quality report;
- a deterministic stale/frozen rule for datasets at rest (distinct
  from the real-time ``StaleDataDetector`` used by live feeds);
- deterministic volume-anomaly detection;
- a clear distinction between warnings (dataset stores but is marked)
  and errors (dataset must not be trusted as research input).

No real-time state, no machine learning, no silent data repairs.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Any, Optional, Sequence

from crypto_trading_lab.domain.models import Candle
from crypto_trading_lab.market_data.historical import (
    TIMEFRAMES,
    DatasetValidation,
    validate_candles,
)

__all__ = [
    "DataQualityError",
    "DataQualityWarning",
    "QualityIssueSeverity",
    "QualityIssue",
    "VolumeAnomaly",
    "DataQualityReport",
    "DataQualityValidator",
    "validate_dataset_quality",
    "create_quality_report",
    "DatasetProvenance",
    "SurvivorshipBiasNote",
    "record_survivorship_bias",
    "BarType",
    "BarConstructionInfo",
    "build_volume_bars",
    "build_dollar_bars",
    "build_imbalance_bars",
]

#: Default factor beyond which a structural shift in traded volume
#: (median of the first half vs the second half of a dataset) is flagged
#: as a liquidity change rather than an ordinary spike.
DEFAULT_LIQUIDITY_CHANGE_RATIO = Decimal("5")

#: Default factor above/below which a candle's volume is suspicious
#: relative to the rolling median of its recent neighbours.
DEFAULT_VOLUME_ANOMALY_RATIO = Decimal("3")

#: Default rolling window (in candles) for the volume baseline.
DEFAULT_VOLUME_WINDOW = 20

#: Tolerance before the last candle is considered stale: the dataset's
#: last close must be older than ``stale_intervals * interval`` before
#: ``expected_end_time`` for the STALE_DATASET warning to fire.
DEFAULT_STALE_INTERVALS = 1.5


class DataQualityError(Exception):
    """Raised when a dataset cannot be accepted due to quality errors."""


class DataQualityWarning(UserWarning):
    """Warning issued for datasets that store with quality concerns."""


class QualityIssueSeverity(str, Enum):
    """Severity of a single data-quality issue.

    ``ERROR`` means the dataset must not be treated as valid input.
    ``WARNING`` means it may be stored but is flagged as problematic.
    ``INFO`` records a fact without affecting validity.
    """

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


@dataclass(frozen=True)
class QualityIssue:
    """A single data-quality issue found during validation."""

    severity: QualityIssueSeverity
    code: str
    message: str
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "severity": self.severity.value,
            "code": self.code,
            "message": self.message,
            "details": dict(self.details),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "QualityIssue":
        return cls(
            severity=QualityIssueSeverity(str(data["severity"])),
            code=str(data["code"]),
            message=str(data["message"]),
            details=dict(data.get("details") or {}),
        )


@dataclass(frozen=True)
class VolumeAnomaly:
    """A suspicious volume spike or drop on a single candle."""

    candle_index: int
    timestamp: datetime
    expected_volume: Decimal
    actual_volume: Decimal
    deviation_ratio: Decimal
    kind: str  # "spike" or "drop"

    def to_dict(self) -> dict[str, Any]:
        return {
            "candle_index": self.candle_index,
            "timestamp": self.timestamp.isoformat(),
            "expected_volume": str(self.expected_volume),
            "actual_volume": str(self.actual_volume),
            "deviation_ratio": str(self.deviation_ratio),
            "kind": self.kind,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "VolumeAnomaly":
        return cls(
            candle_index=int(data["candle_index"]),
            timestamp=datetime.fromisoformat(str(data["timestamp"])),
            expected_volume=Decimal(str(data["expected_volume"])),
            actual_volume=Decimal(str(data["actual_volume"])),
            deviation_ratio=Decimal(str(data["deviation_ratio"])),
            kind=str(data["kind"]),
        )


@dataclass(frozen=True)
class DataQualityReport:
    """Serializable, per-dataset quality report (Chapter 29)."""

    dataset_id: str
    version: int
    checksum: str
    source: str
    symbol: str
    exchange: str
    interval: str
    start_time: Optional[datetime]
    end_time: Optional[datetime]
    candle_count: int
    survivorship_bias: Optional[SurvivorshipBiasNote] = None

    missing_candles: int = 0
    duplicate_candles: int = 0
    out_of_order_count: int = 0
    invalid_ohlcv_count: int = 0

    is_stale: bool = False
    is_frozen: bool = False

    volume_anomalies: tuple[VolumeAnomaly, ...] = ()
    issues: tuple[QualityIssue, ...] = ()

    validated_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    # -- derived status --------------------------------------------------

    @property
    def has_warnings(self) -> bool:
        return any(
            i.severity is QualityIssueSeverity.WARNING for i in self.issues
        )

    @property
    def has_errors(self) -> bool:
        return any(
            i.severity is QualityIssueSeverity.ERROR for i in self.issues
        )

    @property
    def is_valid(self) -> bool:
        """True when the dataset may be used as research input."""
        return not self.has_errors

    @property
    def completeness_ratio(self) -> float:
        """Fraction of expected candles that are present (0.0 - 1.0)."""
        expected = self.candle_count + self.missing_candles
        if expected <= 0:
            return 0.0
        return self.candle_count / expected

    # -- serialization ---------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        return {
            "dataset_id": self.dataset_id,
            "version": self.version,
            "checksum": self.checksum,
            "source": self.source,
            "symbol": self.symbol,
            "exchange": self.exchange,
            "interval": self.interval,
            "start_time": (
                self.start_time.isoformat() if self.start_time else None
            ),
            "end_time": (
                self.end_time.isoformat() if self.end_time else None
            ),
            "candle_count": self.candle_count,
            "missing_candles": self.missing_candles,
            "duplicate_candles": self.duplicate_candles,
            "out_of_order_count": self.out_of_order_count,
            "invalid_ohlcv_count": self.invalid_ohlcv_count,
            "is_stale": self.is_stale,
            "is_frozen": self.is_frozen,
            "volume_anomalies": [a.to_dict() for a in self.volume_anomalies],
            "issues": [i.to_dict() for i in self.issues],
            "survivorship_bias": (
                self.survivorship_bias.to_dict()
                if self.survivorship_bias is not None
                else None
            ),
            "validated_at": self.validated_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "DataQualityReport":
        start = data.get("start_time")
        end = data.get("end_time")
        validated_at = data.get("validated_at")
        return cls(
            dataset_id=str(data["dataset_id"]),
            version=int(data.get("version", 1)),
            checksum=str(data.get("checksum", "")),
            source=str(data.get("source", "")),
            symbol=str(data["symbol"]),
            exchange=str(data["exchange"]),
            interval=str(data["interval"]),
            start_time=datetime.fromisoformat(start) if start else None,
            end_time=datetime.fromisoformat(end) if end else None,
            candle_count=int(data.get("candle_count", 0)),
            missing_candles=int(data.get("missing_candles", 0)),
            duplicate_candles=int(data.get("duplicate_candles", 0)),
            out_of_order_count=int(data.get("out_of_order_count", 0)),
            invalid_ohlcv_count=int(data.get("invalid_ohlcv_count", 0)),
            is_stale=bool(data.get("is_stale", False)),
            is_frozen=bool(data.get("is_frozen", False)),
            volume_anomalies=tuple(
                VolumeAnomaly.from_dict(a)
                for a in data.get("volume_anomalies", [])
            ),
            issues=tuple(
                QualityIssue.from_dict(i) for i in data.get("issues", [])
            ),
            survivorship_bias=(
                SurvivorshipBiasNote.from_dict(data["survivorship_bias"])
                if data.get("survivorship_bias") is not None
                else None
            ),
            validated_at=(
                datetime.fromisoformat(validated_at)
                if validated_at
                else datetime.now(timezone.utc)
            ),
        )


class DataQualityValidator:
    """Deterministic quality checker for stored historical datasets.

    Mechanical checks (gaps, duplicates, grid alignment) are delegated
    to :func:`validate_candles` from the historical-data module so the
    rules cannot drift between download and validation. This class
    adds the Chapter 29-specific checks on top.
    """

    def __init__(
        self,
        *,
        volume_window: int = DEFAULT_VOLUME_WINDOW,
        volume_anomaly_ratio: Decimal = DEFAULT_VOLUME_ANOMALY_RATIO,
        stale_intervals: float = DEFAULT_STALE_INTERVALS,
        liquidity_change_ratio: Decimal = DEFAULT_LIQUIDITY_CHANGE_RATIO,
    ) -> None:
        if volume_window < 3:
            raise ValueError("volume_window must be at least 3")
        if volume_anomaly_ratio <= 1:
            raise ValueError("volume_anomaly_ratio must be > 1")
        if stale_intervals <= 0:
            raise ValueError("stale_intervals must be positive")
        self.volume_window = volume_window
        self.volume_anomaly_ratio = volume_anomaly_ratio
        self.stale_intervals = stale_intervals
        self.liquidity_change_ratio = liquidity_change_ratio

    # -- public API ------------------------------------------------------

    def validate(
        self,
        candles: Sequence[Candle],
        *,
        symbol: str,
        exchange: str,
        interval: str,
        dataset_id: str = "",
        version: int = 1,
        checksum: str = "",
        source: str = "",
        delisted_assets: set[str] | None = None,
        survivorship_bias: SurvivorshipBiasNote | None = None,
        expected_end_time: Optional[datetime] = None,
        invalid_count: int = 0,
    ) -> DataQualityReport:
        """Run every Chapter 29 check and return a report.

        The report is a fact, not a decision: the caller decides whether
        to store the dataset (see ``DataQualityReport.is_valid``).
        """
        materialized = list(candles)
        mechanical = validate_candles(
            materialized, interval, invalid=invalid_count
        )

        issues: list[QualityIssue] = []
        self._add_mechanical_issues(mechanical, issues)
        self._add_stale_issues(
            materialized, interval, expected_end_time, issues
        )
        frozen = self._is_frozen(materialized, issues)
        check_delisted(symbol, delisted_assets, issues)
        detect_liquidity_change(materialized, self.liquidity_change_ratio, self.volume_window, issues)

        anomalies = tuple(self._detect_volume_anomalies(materialized))
        if anomalies:
            issues.append(
                QualityIssue(
                    severity=QualityIssueSeverity.WARNING,
                    code="VOLUME_ANOMALY",
                    message=(
                        f"{len(anomalies)} suspicious volume "
                        "movement(s) detected"
                    ),
                    details={
                        "count": len(anomalies),
                        "threshold_ratio": str(self.volume_anomaly_ratio),
                    },
                )
            )

        first_open = min(
            (c.open_time for c in materialized), default=None
        )
        last_close = max(
            (c.close_time for c in materialized), default=None
        )

        return DataQualityReport(
            dataset_id=dataset_id,
            version=version,
            checksum=checksum,
            source=source,
            symbol=symbol,
            exchange=exchange,
            interval=interval,
            start_time=first_open,
            end_time=last_close,
            candle_count=len(materialized),
            missing_candles=mechanical.missing,
            duplicate_candles=mechanical.duplicates,
            out_of_order_count=self._count_out_of_order(mechanical),
            invalid_ohlcv_count=mechanical.invalid,
            is_stale=any(i.code == "STALE_DATASET" for i in issues),
            is_frozen=frozen,
            volume_anomalies=anomalies,
            issues=tuple(issues),
            survivorship_bias=survivorship_bias,
        )

    # -- internals -------------------------------------------------------

    @staticmethod
    def _count_out_of_order(validation: DatasetValidation) -> int:
        return sum(
            1
            for issue in validation.issues
            if "out of order" in issue.lower()
        )

    def _add_mechanical_issues(
        self,
        validation: DatasetValidation,
        issues: list[QualityIssue],
    ) -> None:
        if validation.missing:
            issues.append(
                QualityIssue(
                    severity=QualityIssueSeverity.WARNING,
                    code="MISSING_CANDLES",
                    message=(
                        f"{validation.missing} candle(s) are missing "
                        "inside the requested range"
                    ),
                    details={"missing": validation.missing},
                )
            )
        if validation.duplicates:
            issues.append(
                QualityIssue(
                    severity=QualityIssueSeverity.WARNING,
                    code="DUPLICATE_CANDLES",
                    message=(
                        f"{validation.duplicates} duplicate timestamp(s)"
                    ),
                    details={"duplicates": validation.duplicates},
                )
            )
        if validation.invalid:
            issues.append(
                QualityIssue(
                    severity=QualityIssueSeverity.ERROR,
                    code="INVALID_OHLCV",
                    message=(
                        f"{validation.invalid} invalid OHLCV row(s) "
                        "were rejected before this report"
                    ),
                    details={"invalid": validation.invalid},
                )
            )
        for message in validation.issues:
            lowered = message.lower()
            if "out of order" in lowered:
                issues.append(
                    QualityIssue(
                        severity=QualityIssueSeverity.ERROR,
                        code="OUT_OF_ORDER",
                        message=message,
                    )
                )
            elif "not aligned with the timeframe grid" in lowered:
                issues.append(
                    QualityIssue(
                        severity=QualityIssueSeverity.WARNING,
                        code="GRID_ALIGNMENT",
                        message=message,
                    )
                )
            # Counts (missing / duplicates / invalid) are already reported
            # above with their own codes; do not relabel them here.

    def _add_stale_issues(
        self,
        candles: list[Candle],
        interval: str,
        expected_end_time: Optional[datetime],
        issues: list[QualityIssue],
    ) -> None:
        """Deterministic stale rule for a *historical* dataset.

        A dataset is stale when its last candle closes materially
        before the ``expected_end_time`` the caller asked for. If no
        ``expected_end_time`` is provided, the dataset cannot be
        compared against a target and is not flagged — silence is
        honest, guessing is not.

        This is deliberately different from the real-time
        ``StaleDataDetector`` (chapters 26/27): that one watches a
        live feed's freshness, this one watches stored history.
        """
        if expected_end_time is None or not candles:
            return
        if expected_end_time.tzinfo is None:
            raise TypeError(
                "expected_end_time must be timezone-aware (UTC)"
            )
        last_close = max(c.close_time for c in candles)
        gap = expected_end_time - last_close
        tolerance = TIMEFRAMES[interval] * self.stale_intervals
        if gap.total_seconds() > tolerance:
            issues.append(
                QualityIssue(
                    severity=QualityIssueSeverity.WARNING,
                    code="STALE_DATASET",
                    message=(
                        "the dataset ends well before the requested "
                        "period: it is stale for the requested window"
                    ),
                    details={
                        "expected_end_time": expected_end_time.isoformat(),
                        "last_close": last_close.isoformat(),
                        "gap_seconds": gap.total_seconds(),
                        "tolerance_seconds": tolerance,
                    },
                )
            )

    @staticmethod
    def _is_frozen(
        candles: list[Candle], issues: list[QualityIssue]
    ) -> bool:
        """A dataset with zero volume across every candle is frozen."""
        if not candles:
            return False
        if any(c.volume > 0 for c in candles):
            return False
        issues.append(
            QualityIssue(
                severity=QualityIssueSeverity.ERROR,
                code="FROZEN_DATASET",
                message=(
                    "every candle in this dataset has zero volume: "
                    "the market was frozen for the whole period"
                ),
            )
        )
        return True

    def _detect_volume_anomalies(
        self, candles: list[Candle]
    ) -> list[VolumeAnomaly]:
        """Rolling-median volume anomaly detection.

        A candle is flagged when its volume is more than
        ``volume_anomaly_ratio`` times, or less than the inverse, the
        median volume of the previous ``volume_window`` candles. Zero
        volumes are handled separately by :meth:`_is_frozen` and are
        not treated as anomalies here.
        """
        if len(candles) < self.volume_window + 1:
            return []
        anomalies: list[VolumeAnomaly] = []
        ratio = self.volume_anomaly_ratio
        inverse = Decimal(1) / ratio
        window = self.volume_window
        for index in range(window, len(candles)):
            history = [
                candles[i].volume for i in range(index - window, index)
            ]
            current = candles[index].volume
            if current <= 0:
                continue  # frozen data has its own issue
            baseline = _median(history)
            if baseline <= 0:
                continue
            deviation = current / baseline
            if deviation >= ratio:
                kind = "spike"
            elif deviation <= inverse:
                kind = "drop"
            else:
                continue
            anomalies.append(
                VolumeAnomaly(
                    candle_index=index,
                    timestamp=candles[index].open_time,
                    expected_volume=baseline,
                    actual_volume=current,
                    deviation_ratio=deviation,
                    kind=kind,
                )
            )
        return anomalies


    # delisted-asset and liquidity checks live in module-level functions

def _median(values: list[Decimal]) -> Decimal:
    ordered = sorted(values)
    n = len(ordered)
    middle = n // 2
    if n % 2 == 1:
        return ordered[middle]
    return (ordered[middle - 1] + ordered[middle]) / Decimal(2)


# --- convenience wrappers ---------------------------------------------


def validate_dataset_quality(
    candles: Sequence[Candle],
    *,
    symbol: str,
    exchange: str,
    interval: str,
    dataset_id: str = "",
    version: int = 1,
    checksum: str = "",
    source: str = "",
    delisted_assets: set[str] | None = None,
    survivorship_bias: SurvivorshipBiasNote | None = None,
    expected_end_time: Optional[datetime] = None,
    invalid_count: int = 0,
) -> DataQualityReport:
    """One-shot wrapper around :class:`DataQualityValidator.validate`."""
    return DataQualityValidator().validate(
        candles,
        symbol=symbol,
        exchange=exchange,
        interval=interval,
        dataset_id=dataset_id,
        version=version,
        checksum=checksum,
        source=source,
        delisted_assets=delisted_assets,
        survivorship_bias=survivorship_bias,
        expected_end_time=expected_end_time,
        invalid_count=invalid_count,
    )


def create_quality_report(
    candles: Sequence[Candle],
    *,
    dataset_id: str,
    version: int,
    checksum: str,
    source: str = "",
    delisted_assets: set[str] | None = None,
    survivorship_bias: SurvivorshipBiasNote | None = None,
    symbol: str,
    exchange: str,
    interval: str,
    invalid_count: int = 0,
) -> DataQualityReport:
    """Thin alias kept for backward compatibility with earlier callers."""
    return validate_dataset_quality(
        candles,
        symbol=symbol,
        exchange=exchange,
        interval=interval,
        dataset_id=dataset_id,
        version=version,
        checksum=checksum,
        source=source,
        delisted_assets=delisted_assets,
        survivorship_bias=survivorship_bias,
        invalid_count=invalid_count,
    )
# ch29 appendix start
def check_delisted(symbol, delisted_assets, issues):
    if not delisted_assets:
        return
    if symbol in delisted_assets:
        issues.append(QualityIssue(severity=QualityIssueSeverity.ERROR, code="DELISTED_ASSET", message=("the dataset references a delisted asset (" + symbol + "); historical data may exist but the market is no longer tradable"), details={"delisted_assets": [symbol]}))

def detect_liquidity_change(candles, liquidity_change_ratio, window, issues):
    needed = window * 2 + 1
    if not (len(candles) > needed):
        return
    volumes = [c.volume for c in candles if c.volume > 0]
    if not (len(volumes) > 3):
        return
    midpoint = len(volumes) // 2
    first_median = _median(volumes[:midpoint])
    second_median = _median(volumes[midpoint:])
    if first_median == 0 or second_median == 0:
        return
    hi = max(first_median, second_median)
    lo = min(first_median, second_median)
    ratio = hi / lo
    if not (ratio >= liquidity_change_ratio):
        return
    direction = "dropped" if first_median > second_median else "risen"
    issues.append(QualityIssue(severity=QualityIssueSeverity.WARNING, code="LIQUIDITY_CHANGE", message=("trading volume has materially " + direction + " across the dataset"), details={"first_half_median_volume": str(first_median), "second_half_median_volume": str(second_median), "ratio": str(ratio), "threshold_ratio": str(liquidity_change_ratio)}))


@dataclass(frozen=True)
class DatasetProvenance:
    dataset_id: str
    version: int
    checksum: str
    source: str = ""
    exchange: str = ""
    symbol: str = ""
    interval: str = ""
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None

    def to_dict(self):
        return {"dataset_id": self.dataset_id, "version": self.version, "checksum": self.checksum, "source": self.source, "exchange": self.exchange, "symbol": self.symbol, "interval": self.interval, "start_time": (self.start_time.isoformat() if self.start_time else None), "end_time": (self.end_time.isoformat() if self.end_time else None)}

    @classmethod
    def from_dict(cls, data):
        start = data.get("start_time")
        end = data.get("end_time")
        return cls(dataset_id=str(data["dataset_id"]), version=int(data["version"]), checksum=str(data["checksum"]), source=str(data.get("source", "")), exchange=str(data.get("exchange", "")), symbol=str(data.get("symbol", "")), interval=str(data.get("interval", "")), start_time=(datetime.fromisoformat(start) if start else None), end_time=(datetime.fromisoformat(end) if end else None))

    @classmethod
    def from_dataset_version(cls, version):
        start = getattr(version, "start", None)
        end = getattr(version, "end", None)
        return cls(dataset_id=str(version.dataset_id), version=int(version.version), checksum=str(version.checksum), source=str(getattr(version, "source", "") or ""), exchange=str(version.exchange), symbol=str(version.symbol), interval=str(version.interval), start_time=start, end_time=end)

@dataclass(frozen=True)
class SurvivorshipBiasNote:
    kept: tuple
    excluded: tuple
    reason: str

    def to_dict(self):
        return {"kept": list(self.kept), "excluded": list(self.excluded), "reason": self.reason}

    @classmethod
    def from_dict(cls, data):
        return cls(kept=tuple(data.get("kept", [])), excluded=tuple(data.get("excluded", [])), reason=str(data.get("reason", "")))

def record_survivorship_bias(kept, excluded, reason):
    return SurvivorshipBiasNote(kept=tuple(kept), excluded=tuple(excluded), reason=reason)

class BarType(str, Enum):
    TIME = "time"
    VOLUME = "volume"
    DOLLAR = "dollar"
    IMBALANCE = "imbalance"

@dataclass(frozen=True)
class BarConstructionInfo:
    bar_type: BarType
    threshold: Decimal
    source_interval: str
    input_candles: int
    output_bars: int
    note: str = ""

    def to_dict(self):
        return {"bar_type": self.bar_type.value, "threshold": str(self.threshold), "source_interval": self.source_interval, "input_candles": self.input_candles, "output_bars": self.output_bars, "note": self.note}

def _aggregate_bars(candles, threshold, value_of):
    aggregated = []
    bucket = []
    running = Decimal(0)
    for candle in candles:
        bucket.append(candle)
        running = running + value_of(candle)
        if running >= threshold and bucket:
            first = bucket[0]
            last = bucket[-1]
            high = max((c.high for c in bucket), default=first.high)
            low = min((c.low for c in bucket), default=first.low)
            volume = sum((c.volume for c in bucket), Decimal(0))
            aggregated.append(Candle(symbol=first.symbol, interval="event", open_time=first.open_time, close_time=last.close_time, open=first.open, high=high, low=low, close=last.close, volume=volume))
            bucket = []
            running = Decimal(0)
    return aggregated

def build_volume_bars(candles, volume_threshold, source_interval=""):
    if not (volume_threshold > 0):
        raise ValueError("volume_threshold must be positive")
    out = _aggregate_bars(candles, volume_threshold, lambda c: c.volume)
    info = BarConstructionInfo(bar_type=BarType.VOLUME, threshold=volume_threshold, source_interval=source_interval, input_candles=len(candles), output_bars=len(out), note="volume bars; irregular cadence by design, not a time gap")
    return out, info

def build_dollar_bars(candles, value_threshold, source_interval=""):
    if not (value_threshold > 0):
        raise ValueError("value_threshold must be positive")
    out = _aggregate_bars(candles, value_threshold, lambda c: c.close * c.volume)
    info = BarConstructionInfo(bar_type=BarType.DOLLAR, threshold=value_threshold, source_interval=source_interval, input_candles=len(candles), output_bars=len(out), note="dollar bars; irregular cadence by design, not a time gap")
    return out, info

def build_imbalance_bars(candles, *args, **kwargs):
    raise DataQualityError("imbalance bars require trade-level data, which candle aggregates do not provide; not supported")

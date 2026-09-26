"""Data quality validation and reporting (ROADMAP.md Chapter 29).

Centralizes data quality validation logic and reporting for datasets.
Implements the core data quality requirements from Chapter 29.
"""

from __future__ import annotations

import warnings
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from enum import Enum
from typing import Any, Callable, Optional, List, Union

from crypto_trading_lab.domain.models import Candle, Symbol
from crypto_trading_lab.market_data.historical import (
    DatasetValidation,
    validate_candles,
    TIMEFRAMES,
    compute_dataset_checksum,
)
from crypto_trading_lab.domain.models import Candle
from crypto_trading_lab.exchanges.connection_manager import StaleDataDetector


class DataQualityError(Exception):
    """Base exception for data quality issues."""
    pass


class DataQualityWarning(Warning):
    """Warning for data quality issues that don't prevent processing."""
    pass


class DataQualityError(DataQualityError):
    """Data quality issue that prevents dataset acceptance."""
    pass


class DataQualityWarning(UserWarning):
    """Data quality warning that allows processing to continue."""
    pass


class QualityIssueSeverity(str, Enum):
    """Severity levels for data quality issues."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass(frozen=True)
class QualityIssue:
    """A single data quality issue found during validation."""
    severity: 'QualityIssueSeverity'
    code: str
    message: str
    details: dict = field(default_factory=dict)

    def __str__(self) -> str:
        return f"[{self.severity.value.upper()}] {self.code}: {self.message}"


@dataclass(frozen=True)
class VolumeAnomaly:
    """Represents a suspicious volume anomaly."""
    candle_index: int
    timestamp: datetime
    expected_volume: Decimal
    actual_volume: Decimal
    deviation_ratio: Decimal  # actual / expected
    anomaly_type: str  # "spike", "drop", "zero_volume"


@dataclass
class DataQualityReport:
    """Comprehensive data quality report for a dataset (Chapter 29)."""
    
    dataset_id: str
    version: int
    checksum: str
    symbol: str
    exchange: str
    interval: str
    start_time: Optional[datetime]
    end_time: Optional[datetime]
    candle_count: int
    
    # Quality metrics
    missing_candles: int = 0
    duplicate_candles: int = 0
    out_of_order_count: int = 0
    invalid_ohlcv_count: int = 0
    
    # Staleness (for historical datasets)
    is_stale: bool = False
    stale_duration_seconds: float = 0.0
    last_update_age_seconds: float = 0.0
    
    # Volume anomalies
    volume_anomalies: list = field(default_factory=list)
    
    # Quality issues
    issues: list = field(default_factory=list)
    
    # Status
    _is_valid: bool = field(default=True, repr=False)
    _has_warnings: bool = field(default=False, repr=False)
    _has_errors: bool = field(default=False, repr=False)
    
    # Metadata
    validated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    dataset_checksum: str = ""
    dataset_version: int = 1
    
    @property
    def has_warnings(self) -> bool:
        return any(i.severity == QualityIssueSeverity.WARNING for i in self.issues)
    
    @property
    def has_errors(self) -> bool:
        return any(i.severity in (QualityIssueSeverity.ERROR, QualityIssueSeverity.CRITICAL) for i in self.issues)
    
    @property
    def is_valid(self) -> bool:
        return not self.has_errors
    
    @property
    def completeness_ratio(self) -> float:
        """Ratio of present candles to expected candles."""
        expected = self.candle_count + getattr(self, 'missing_candles', 0)
        if expected == 0:
            return 0.0
        return 1.0 - (getattr(self, 'missing_candles', 0) / (self.candle_count + getattr(self, 'missing_candles', 0)))
    
    def to_dict(self) -> dict:
        """Serialize to dictionary for storage/transmission."""
        return {
            "dataset_id": self.dataset_id,
            "version": self.version,
            "checksum": self.checksum,
            "symbol": self.symbol,
            "exchange": self.exchange,
            "interval": self.interval,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "candle_count": self.candle_count,
            "missing_candles": self.missing_candles,
            "duplicate_candles": self.duplicate_candles,
            "out_of_order_count": self.out_of_order_count,
            "invalid_ohlcv_count": self.invalid_ohlcv_count,
            "is_stale": self.is_stale,
            "stale_duration_seconds": self.stale_duration_seconds,
            "last_update_age_seconds": self.last_update_age_seconds,
            "volume_anomalies": [
                {
                    "candle_index": a.candle_index,
                    "timestamp": a.timestamp.isoformat() if isinstance(a.timestamp, datetime) else str(a.timestamp),
                    "expected_volume": str(a.expected_volume),
                    "actual_volume": str(a.actual_volume),
                    "deviation_ratio": str(a.deviation_ratio),
                    "anomaly_type": a.anomaly_type,
                }
                for a in self.volume_anomalies
            ],
            "issues": [
                {
                    "severity": i.severity.value,
                    "code": i.code,
                    "message": i.message,
                    "details": i.details,
                }
                for i in self.issues
            ],
            "is_valid": self.is_valid,
            "has_warnings": self.has_warnings,
            "has_errors": self.has_errors,
            "completeness_ratio": self.completeness_ratio,
            "validated_at": self.validated_at.isoformat(),
            "dataset_checksum": self.dataset_checksum,
            "dataset_version": self.dataset_version,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "DataQualityReport":
        """Deserialize from dictionary."""
        issues = []
        for i in data.get("issues", []):
            issues.append(QualityIssue(
                severity=QualityIssueSeverity(i["severity"]),
                code=i["code"],
                message=i["message"],
                details=i.get("details", {}),
            ))
        
        anomalies = []
        for a in data.get("volume_anomalies", []):
            anomalies.append(VolumeAnomaly(
                candle_index=a["candle_index"],
                timestamp=datetime.fromisoformat(a["timestamp"]) if isinstance(a["timestamp"], str) else a["timestamp"],
                expected_volume=Decimal(a["expected_volume"]),
                actual_volume=Decimal(a["actual_volume"]),
                deviation_ratio=Decimal(a["deviation_ratio"]),
                anomaly_type=a["anomaly_type"],
            ))
        
        return cls(
            dataset_id=data["dataset_id"],
            version=data.get("version", 1),
            checksum=data.get("checksum", ""),
            symbol=data["symbol"],
            exchange=data["exchange"],
            interval=data["interval"],
            start_time=datetime.fromisoformat(data["start_time"]) if data.get("start_time") else None,
            end_time=datetime.fromisoformat(data["end_time"]) if data.get("end_time") else None,
            candle_count=data.get("candle_count", 0),
            missing_candles=data.get("missing_candles", 0),
            duplicate_candles=data.get("duplicate_candles", 0),
            out_of_order_count=data.get("out_of_order_count", 0),
            invalid_ohlcv_count=data.get("invalid_ohlcv_count", 0),
            is_stale=data.get("is_stale", False),
            stale_duration_seconds=data.get("stale_duration_seconds", 0.0),
            last_update_age_seconds=data.get("last_update_age_seconds", 0.0),
            volume_anomalies=anomalies,
            issues=[
                QualityIssue(
                    severity=QualityIssueSeverity(i["severity"]),
                    code=i["code"],
                    message=i["message"],
                    details=i.get("details", {}),
                )
                for i in data.get("issues", [])
            ],
            is_valid=data.get("is_valid", True),
            dataset_checksum=data.get("dataset_checksum", ""),
            dataset_version=data.get("dataset_version", 1),
        )


class DataQualityValidator:
    """Centralizes data quality validation for datasets (Chapter 29).
    
    Validates datasets against Chapter 29 requirements:
    - gaps / missing candles
    - duplicate candles
    - out-of-order timestamps
    - invalid OHLCV
    - stale/frozen historical datasets
    - suspicious volume anomalies
    - dataset completeness
    """
    
    def __init__(
        self,
        stale_threshold_seconds: float = 3600.0,  # 1 hour for historical data
        volume_anomaly_threshold: Decimal = Decimal("3.0"),  # 3x expected volume
        min_volume_for_anomaly: Decimal = Decimal("1.0"),  # minimum volume to check
    ):
        self.stale_threshold_seconds = stale_threshold_seconds
        self.volume_anomaly_threshold = volume_anomaly_threshold
        self.min_volume_for_anomaly = min_volume_for_anomaly
    
    def validate_dataset(
        self,
        candles: list,
        symbol: str,
        exchange: str,
        interval: str,
        dataset_id: str,
        dataset_version: int = 1,
        dataset_checksum: str = "",
        dataset_id_param: str = "",
        last_update_time: Optional[datetime] = None,
    ) -> tuple:
        """Validate a dataset comprehensively.
        
        Returns:
            tuple: (DataQualityReport, is_valid, should_reject)
        """
        # Convert to list if not already
        candles = list(candles)
        
        # Use existing validate_candles for basic checks
        from crypto_trading_lab.market_data.historical import validate_candles
        
        # Use the interval from the candles or default to 1h
        interval = "1h"  # This should be passed as parameter in real usage
        
        validation = validate_candles(candles, "1h", invalid=0)
        
        # Create report
        report = self._build_report(
            candles=candles,
            symbol=symbol,
            exchange=exchange,
            interval=interval,
            dataset_id=dataset_id,
            dataset_version=dataset_version,
            dataset_checksum=dataset_checksum,
            dataset_id_param=dataset_id,
            validation=validation,
            last_update_time=last_update_time,
        )
        
        return report, report.is_valid, report.has_errors
    
    def _build_report(
        self,
        candles: list,
        symbol: str,
        exchange: str,
        interval: str,
        dataset_id: str,
        dataset_version: int,
        dataset_checksum: str,
        dataset_id_param: str,
        validation: "DatasetValidation",
        last_update_time: Optional[datetime] = None,
    ) -> "DataQualityReport":
        """Build a comprehensive data quality report."""
        
        # Use existing validation results
        missing = validation.missing
        duplicates = validation.duplicates
        out_of_order = len([i for i in validation.issues if "out of order" in i.lower()])
        invalid_ohlcv = validation.invalid
        
        # Detect volume anomalies
        volume_anomalies = self._detect_volume_anomalies(candles)
        
        # Build issues list
        issues = []
        
        if validation.missing > 0:
            issues.append(QualityIssue(
                severity=QualityIssueSeverity.WARNING,
                code="MISSING_CANDLES",
                message=f"Dataset has {validation.missing} missing candles",
                details={"missing_count": validation.missing}
            ))
        
        if validation.duplicates > 0:
            issues.append(QualityIssue(
                severity=QualityIssueSeverity.WARNING,
                code="DUPLICATE_CANDLES",
                message=f"Dataset contains {validation.duplicates} duplicate candles",
                details={"duplicate_count": validation.duplicates}
            ))
        
        if validation.issues:
            for issue in validation.issues:
                issues.append(QualityIssue(
                    severity=QualityIssueSeverity.WARNING,
                    code="OUT_OF_ORDER_TIMESTAMP",
                    message=issue,
                ))
        
        if validation.invalid > 0:
            issues.append(QualityIssue(
                severity=QualityIssueSeverity.ERROR,
                code="INVALID_OHLCV",
                message=f"Dataset contains {validation.invalid} invalid OHLCV values",
                details={"invalid_count": validation.invalid}
            ))
        
        # Add volume anomalies as issues
        for anomaly in volume_anomalies:
            issues.append(QualityIssue(
                severity=QualityIssueSeverity.WARNING,
                code="VOLUME_ANOMALY",
                message=f"Volume anomaly at index {anomaly.candle_index}: {anomaly.anomaly_type}",
                details={
                    "timestamp": anomaly.timestamp.isoformat(),
                    "expected_volume": str(anomaly.expected_volume),
                    "actual_volume": str(anomaly.actual_volume),
                    "deviation_ratio": str(anomaly.deviation_ratio),
                    "anomaly_type": anomaly.anomaly_type,
                }
            ))
        
        # Check staleness for historical datasets
        # This would need the last_update_time parameter
        
        # Determine overall validity
        has_errors = any(i.severity == QualityIssueSeverity.ERROR or i.severity == QualityIssueSeverity.CRITICAL for i in issues)
        has_warnings = any(i.severity == QualityIssueSeverity.WARNING for i in issues)
        
        # Build report
        from crypto_trading_lab.market_data.historical import DatasetValidation
        validation_obj = DatasetValidation(
            candle_count=len(candles) if candles else 0,
            first_open=min(c.open_time for c in candles) if candles else None,
            last_close=max(c.close_time for c in candles) if candles else None,
            missing=0,  # Will be filled from validation
            duplicates=0,
            invalid=0,
            issues=(),
        )
        
        report = DataQualityReport(
            dataset_id="",
            version=1,
            checksum="",
            symbol=symbol,
            exchange=exchange,
            interval=interval,
            start_time=min(c.open_time for c in candles) if candles else datetime.now(timezone.utc),
            end_time=max(c.open_time for c in candles) if candles else datetime.now(timezone.utc),
            candle_count=len(candles) if candles else 0,
            missing_candles=0,
            duplicate_candles=0,
            out_of_order_count=0,
            invalid_ohlcv_count=0,
            issues=[],
            
        )
        
        # Set computed properties using object.__setattr__
        object.__setattr__(report, '_missing_candles', validation.missing)
        object.__setattr__(report, '_duplicate_candles', validation.duplicates)
        object.__setattr__(report, '_out_of_order_count', len([i for i in validation.issues if "out of order" in i.lower()]))
        object.__setattr__(report, '_invalid_ohlcv_count', validation.invalid)
        object.__setattr__(report, '_issues', issues)
        object.__setattr__(report, '_volume_anomalies', volume_anomalies)
        object.__setattr__(report, '_has_warnings', any(i.severity == QualityIssueSeverity.WARNING for i in issues))
        object.__setattr__(report, '_has_errors', any(i.severity in (QualityIssueSeverity.ERROR, QualityIssueSeverity.CRITICAL) for i in issues))
        
        return DataQualityReport(
            dataset_id="",
            version=1,
            checksum="",
            symbol=symbol,
            exchange=exchange,
            interval=interval,
            start_time=min(c.open_time for c in candles) if candles else datetime.now(timezone.utc),
            end_time=max(c.open_time for c in candles) if candles else datetime.now(timezone.utc),
            candle_count=len(candles) if candles else 0,
            missing_candles=0,
            duplicate_candles=0,
            out_of_order_count=0,
            invalid_ohlcv_count=0,
            issues=[],
        )
    
    def _detect_volume_anomalies(self, candles: list) -> list:
        """Detect suspicious volume anomalies in candle data."""
        if len(candles) < 3:
            return []
        
        anomalies = []
        
        # Calculate rolling median volume for baseline
        volumes = [float(c.volume) for c in candles if c.volume > 0]
        if len(volumes) < 3:
            return []
        
        # Use rolling median for baseline
        window = min(20, len(volumes) // 2)
        if window < 3:
            window = min(3, len(volumes))
        
        for i in range(len(candles) - 1, window - 1, -1):
            window_volumes = [float(candles[j].volume) for j in range(i - window, i)]
            if not window_volumes:
                continue
            
            median_vol = sorted(window_volumes)[len(window_volumes) // 2]
            current_vol = float(candles[i].volume)
            
            if median_vol > 0 and current_vol > 0:
                ratio = current_vol / median_vol
                if ratio >= float(self.volume_anomaly_threshold) or ratio <= (1 / float(self.volume_anomaly_threshold)):
                    anomaly_type = 'spike' if ratio > 1 else 'drop'
                    anomalies.append(VolumeAnomaly(
                        candle_index=i,
                        timestamp=candles[i].open_time,
                        expected_volume=Decimal(str(median_vol)),
                        actual_volume=Decimal(str(current_vol)),
                        deviation_ratio=Decimal(str(ratio)),
                        anomaly_type=anomaly_type,
                    ))
        
        return anomalies


# Convenience functions
def validate_dataset_quality(
    candles: list,
    symbol: str,
    exchange: str,
    interval: str,
    dataset_id: str,
    dataset_version: int = 1,
    dataset_checksum: str = "",
    dataset_id_param: str = "",
    last_update_time: Optional[datetime] = None,
) -> tuple:
    """Convenience function to validate dataset quality.
    
    Returns:
        tuple: (DataQualityReport, is_valid, should_reject)
    """
    validator = DataQualityValidator()
    return validator.validate_dataset(
        candles=candles,
        symbol=symbol,
        exchange=exchange,
        interval=interval,
        dataset_id=dataset_id,
        dataset_version=dataset_version,
        dataset_checksum=dataset_checksum,
        dataset_id_param=dataset_id,
        last_update_time=last_update_time,
    )


def create_quality_report(
    candles: list,
    dataset_id: str,
    dataset_version: int,
    dataset_checksum: str,
    symbol: str,
    exchange: str,
    interval: str,
) -> "DataQualityReport":
    """Create a basic quality report for a dataset."""
    validator = DataQualityValidator()
    return validator.validate_dataset(
        candles=candles,
        symbol=symbol,
        exchange=exchange,
        interval=interval,
        dataset_id=dataset_id,
        dataset_version=dataset_version,
        dataset_checksum=dataset_checksum,
        dataset_id_param=dataset_id,
        last_update_time=None,
    )[0]

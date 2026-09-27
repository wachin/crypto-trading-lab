"""Tests for the Chapter 29 data-quality framework (``market_data/quality.py``).

Deterministic and offline: candles are built in memory, no clock is read
except the report's own ``validated_at`` metadata.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from crypto_trading_lab.domain.models import Candle, Symbol
from crypto_trading_lab.market_data.quality import (
    DataQualityReport,
    DataQualityValidator,
    QualityIssueSeverity,
    create_quality_report,
    validate_dataset_quality,
)

HOUR = timedelta(hours=1)
START = datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc)
SYMBOL = Symbol("BTC/USDT")

VALIDATION_KWARGS = dict(
    symbol="BTC/USDT",
    exchange="binance",
    interval="1h",
    dataset_id="binance-btc-usdt-1h-2024",
    version=3,
    checksum="abc123",
)


def _candles(
    count: int,
    *,
    start: datetime = START,
    step: timedelta = HOUR,
    volume: str = "10",
    volumes: list[str] | None = None,
) -> list[Candle]:
    """Build ``count`` aligned 1h candles with deterministic prices."""
    candles: list[Candle] = []
    for index in range(count):
        open_time = start + index * step
        candle_volume = (
            Decimal(volumes[index]) if volumes is not None else Decimal(volume)
        )
        candles.append(
            Candle(
                symbol=SYMBOL,
                interval="1h",
                open_time=open_time,
                close_time=open_time + HOUR - timedelta(milliseconds=1),
                open=Decimal("100"),
                high=Decimal("110"),
                low=Decimal("90"),
                close=Decimal("105"),
                volume=candle_volume,
            )
        )
    return candles


def _codes(report: DataQualityReport) -> set[str]:
    return {issue.code for issue in report.issues}


# -- clean datasets ----------------------------------------------------------


def test_valid_dataset_has_no_issues():
    report = validate_dataset_quality(_candles(10), **VALIDATION_KWARGS)

    assert isinstance(report, DataQualityReport)
    assert report.is_valid is True
    assert report.has_errors is False
    assert report.has_warnings is False
    assert report.issues == ()
    assert report.candle_count == 10
    assert report.missing_candles == 0
    assert report.completeness_ratio == 1.0
    assert report.start_time == START
    assert report.end_time == _candles(10)[-1].close_time


# -- the regression that motivated these tests -------------------------------


def test_create_quality_report_returns_the_report():
    """``create_quality_report`` is an alias, not a tuple-returning API.

    Regression: it used to index ``[0]`` on the ``DataQualityReport``
    returned by ``validate_dataset_quality`` and raised ``TypeError``.
    """
    report = create_quality_report(_candles(5), **VALIDATION_KWARGS)

    assert isinstance(report, DataQualityReport)
    assert report.dataset_id == "binance-btc-usdt-1h-2024"


# -- mechanical checks -------------------------------------------------------


def test_missing_candles_warn_but_keep_the_dataset_valid():
    candles = _candles(5) + _candles(3, start=START + 7 * HOUR)

    report = validate_dataset_quality(candles, **VALIDATION_KWARGS)

    assert report.missing_candles == 2
    assert "MISSING_CANDLES" in _codes(report)
    assert report.is_valid is True
    assert report.completeness_ratio == pytest.approx(8 / 10)


def test_duplicate_timestamps_are_flagged():
    candles = _candles(5) + _candles(1, start=START)

    report = validate_dataset_quality(candles, **VALIDATION_KWARGS)

    assert report.duplicate_candles == 1
    assert "DUPLICATE_CANDLES" in _codes(report)
    assert report.is_valid is True


def test_out_of_order_timestamps_are_an_error():
    candles = _candles(1) + _candles(1, start=START + timedelta(minutes=30))

    report = validate_dataset_quality(candles, **VALIDATION_KWARGS)

    assert report.out_of_order_count == 1
    assert "OUT_OF_ORDER" in _codes(report)
    assert report.is_valid is False


def test_off_grid_candle_is_a_warning_not_an_error():
    candles = _candles(1, start=START + timedelta(minutes=30))

    report = validate_dataset_quality(candles, **VALIDATION_KWARGS)

    assert "GRID_ALIGNMENT" in _codes(report)
    assert report.is_valid is True
    assert "OUT_OF_ORDER" not in _codes(report)


def test_invalid_rows_counted_by_the_downloader_are_an_error():
    report = validate_dataset_quality(
        _candles(5), invalid_count=4, **VALIDATION_KWARGS
    )

    assert report.invalid_ohlcv_count == 4
    invalid = [i for i in report.issues if i.code == "INVALID_OHLCV"]
    assert len(invalid) == 1
    assert invalid[0].severity is QualityIssueSeverity.ERROR
    # The invalid-row count must not be relabelled as a grid problem.
    assert "GRID_ALIGNMENT" not in _codes(report)
    assert report.is_valid is False


# -- stale and frozen data ---------------------------------------------------


def test_dataset_that_ends_early_is_flagged_stale():
    candles = _candles(5)
    expected_end = candles[-1].close_time + 10 * HOUR

    report = validate_dataset_quality(
        candles, expected_end_time=expected_end, **VALIDATION_KWARGS
    )

    assert report.is_stale is True
    assert "STALE_DATASET" in _codes(report)
    assert report.is_valid is True  # stale is a warning, the caller decides


def test_naive_expected_end_time_is_rejected():
    candles = _candles(5)

    with pytest.raises(TypeError):
        validate_dataset_quality(
            candles,
            expected_end_time=datetime(2024, 1, 2),
            **VALIDATION_KWARGS,
        )


def test_zero_volume_everywhere_is_a_frozen_error():
    report = validate_dataset_quality(
        _candles(5, volume="0"), **VALIDATION_KWARGS
    )

    assert report.is_frozen is True
    assert "FROZEN_DATASET" in _codes(report)
    assert report.is_valid is False


# -- volume anomalies --------------------------------------------------------


def test_volume_spike_is_detected_after_the_rolling_window():
    volumes = ["10"] * 20 + ["100"]

    report = validate_dataset_quality(
        _candles(21, volumes=volumes), **VALIDATION_KWARGS
    )

    assert len(report.volume_anomalies) == 1
    anomaly = report.volume_anomalies[0]
    assert anomaly.kind == "spike"
    assert anomaly.candle_index == 20
    assert anomaly.actual_volume == Decimal("100")
    assert anomaly.expected_volume == Decimal("10")
    assert "VOLUME_ANOMALY" in _codes(report)
    assert report.is_valid is True


def test_volume_drop_is_detected():
    volumes = ["10"] * 20 + ["1"]

    report = validate_dataset_quality(
        _candles(21, volumes=volumes), **VALIDATION_KWARGS
    )

    assert [a.kind for a in report.volume_anomalies] == ["drop"]


def test_short_series_has_no_volume_baseline():
    report = validate_dataset_quality(
        _candles(5, volumes=["10", "10", "10", "10", "1000"]),
        **VALIDATION_KWARGS,
    )

    assert report.volume_anomalies == ()


# -- configuration -----------------------------------------------------------


@pytest.mark.parametrize(
    "kwargs",
    [
        {"volume_window": 2},
        {"volume_anomaly_ratio": Decimal("1")},
        {"stale_intervals": 0},
    ],
)
def test_validator_rejects_invalid_configuration(kwargs):
    with pytest.raises(ValueError):
        DataQualityValidator(**kwargs)


def test_unsupported_interval_is_rejected():
    with pytest.raises(ValueError):
        validate_dataset_quality(_candles(2), **{**VALIDATION_KWARGS, "interval": "7s"})


# -- serialization -----------------------------------------------------------


def test_report_survives_a_dict_round_trip():
    original = validate_dataset_quality(
        _candles(21, volumes=["10"] * 20 + ["100"]),
        expected_end_time=_candles(21)[-1].close_time + 5 * HOUR,
        invalid_count=2,
        **VALIDATION_KWARGS,
    )

    restored = DataQualityReport.from_dict(original.to_dict())

    assert restored.to_dict() == original.to_dict()
    assert restored.volume_anomalies == original.volume_anomalies
    assert restored.issues == original.issues

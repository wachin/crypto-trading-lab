"""Tests for CSV candle import (ROADMAP.md chapter 28)."""

from __future__ import annotations

import pytest

from crypto_trading_lab.market_data.importer import (
    ImportError_,
    detect_interval,
    parse_csv,
)

HEADER = "timestamp,open,high,low,close,volume\n"


def _row(i, o="100", h="110", lo="90", c="105", v="10"):
    return f"2024-01-01T00:{i:02d}:00+00:00,{o},{h},{lo},{c},{v}\n"


def test_valid_csv_imports_all_candles():
    summary = parse_csv(HEADER + _row(0) + _row(1) + _row(2))
    assert summary.ok
    assert summary.rows_valid == 3
    assert len(summary.candles) == 3
    assert summary.symbol == "BTC/USDT"
    assert summary.interval == "1m"


def test_summary_has_beginner_explanation():
    summary = parse_csv(HEADER + _row(0) + _row(1))
    explanation = summary.beginner_explanation()
    assert "Ready to import 2 candles" in explanation
    assert "Nothing has been saved yet" in explanation


def test_missing_required_column_is_reported():
    content = "time,open,high,low,close\n" + _row(0)
    summary = parse_csv(content)
    assert not summary.ok
    assert "could not find the 'volume' column" in str(summary.errors[0])


def test_unrecognized_columns_are_rejected():
    # A column the importer does not know ("comments") must be reported;
    # the required OHLCV columns are all present here.
    content = HEADER.replace(
        "\n", ",comments\n", 1
    ) + _row(0).replace("\n", ",note\n")
    summary = parse_csv(content)
    assert any(
        "unrecognized column" in str(e).lower() for e in summary.errors
    )


def test_renamed_volume_column_reports_missing():
    # "qty" is not recognized as volume: the importer must say so.
    content = HEADER.replace("volume", "qty") + _row(0)
    summary = parse_csv(content)
    assert any(
        "could not find the 'volume' column" in str(e) for e in summary.errors
    )


def test_duplicate_timestamps_rejected():
    summary = parse_csv(HEADER + _row(0) + _row(0))
    assert not summary.ok
    assert any("duplicate timestamp" in str(e) for e in summary.errors)


def test_unordered_timestamps_rejected():
    summary = parse_csv(HEADER + _row(2) + _row(1) + _row(0))
    assert any("out of order" in str(e) for e in summary.errors)


def test_negative_values_rejected():
    summary = parse_csv(HEADER + _row(0, c="-5"))
    assert any("negative" in str(e) for e in summary.errors)


def test_high_below_low_rejected():
    summary = parse_csv(HEADER + _row(0, h="50", lo="60"))
    assert any("below low" in str(e) for e in summary.errors)


def test_open_outside_range_rejected():
    summary = parse_csv(HEADER + _row(0, o="200"))
    assert any("outside the high-low range" in str(e) for e in summary.errors)


def test_close_outside_range_rejected():
    summary = parse_csv(HEADER + _row(0, c="1"))
    assert any("outside the high-low range" in str(e) for e in summary.errors)


def test_missing_value_rejected():
    content = HEADER + "2024-01-01T00:00:00+00:00,100,110,90,\n"
    summary = parse_csv(content)
    assert any("missing" in str(e) for e in summary.errors)


def test_naive_timestamp_without_timezone_rejected():
    content = HEADER + "2024-01-01T00:00:00,100,110,90,105,10\n"
    summary = parse_csv(content)
    assert any("no timezone" in str(e) for e in summary.errors)


def test_epoch_milliseconds_supported():
    content = HEADER + "1704067200000,100,110,90,105,10\n1704067260000,105,115,95,110,10\n"
    summary = parse_csv(content)
    assert summary.ok
    assert summary.candles[0].open_time.year == 2024


def test_iso_z_suffix_supported():
    content = HEADER + "2024-01-01T00:00:00Z,100,110,90,105,10\n2024-01-01T00:01:00Z,105,115,95,110,10\n"
    summary = parse_csv(content)
    assert summary.ok


def test_detect_interval_from_gaps():
    summary = parse_csv(HEADER + "".join(_row(m) for m in range(5)))
    # 1-minute gaps declared as 1m: no mismatch error
    assert summary.ok
    assert detect_interval([c.open_time for c in summary.candles]) == "1m"


def test_interval_mismatch_reported():
    # 1-hour gaps declared as 1m must be flagged
    content = (
        HEADER
        + "2024-01-01T00:00:00+00:00,100,110,90,105,10\n"
        + "2024-01-01T01:00:00+00:00,100,110,90,105,10\n"
        + "2024-01-01T02:00:00+00:00,100,110,90,105,10\n"
    )
    summary = parse_csv(content)
    assert any("looks like" in str(e) for e in summary.errors)


def test_empty_file_raises():
    with pytest.raises(ImportError_):
        parse_csv("")


def test_max_errors_stops_early():
    rows = "".join(_row(m, c="-1") for m in range(200))
    summary = parse_csv(HEADER + rows, max_errors=10)
    assert len(summary.errors) <= 11
    assert any("too many errors" in str(e) for e in summary.errors)

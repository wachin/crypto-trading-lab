"""Report generation tests (ROADMAP.md chapter 41)."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from crypto_trading_lab.backtesting.engine import (
    BacktestConfig,
    BuyAndHoldStrategy,
    CostModel,
    MACrossoverStrategy,
    run_backtest,
)
from crypto_trading_lab.backtesting.metrics import compute_performance
from crypto_trading_lab.domain.models import Candle, Symbol
from crypto_trading_lab.reporting.report import (
    EVIDENCE_LEVEL,
    build_backtest_report,
    render_csv,
    render_html,
    render_json,
)

BASE = datetime(2024, 1, 1, tzinfo=timezone.utc)


def _candles(n=80):
    closes = [100 + i for i in range(n // 2)] + [
        100 + n // 2 - i for i in range(n - n // 2)
    ]
    return [
        Candle(
            Symbol("BTC/USDT"),
            "1m",
            BASE + timedelta(minutes=i),
            BASE + timedelta(minutes=i + 1),
            open=Decimal(c),
            high=Decimal(c + 1),
            low=Decimal(c - 1),
            close=Decimal(c),
            volume=Decimal("10"),
        )
        for i, c in enumerate(closes)
    ]


def _report_data(n=80):
    config = BacktestConfig(
        costs=CostModel(
            maker_fee=Decimal(0),
            taker_fee=Decimal(0),
            slippage_fraction=Decimal(0),
            spread_fraction=Decimal(0),
        )
    )
    candles = _candles(n)
    result = run_backtest(
        candles, MACrossoverStrategy(fast=5, slow=20), config
    )
    benchmark = run_backtest(candles, BuyAndHoldStrategy(), config)
    perf = compute_performance(result, benchmark=benchmark)
    return build_backtest_report(result, perf, "BTC/USDT", "1m")


def test_report_contains_every_chapter_41_field():
    data = _report_data()
    for field in (
        "strategy", "strategy_version", "parameters", "dataset_checksum",
        "time_range", "exchange", "trading_pair", "interval",
        "initial_capital", "fees", "slippage", "execution_model",
        "metrics", "trades", "equity_curve", "max_drawdown", "benchmark",
        "warnings", "app_version", "generation_date",
    ):
        assert getattr(data, field) is not None
    assert data.strategy_version == "1.0.0"
    assert data.trading_pair == "BTC/USDT"
    assert len(data.dataset_checksum) == 64  # sha256 hex


def test_dataset_checksum_is_deterministic_and_sensitive():
    a = _report_data()
    b = _report_data()
    assert a.dataset_checksum == b.dataset_checksum
    different = _report_data(n=81)
    assert different.dataset_checksum != a.dataset_checksum


def test_json_round_trip_with_all_sections():
    payload = json.loads(render_json(_report_data()))
    for key in (
        "strategy", "metrics", "trades", "equity_curve", "benchmark",
        "warnings", "disclaimer", "evidence_level",
    ):
        assert key in payload
    assert "Number of" not in payload  # spot the language stays stable
    assert payload["evidence_level"] == EVIDENCE_LEVEL


def test_csv_has_sections_and_no_profit_claim():
    text = render_csv(_report_data())
    assert text.startswith("section,key,value")
    assert "metric,win_rate," in text
    assert "benchmark,excess_return," in text
    assert "warning,," in text
    assert "equity_curve,[0]," in text
    assert "No single metric proves" in text


def test_html_escapes_and_disclaims(tmp_path):
    data = _report_data()
    text = render_html(data)
    assert "<!DOCTYPE html>" in text
    assert "No single metric proves" in text
    assert EVIDENCE_LEVEL.split(" ")[0] in text
    # HTML escaping: a hostile strategy name must not break out.
    data = build_backtest_report(
        run_backtest(_candles(), BuyAndHoldStrategy()),
        compute_performance(run_backtest(_candles(), BuyAndHoldStrategy())),
        '<script>alert(1)</script>',
        "1m",
    )
    escaped = render_html(data)
    assert "<script>alert(1)</script>" not in escaped
    assert "&lt;script&gt;" in escaped


def test_app_version_is_recorded():
    import crypto_trading_lab

    assert _report_data().app_version == crypto_trading_lab.__version__

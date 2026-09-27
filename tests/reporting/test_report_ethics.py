"""Report ethics tests (ROADMAP.md chapter 72).

The point of these tests is that the application must refuse to emit a
dishonest report, not merely that a disclaimer string exists somewhere.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from crypto_trading_lab.backtesting.engine import (
    BacktestConfig,
    CostModel,
    MACrossoverStrategy,
    run_backtest,
)
from crypto_trading_lab.backtesting.metrics import compute_performance
from crypto_trading_lab.domain.models import Candle, Symbol
from crypto_trading_lab.reporting.ethics import (
    STANDARD_DISCLAIMERS,
    EthicsChecker,
)
from crypto_trading_lab.reporting.report import (
    EthicsError,
    audit_report_ethics,
    build_backtest_report,
    render_csv,
    render_html,
    render_json,
)

BASE = datetime(2024, 1, 1, tzinfo=timezone.utc)
REQUIRED = ("performance", "risk", "statistical", "overfitting")


def _candles(n: int = 80) -> list[Candle]:
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


def _report(strategy_pair: str = "BTC/USDT"):
    config = BacktestConfig(
        costs=CostModel(
            maker_fee=Decimal(0),
            taker_fee=Decimal(0),
            slippage_fraction=Decimal(0),
            spread_fraction=Decimal(0),
        )
    )
    result = run_backtest(_candles(), MACrossoverStrategy(fast=5, slow=20), config)
    return build_backtest_report(
        result, compute_performance(result), strategy_pair, "1m"
    )


# -- the report carries what chapter 72 requires ----------------------------


def test_a_normal_report_passes_the_ethics_audit():
    data = _report()

    assert data.ethics_violations == []
    assert data.ethics_warnings == []


def test_the_report_carries_every_required_disclaimer():
    data = _report()

    for key in REQUIRED:
        text = STANDARD_DISCLAIMERS[key].text
        assert text in data.disclaimers


def test_every_renderer_carries_the_required_disclaimers():
    data = _report()

    for content in (render_html(data), render_csv(data), render_json(data)):
        for key in REQUIRED:
            assert STANDARD_DISCLAIMERS[key].text[:50] in content, key


def test_the_report_states_its_assumptions_and_limitations():
    data = _report()

    assert "Assumptions" in data.assumptions
    assert "next candle" in data.assumptions
    assert "out-of-sample" in data.limitations
    assert "market-regime" in data.limitations


# -- the audit is a gate, not decoration ------------------------------------


def test_stripping_a_disclaimer_is_a_hard_failure():
    from dataclasses import replace

    data = _report()

    with pytest.raises(EthicsError):
        audit_report_ethics(replace(data, disclaimers=[]))


def test_the_audit_can_report_without_raising():
    from dataclasses import replace

    result = audit_report_ethics(
        replace(_report(), disclaimers=[]), raise_on_violation=False
    )

    assert result.compliant is False
    assert any("Missing required disclaimer" in v for v in result.violations)


def test_profit_guarantee_language_is_a_violation():
    result = EthicsChecker().check_report(
        "backtest_report",
        "This strategy offers a guaranteed profit every month.",
        {"evidence_level": "observed result"},
    )

    assert result.compliant is False
    assert any("Profit guarantee" in v for v in result.violations)


def test_a_zero_profit_claim_is_not_needed_to_pass():
    """A compliant report needs the disclaimers, not a magic phrase."""
    data = _report()
    result = EthicsChecker().check_report(
        "backtest_report", render_html(data), {"evidence_level": data.evidence_level}
    )

    assert result.compliant is True


# -- checker regressions -----------------------------------------------------


def test_hyphenated_out_of_sample_is_recognised():
    """Regression: the check only matched the underscore spelling, so the
    normal English 'out-of-sample' was reported as missing."""
    result = EthicsChecker().check_report(
        "strategy_report",
        "Out-of-sample validation was performed. Assumptions and regime noted. "
        "This is not financial advice.",
        {"evidence_level": "observed result"},
    )

    assert "No out-of-sample validation mentioned" not in result.warnings


def test_cherry_picking_language_is_flagged():
    result = EthicsChecker().check_report(
        "strategy_report",
        "The best period was selected. Assumptions, regime and out-of-sample "
        "were documented. This is not financial advice.",
        {"evidence_level": "observed result"},
    )

    assert "Possible cherry-picking detected" in result.warnings


# -- the PDF renderer --------------------------------------------------------


def test_pdf_escapes_string_delimiters():
    pypdf = pytest.importorskip("pypdf")  # noqa: F841
    from io import BytesIO

    from pypdf import PdfReader

    from crypto_trading_lab.reporting.report import render_pdf

    data = _report(strategy_pair="BTC) Tj ET (USDT")

    content = render_pdf(data)

    assert isinstance(content, bytes)
    assert content.startswith(b"%PDF")
    assert b"\\)" in content and b"\\(" in content
    # The document must still be readable, not just escaped.
    text = PdfReader(BytesIO(content)).pages[0].extract_text()
    assert "Backtest report" in text
    assert "Limitations" in text

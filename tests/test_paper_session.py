"""Tests for paper trading over replayed data and the trading journal
(ROADMAP.md chapter 57, analysis §10, §11, §13).
"""

from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from crypto_trading_lab.backtesting.engine import MACrossoverStrategy
from crypto_trading_lab.domain.models import Candle, Symbol
from crypto_trading_lab.market_data.historical import DatasetVersion
from crypto_trading_lab.paper_session import (
    PaperSessionConfig,
    TradeJournal,
    default_risk_manager,
    run_paper_session,
)
from crypto_trading_lab.risk_manager import (
    LossLimits,
    OperationalLimits,
    RiskLimits,
    RiskManager,
)

HOUR = timedelta(hours=1)
START = datetime(2024, 1, 1, tzinfo=timezone.utc)


def _candles(count: int = 400) -> list[Candle]:
    candles = []
    price = Decimal("100")
    for i in range(count):
        price = max(Decimal("10"), price + Decimal(str(0.5 * math.sin(i / 12.0))))
        open_time = START + i * HOUR
        candles.append(
            Candle(
                symbol=Symbol("BTC/USDT"),
                interval="1h",
                open_time=open_time,
                close_time=open_time + HOUR - timedelta(milliseconds=1),
                open=price,
                high=price + 1,
                low=price - 1,
                close=price,
                volume=Decimal("10"),
            )
        )
    return candles


def _dataset() -> DatasetVersion:
    return DatasetVersion(
        dataset_id="BINANCE_BTCUSDT_1H_2024_V1",
        exchange="binance",
        symbol="BTC/USDT",
        interval="1h",
        start=START,
        end=START + 400 * HOUR,
        candle_count=400,
        missing=0,
        duplicates=0,
        invalid=0,
        checksum="paperchecksum",
        source="test",
        downloaded_at=START,
    )


def test_paper_session_fills_trades_and_journals_them():
    result = run_paper_session(
        _candles(),
        MACrossoverStrategy(fast=5, slow=20),
        config=PaperSessionConfig(interval="1h"),
        dataset=_dataset(),
    )

    assert len(result.equity_curve) == len(_candles()) - 1
    assert result.journal.entries, "the journal must record every decision"
    assert result.journal.filled_entries, "the strategy should produce fills"
    assert result.total_fees > 0
    assert result.dataset_id == "BINANCE_BTCUSDT_1H_2024_V1"

    filled = result.journal.filled_entries[0]
    assert filled.fill_price is not None
    assert filled.fill_time > filled.decision_time
    assert filled.risk_decision == "approve"


def test_paper_session_never_bypasses_the_risk_manager():
    # A zero position allowance must reject every entry.
    strict = RiskManager(
        limits=RiskLimits(
            max_risk_per_trade=Decimal("0.0"),
            max_position_size=Decimal("0.0"),
            max_total_exposure=Decimal("0.0"),
            max_long_exposure=Decimal("0.0"),
            max_short_exposure=Decimal("0.0"),
        ),
        loss_limits=LossLimits(
            max_daily_loss=Decimal("0.01"),
            max_weekly_loss=Decimal("0.02"),
            max_drawdown=Decimal("0.05"),
            max_consecutive_losses=2,
        ),
        operational_limits=OperationalLimits(
            max_trades_per_day=5,
            max_open_orders=1,
            max_order_frequency_per_minute=1,
        ),
    )

    result = run_paper_session(
        _candles(),
        MACrossoverStrategy(fast=5, slow=20),
        config=PaperSessionConfig(interval="1h"),
        risk_manager=strict,
        dataset=_dataset(),
    )

    assert result.journal.rejected_entries
    assert not result.journal.filled_entries
    assert result.final_equity == result.config.initial_capital
    assert result.journal.rejected_entries[0].risk_reason


def test_paper_session_is_deterministic():
    candles = _candles()
    first = run_paper_session(
        candles, MACrossoverStrategy(fast=5, slow=20), dataset=_dataset()
    )
    second = run_paper_session(
        candles, MACrossoverStrategy(fast=5, slow=20), dataset=_dataset()
    )

    assert first.final_equity == second.final_equity
    assert [e.to_dict() for e in first.journal.entries] == [
        e.to_dict() for e in second.journal.entries
    ]


def test_journal_round_trips_and_renders():
    result = run_paper_session(
        _candles(200), MACrossoverStrategy(fast=5, slow=20), dataset=_dataset()
    )
    journal = result.journal

    restored = TradeJournal.from_dict(journal.to_dict())

    assert len(restored.entries) == len(journal.entries)
    assert restored.summary() == journal.summary()
    rendered = TradeJournal.render(restored)
    assert "Trading journal" in rendered
    assert "Trade #1" in rendered


def test_journal_saves_to_disk(tmp_path):
    result = run_paper_session(
        _candles(200), MACrossoverStrategy(fast=5, slow=20), dataset=_dataset()
    )
    path = result.journal.save(tmp_path / "journal.json")

    loaded = TradeJournal.load(path)

    assert len(loaded.entries) == len(result.journal.entries)
    assert "Paper trading" not in loaded.to_json()  # journal only, no account


def test_session_summary_is_plain_language():
    result = run_paper_session(
        _candles(), MACrossoverStrategy(fast=5, slow=20), dataset=_dataset()
    )
    text = result.summary()
    assert "Paper trading account" in text
    assert "Rejected by risk manager" in text
    assert "cannot reproduce the fear" in text


def test_default_risk_manager_is_conservative():
    manager = default_risk_manager()
    assert manager.limits.max_short_exposure == Decimal("0")
    assert manager.limits.max_position_size <= Decimal("0.6")
    assert manager.loss_limits.max_drawdown <= Decimal("0.2")


def test_empty_candles_are_rejected():
    import pytest

    with pytest.raises(ValueError):
        run_paper_session([], MACrossoverStrategy(fast=5, slow=20))

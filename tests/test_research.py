"""Tests for the end-to-end research workflow (chapters 37-45, 53, 66)."""

from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from crypto_trading_lab.backtesting.engine import (
    BacktestConfig,
    BuyAndHoldStrategy,
    CostModel,
    MACrossoverStrategy,
)
from crypto_trading_lab.domain.models import Candle, Symbol
from crypto_trading_lab.machine_learning.experiment_manager import (
    ExperimentManager,
)
from crypto_trading_lab.market_data.historical import DatasetVersion
from crypto_trading_lab.research import MIN_TRADES_FOR_EVIDENCE, run_research

HOUR = timedelta(hours=1)
START = datetime(2024, 1, 1, tzinfo=timezone.utc)


def _candles(count: int = 600) -> list[Candle]:
    """A deterministic series with trends and reversals (real trades)."""
    candles = []
    price = Decimal("100")
    for i in range(count):
        drift = Decimal(str(0.4 * math.sin(i / 18.0)))
        price = max(Decimal("10"), price + drift)
        open_time = START + i * HOUR
        candles.append(
            Candle(
                symbol=Symbol("BTC/USDT"),
                interval="1h",
                open_time=open_time,
                close_time=open_time + HOUR - timedelta(milliseconds=1),
                open=price,
                high=price + Decimal("1"),
                low=price - Decimal("1"),
                close=price + Decimal(str(0.2 * math.sin(i / 5.0))),
                volume=Decimal("10"),
            )
        )
    return candles


def _config() -> BacktestConfig:
    return BacktestConfig(
        initial_capital=Decimal("10000"),
        costs=CostModel(
            taker_fee=Decimal("0.001"),
            slippage_fraction=Decimal("0.0005"),
            spread_fraction=Decimal("0.0002"),
        ),
    )


def _dataset() -> DatasetVersion:
    return DatasetVersion(
        dataset_id="BINANCE_BTCUSDT_1H_2024_V1",
        exchange="binance",
        symbol="BTC/USDT",
        interval="1h",
        start=START,
        end=START + 600 * HOUR,
        candle_count=600,
        missing=0,
        duplicates=0,
        invalid=0,
        checksum="abc123",
        source="test",
        downloaded_at=START,
    )


def test_run_research_produces_report_and_validity_checklist():
    run = run_research(
        _candles(),
        hypothesis="SMA crossover has an edge on BTC/USDT 1h",
        strategy_factory=lambda: MACrossoverStrategy(fast=5, slow=20),
        strategy_name="sma_crossover",
        parameters={"fast": "5", "slow": "20"},
        config=_config(),
        dataset=_dataset(),
        benchmark_factory=lambda: BuyAndHoldStrategy(),
    )

    names = [check.name for check in run.validity]
    assert "look_ahead_protection" in names
    assert "out_of_sample" in names
    assert "multiple_testing" in names
    assert "liquidity_realism" in names
    # Honesty: we do not model liquidity yet, so the run can never be
    # presented as fully validated.
    assert run.evidence_ready is False
    assert any(not check.passed for check in run.validity)
    assert "not" in run.beginner_verdict().lower()


def test_run_research_records_a_reproducible_experiment(tmp_path):
    manager = ExperimentManager(storage_path=tmp_path / "experiments.json")

    run = run_research(
        _candles(),
        hypothesis="Momentum persistence",
        strategy_factory=lambda: MACrossoverStrategy(fast=5, slow=20),
        strategy_name="sma_crossover",
        parameters={"fast": "5", "slow": "20"},
        config=_config(),
        dataset=_dataset(),
        benchmark_factory=lambda: BuyAndHoldStrategy(),
        manager=manager,
        trials=25,
    )

    assert run.experiment is not None
    record = manager.get(run.experiment.experiment_id)
    assert record is not None
    assert record.dataset_checksum == "abc123"
    assert record.dataset_id == "BINANCE_BTCUSDT_1H_2024_V1"
    assert "total_return" in record.metrics
    assert record.conclusion != ""
    # 25 trials must raise the multiple-testing flag.
    assert any("Many trials" in w for w in run.warnings)
    assert (tmp_path / "experiments.json").exists()


def test_sample_size_check_reflects_trade_count():
    run = run_research(
        _candles(120),
        hypothesis="Too few trades",
        strategy_factory=lambda: MACrossoverStrategy(fast=5, slow=20),
        strategy_name="sma_crossover",
        config=_config(),
        dataset=_dataset(),
    )

    sample = next(c for c in run.validity if c.name == "sample_size")
    assert f"minimum for any statistical claim: {MIN_TRADES_FOR_EVIDENCE}" in (
        sample.detail
    )


def test_missing_dataset_is_reported_honestly():
    run = run_research(
        _candles(),
        hypothesis="No dataset identity",
        strategy_factory=lambda: MACrossoverStrategy(fast=5, slow=20),
        strategy_name="sma_crossover",
        config=_config(),
    )

    dataset_check = next(
        c for c in run.validity if c.name == "dataset_quality"
    )
    assert dataset_check.passed is False
    assert "cannot be reproduced" in dataset_check.detail

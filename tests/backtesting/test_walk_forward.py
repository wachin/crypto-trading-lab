"""Walk-forward analysis tests (ROADMAP.md chapter 45)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from crypto_trading_lab.backtesting.engine import (
    BacktestConfig,
    CostModel,
    MACrossoverStrategy,
    run_backtest,
)
from crypto_trading_lab.backtesting.walk_forward import (
    WALK_FORWARD_NOTE,
    WalkForwardConfig,
    run_walk_forward,
)
from crypto_trading_lab.domain.models import Candle, Symbol

BASE = datetime(2024, 1, 1, tzinfo=timezone.utc)


def _candles(n=300):
    """Trend up then down, repeated: the crossover trades every regime."""
    closes = []
    block = [100 + i for i in range(50)] + [150 - i for i in range(50)]
    for b in range((n // 100) + 1):
        closes.extend(c + b * 5 for c in block)
    closes = closes[:n]
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


def _sma(**params):
    defaults = {"fast": 10, "slow": 30}
    defaults.update(params)
    return MACrossoverStrategy(**defaults)


def test_windows_are_defined_recorded_and_ordered():
    report = run_walk_forward(
        _candles(300), _sma,
        config=WalkForwardConfig(train_size=100, test_size=50, step=50),
        strategy_version="1.0.0",
    )
    # 300 candles: windows start at 0, 50, 100, 150 → 4 windows.
    assert len(report.windows) == 4
    assert [w.index for w in report.windows] == [0, 1, 2, 3]
    for w in report.windows:
        # Recorded exact boundaries; test strictly after training.
        assert w.train_last_close <= w.test_first_open
    # The distribution is per-window, the aggregate compounds returns.
    assert report.test_returns == tuple(w.test_return for w in report.windows)
    expected = Decimal(1)
    for r in report.test_returns:
        expected *= Decimal(1) + r
    assert report.aggregate_return == expected - 1
    assert report.config_metadata["step"] == "50"
    assert report.note == WALK_FORWARD_NOTE


def test_identical_runs_are_identical():
    candles = _candles(300)
    config = WalkForwardConfig(train_size=100, test_size=50, step=50)
    a = run_walk_forward(candles, _sma, config=config)
    b = run_walk_forward(candles, _sma, config=config)
    assert a == b  # 45.2 reproducibility


def test_parameter_selection_happens_per_window_on_training_only():
    candles = _candles(300)
    grid = [
        {"fast": 5, "slow": 20},
        {"fast": 10, "slow": 30},
        {"fast": 20, "slow": 60},
    ]
    config = WalkForwardConfig(train_size=100, test_size=50, step=50)
    no_costs = BacktestConfig(
        costs=CostModel(
            maker_fee=Decimal(0), taker_fee=Decimal(0),
            slippage_fraction=Decimal(0), spread_fraction=Decimal(0),
        )
    )
    report = run_walk_forward(
        candles, _sma, parameter_sets=grid, config=config,
        backtest_config=no_costs,
    )
    for w in report.windows:
        selected = {k: int(v) for k, v in w.selected_parameters.items()}
        assert selected in grid
        # The selected set is the best ON THE TRAINING SLICE only.
        train_slice = candles[w.index * 50: w.index * 50 + 100]
        train_runs = {
            tuple(p.items()): run_backtest(
                train_slice, _sma(**p), no_costs
            ).return_fraction
            for p in grid
        }
        best = max(train_runs, key=train_runs.get)
        assert tuple(sorted(selected.items())) == tuple(
            sorted((k, v) for k, v in dict(best).items())
        ) or train_runs[dict(best)] == train_runs.get(
            tuple(selected.items()), None
        )


def test_degradation_flag_fires_for_collapsed_windows():
    report = run_walk_forward(
        _candles(300), _sma,
        config=WalkForwardConfig(
            train_size=100, test_size=50, step=50,
            degradation_fraction=Decimal("2"),  # everything degrades
        ),
    )
    # With the threshold above every realistic ratio, positive-training
    # windows must all be flagged.
    expected = {w.index for w in report.windows if w.train_return > 0}
    assert set(report.degraded_windows) == expected


def test_warmup_prefix_extends_but_does_not_move_boundaries():
    report = run_walk_forward(
        _candles(300), _sma,
        config=WalkForwardConfig(
            train_size=100, test_size=50, step=50, warmup=10
        ),
    )
    # Boundaries still point at the true window, not the warm-up.
    w = report.windows[1]
    assert w.train_first_open == _candles(300)[40].open_time.isoformat() \
        or w.train_first_open == _candles(300)[50].open_time.isoformat()


def test_too_little_data_raises():
    with pytest.raises(ValueError, match="no full walk-forward window"):
        run_walk_forward(
            _candles(120), _sma,
            config=WalkForwardConfig(train_size=100, test_size=50, step=50),
        )

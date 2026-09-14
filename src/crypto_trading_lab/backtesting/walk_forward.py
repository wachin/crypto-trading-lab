"""Walk-forward analysis (ROADMAP.md chapter 45).

Rolling evaluation: train on a window, evaluate on the forward window
that follows it, move, repeat. Every window is recorded with its exact
boundaries and the parameters selected *inside that window*, the
per-window results are shown as a distribution (not only an
aggregate), and the answer is deterministic — re-running with
identical inputs produces identical results (45.2).

Walk-forward is **not** the simple train/validation/test split of
chapter 38, and it is not CPCV (45.3, research): it follows one
chronological path through history.

Aggregation note: the aggregate return stitches window returns by
compounding a unit stake per window — it is a summary across
conditions, not a simulation of one continuous portfolio.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Callable, Sequence

from crypto_trading_lab.domain.models import Candle
from crypto_trading_lab.backtesting.engine import BacktestConfig, run_backtest

__all__ = [
    "WalkForwardConfig",
    "WindowResult",
    "WalkForwardReport",
    "WALK_FORWARD_NOTE",
    "run_walk_forward",
]

WALK_FORWARD_NOTE = (
    "Walk-forward reduces the overfitting risk of a single historical "
    "test but does not eliminate it; aggregate results across windows "
    "are an observed distribution on past data, not proof of future "
    "profitability."
)


@dataclass(frozen=True)
class WalkForwardConfig:
    """Window definition (45.1). Sizes are candle counts."""

    train_size: int
    test_size: int
    step: int
    warmup: int = 0
    # Material-degradation threshold for the per-window flag (45.1):
    # the forward result degraded if it ends below this fraction of
    # the training-window return.
    degradation_fraction: Decimal = Decimal("0.5")

    def __post_init__(self) -> None:
        if self.train_size < 2 or self.test_size < 2 or self.step < 1:
            raise ValueError("invalid window sizes")

    def metadata(self) -> dict[str, str]:
        return {
            "train_size": str(self.train_size),
            "test_size": str(self.test_size),
            "step": str(self.step),
            "warmup": str(self.warmup),
            "degradation_fraction": str(self.degradation_fraction),
            "randomness": "none (deterministic window generation)",
        }


@dataclass(frozen=True)
class WindowResult:
    """One walk-forward window, fully recorded (45.1)."""

    index: int
    train_first_open: str
    train_last_close: str
    test_first_open: str
    test_last_close: str
    selected_parameters: dict[str, str]
    train_return: Decimal
    test_return: Decimal
    test_trades: int
    degraded: bool


@dataclass(frozen=True)
class WalkForwardReport:
    """Aggregate + per-window distribution (45.1, 45.2)."""

    windows: tuple[WindowResult, ...]
    aggregate_return: Decimal          # product of (1 + test r_i) - 1
    strategy_version: str
    dataset_version: str
    config_metadata: dict[str, str]
    note: str = WALK_FORWARD_NOTE

    @property
    def test_returns(self) -> tuple[Decimal, ...]:
        return tuple(w.test_return for w in self.windows)

    @property
    def degraded_windows(self) -> tuple[int, ...]:
        return tuple(w.index for w in self.windows if w.degraded)


def run_walk_forward(
    candles: Sequence[Candle],
    strategy_factory: Callable[..., object],
    parameter_sets: Sequence[dict] | None = None,
    config: WalkForwardConfig | None = None,
    backtest_config: BacktestConfig | None = None,
    strategy_version: str = "unknown",
    dataset_version: str = "unversioned (experiment tracking pending, ch. 53)",
) -> WalkForwardReport:
    """Run rolling train → forward-test windows (chapter 45).

    ``strategy_factory(**params)`` builds the strategy. When
    ``parameter_sets`` is given, each window *selects* the best set on
    its training slice only (best training total return — a limited,
    documented, window-local selection, not the chapter 39 optimizer)
    and evaluates it on the forward window. Later windows never inform
    earlier ones: the chronology of windows and the engine's
    no-look-ahead guarantee make leakage impossible by construction.
    """
    config = config or WalkForwardConfig(train_size=100, test_size=50, step=50)
    backtest_config = backtest_config or BacktestConfig()
    n = len(candles)

    windows: list[WindowResult] = []
    start = 0
    index = 0
    while start + config.train_size + config.test_size <= n:
        train_end = start + config.train_size
        test_end = train_end + config.test_size

        # Warm-up: borrow candles from BEFORE the window (45.1/38.1).
        train_start = max(0, start - config.warmup)
        train_slice = candles[train_start:train_end]
        test_slice = candles[max(0, train_end - config.warmup):test_end]

        candidates = parameter_sets if parameter_sets else [{}]
        best = None
        for params in candidates:
            run = run_backtest(
                train_slice, strategy_factory(**params), backtest_config
            )
            if best is None or run.return_fraction > best[0].return_fraction:
                best = (run, params)
        train_run, selected = best
        test_run = run_backtest(
            test_slice, strategy_factory(**selected), backtest_config
        )
        windows.append(
            WindowResult(
                index=index,
                train_first_open=candles[train_start].open_time.isoformat(),
                train_last_close=candles[train_end - 1].close_time.isoformat(),
                test_first_open=candles[train_end].open_time.isoformat(),
                test_last_close=candles[test_end - 1].close_time.isoformat(),
                selected_parameters={k: str(v) for k, v in selected.items()},
                train_return=train_run.return_fraction,
                test_return=test_run.return_fraction,
                test_trades=len(test_run.trades),
                degraded=(
                    train_run.return_fraction > 0
                    and test_run.return_fraction
                    < train_run.return_fraction * config.degradation_fraction
                ),
            )
        )
        start += config.step
        index += 1

    if not windows:
        raise ValueError(
            "no full walk-forward window fits the data "
            f"({n} candles, config {config.metadata()})"
        )

    aggregate = Decimal(1)
    for w in windows:
        aggregate *= Decimal(1) + w.test_return
    aggregate -= Decimal(1)

    return WalkForwardReport(
        windows=tuple(windows),
        aggregate_return=aggregate,
        strategy_version=strategy_version,
        dataset_version=dataset_version,
        config_metadata=config.metadata(),
    )

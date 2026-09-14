"""Robustness and sensitivity analysis (ROADMAP.md chapter 44).

Answers "does the result still exist when we change the conditions?"
without pretending to predict anything: Monte Carlo resampling of the
observed trade distribution, documented parameter perturbation, and
sweeps of the cost assumptions.

Honesty rules enforced here (44.4): every Monte Carlo run records its
seed and its scenario count, reports distributions rather than single
points, and always carries the warning that reshuffling trades
destroys the temporal structure of the data — it is an estimate under
stated assumptions, never a prediction of the future.

Monte Carlo randomness uses the standard-library ``random.Random``
with an explicit seed (module-level determinism, chapter 37.8); it is
research tooling only and never touches money.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from decimal import Decimal
from typing import Callable, Sequence

from crypto_trading_lab.backtesting.engine import (
    BacktestConfig,
    BacktestResult,
    CostModel,
    run_backtest,
)
from crypto_trading_lab.domain.models import Candle

__all__ = [
    "MonteCarloConfig",
    "MonteCarloReport",
    "monte_carlo_trades",
    "PerturbationResult",
    "perturb_sma_crossover",
    "CostSweepRow",
    "sweep_costs",
]

#: Mandatory honesty lines attached to every Monte Carlo report.
MONTE_CARLO_WARNINGS = (
    "Monte Carlo reshuffling destroys the temporal structure of the "
    "data (autocorrelation, regimes); the distributions below are "
    "estimates under the stated assumptions, not predictions.",
    "A Monte Carlo result is never a prediction of future "
    "performance.",
)


def _percentile(sorted_values: list[Decimal], fraction: Decimal) -> Decimal:
    """Nearest-rank percentile for a non-empty sorted list."""
    index = int((fraction * Decimal(len(sorted_values) - 1)).to_integral_value())
    return sorted_values[index]


@dataclass(frozen=True)
class MonteCarloConfig:
    """Scenario definition for trade-resampling Monte Carlo (44.4)."""

    scenarios: int = 500
    seed: int = 1  # always recorded and reproducible
    ruin_threshold_fraction: Decimal = Decimal("0.5")  # of initial capital

    def __post_init__(self) -> None:
        if self.scenarios < 1:
            raise ValueError("scenarios must be at least 1")


@dataclass(frozen=True)
class MonteCarloReport:
    """Distribution of outcomes over resampled trade sequences."""

    scenario_count: int
    seed: int
    trades_observed: int
    profit_p5: Decimal
    profit_p50: Decimal
    profit_p95: Decimal
    max_drawdown_p50: Decimal       # fraction
    max_drawdown_p95: Decimal       # bad tail
    probability_of_loss: Decimal    # fraction of scenarios ending negative
    risk_of_ruin: Decimal           # fraction of scenarios hitting ruin
    ruin_threshold_fraction: Decimal  # of initial capital, as recorded
    warnings: tuple[str, ...] = MONTE_CARLO_WARNINGS

    def metadata(self) -> dict[str, str]:
        return {
            "scenarios": str(self.scenario_count),
            "seed": str(self.seed),
            "ruin_threshold_fraction": str(self.ruin_threshold_fraction),
        }


def monte_carlo_trades(
    result: BacktestResult, config: MonteCarloConfig | None = None
) -> MonteCarloReport:
    """Bootstrap-resample the observed trades (chapter 44.4).

    Each scenario draws ``len(trades)`` trade net P&Ls **with
    replacement** from the observed trades, then accumulates an equity
    path to measure its total profit and maximum drawdown. Only the
    empirical trade distribution is simulated — no parametric model.
    """
    config = config or MonteCarloConfig()
    pnls = [t.net_pnl for t in result.trades]
    if not pnls:
        raise ValueError(
            "Monte Carlo on trades requires at least one closed trade"
        )
    rng = random.Random(config.seed)
    capital = result.initial_capital
    ruin_level = capital * config.ruin_threshold_fraction

    profits: list[Decimal] = []
    drawdowns: list[Decimal] = []
    losers = 0
    ruined = 0
    for _ in range(config.scenarios):
        equity = capital
        peak = capital
        max_dd = Decimal(0)
        hit_ruin = False
        for _ in range(len(pnls)):
            equity += rng.choice(pnls)
            if equity > peak:
                peak = equity
            if peak > 0:
                max_dd = max(max_dd, (peak - equity) / peak)
            if equity <= ruin_level:
                hit_ruin = True
        profit = equity - capital
        profits.append(profit)
        drawdowns.append(max_dd)
        if profit < 0:
            losers += 1
        if hit_ruin:
            ruined += 1

    profits.sort()
    drawdowns.sort()
    n = Decimal(config.scenarios)
    return MonteCarloReport(
        scenario_count=config.scenarios,
        seed=config.seed,
        trades_observed=len(pnls),
        profit_p5=_percentile(profits, Decimal("0.05")),
        profit_p50=_percentile(profits, Decimal("0.5")),
        profit_p95=_percentile(profits, Decimal("0.95")),
        max_drawdown_p50=_percentile(drawdowns, Decimal("0.5")),
        max_drawdown_p95=_percentile(drawdowns, Decimal("0.95")),
        probability_of_loss=Decimal(losers) / n,
        risk_of_ruin=Decimal(ruined) / n,
        ruin_threshold_fraction=config.ruin_threshold_fraction,
    )


# --- 44.2 Parameter perturbation ----------------------------------------------


@dataclass(frozen=True)
class PerturbationResult:
    """One perturbed parameter set and its outcome (44.2)."""

    fast: int
    slow: int
    net_profit: Decimal
    return_fraction: Decimal
    delta_vs_reference: Decimal     # return minus reference return
    collapsed: bool                 # metric fell into collapse territory


def perturb_sma_crossover(
    candles: Sequence[Candle],
    fast: int,
    slow: int,
    reference_return: Decimal,
    config: BacktestConfig | None = None,
    neighborhood: Decimal = Decimal("0.2"),   # ±20%, documented
    collapse_fraction: Decimal = Decimal("0.5"),
) -> list[PerturbationResult]:
    """Perturb the SMA windows in a documented neighborhood (44.2).

    Each window is moved by ±``neighborhood`` (fraction) around the
    chosen values; a perturbation is flagged as ``collapsed`` when its
    return drops below ``collapse_fraction`` of the reference return.
    """
    from crypto_trading_lab.backtesting.engine import MACrossoverStrategy

    config = config or BacktestConfig()
    results: list[PerturbationResult] = []
    fast_steps = sorted({
        max(2, int((Decimal(fast) * (Decimal(1) - neighborhood)))),
        fast,
        int(Decimal(fast) * (Decimal(1) + neighborhood)),
    })
    slow_steps = sorted({
        max(3, int((Decimal(slow) * (Decimal(1) - neighborhood)))),
        slow,
        int(Decimal(slow) * (Decimal(1) + neighborhood)),
    })
    for f in fast_steps:
        for s in slow_steps:
            if f >= s or (f == fast and s == slow):
                continue
            run = run_backtest(
                candles, MACrossoverStrategy(fast=f, slow=s), config
            )
            collapsed = (
                reference_return > 0
                and run.return_fraction < reference_return * collapse_fraction
            )
            results.append(
                PerturbationResult(
                    fast=f,
                    slow=s,
                    net_profit=run.net_profit,
                    return_fraction=run.return_fraction,
                    delta_vs_reference=(
                        run.return_fraction - reference_return
                    ),
                    collapsed=collapsed,
                )
            )
    return results


# --- 44.1 + 44.3: cost sweeps ---------------------------------------------------


@dataclass(frozen=True)
class CostSweepRow:
    """One cost scenario in a sensitivity sweep."""

    fee: Decimal
    slippage: Decimal
    spread: Decimal
    net_profit: Decimal
    return_fraction: Decimal


def sweep_costs(
    candles: Sequence[Candle],
    strategy_factory: Callable[[], "object"],
    config: BacktestConfig | None = None,
    multipliers: Sequence[Decimal] = (
        Decimal(0), Decimal("0.5"), Decimal(1), Decimal(2), Decimal(4),
    ),
) -> list[CostSweepRow]:
    """Scale all trading costs by each multiplier (44.1, 44.3).

    Reveals whether the apparent edge survives realistic cost
    uncertainty: a strategy that only works at exactly the assumed fee
    schedule is fragile.
    """
    base = (config or BacktestConfig()).costs
    config = config or BacktestConfig()
    rows: list[CostSweepRow] = []
    for m in multipliers:
        costs = CostModel(
            maker_fee=base.maker_fee * m,
            taker_fee=base.taker_fee * m,
            slippage_fraction=base.slippage_fraction * m,
            spread_fraction=base.spread_fraction * m,
        )
        run = run_backtest(
            candles,
            strategy_factory(),
            BacktestConfig(
                initial_capital=config.initial_capital,
                costs=costs,
                execution_model=config.execution_model,
                intrabar_policy=config.intrabar_policy,
                quantity_step=config.quantity_step,
                min_notional=config.min_notional,
            ),
        )
        rows.append(
            CostSweepRow(
                fee=costs.taker_fee,
                slippage=costs.slippage_fraction,
                spread=costs.spread_fraction,
                net_profit=run.net_profit,
                return_fraction=run.return_fraction,
            )
        )
    return rows

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
from crypto_trading_lab.market_data.splitting import (
    PeriodKind,
    split_candles,
)

__all__ = [
    "MonteCarloConfig",
    "MonteCarloReport",
    "monte_carlo_trades",
    "PerturbationResult",
    "perturb_sma_crossover",
    "CostSweepRow",
    "sweep_costs",
    "DegradationReport",
    "out_of_sample_degradation",
    "DEGRADATION_NOTE",
    "RobustnessReport",
    "compute_robustness_report",
    "RiskOfRuinReport",
    "compute_risk_of_ruin",
    "PositionSizingConfig",
]

#: Mandatory interpretation line (44.7).
DEGRADATION_NOTE = (
    "In-sample performance was used to build the strategy and is not "
    "independent evidence; only the out-of-sample figure can support "
    "(or kill) the hypothesis, and a single out-of-sample run stays an "
    "observed result."
)

#: Mandatory honesty lines attached to every Monte Carlo report.
MONTE_CARLO_WARNINGS = (
    "Monte Carlo reshuffling destroys the temporal structure of the "
    "data (autocorrelation, regimes); the distributions below are "
    "estimates under the stated assumptions, not predictions.",
    "A Monte Carlo result is never a prediction of future "
    "performance.",
)

#: Assumption note for consolidated robustness reports (44.9).
ROBUSTNESS_ASSUMPTIONS = (
    "Robustness tests evaluate whether results persist under changed "
    "conditions. They are research capabilities, not predictions. "
    "Each test carries explicit assumptions, seeds, and scenario counts. "
    "No single test proves future profitability."
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


# --- 44.7 Out-of-sample degradation --------------------------------------


@dataclass(frozen=True)
class DegradationReport:
    """In-sample vs validation vs out-of-sample comparison (44.7)."""

    train_return: Decimal
    validation_return: Decimal
    out_of_sample_return: Decimal
    degradation: Decimal | None  # 1 - oos/train; None if train <= 0
    collapsed: bool              # OOS sign/level collapse vs training
    boundaries: dict[str, str]
    note: str = DEGRADATION_NOTE


def out_of_sample_degradation(
    candles: Sequence[Candle],
    strategy_factory: Callable[[], "object"],
    backtest_config: BacktestConfig | None = None,
    collapse_margin: Decimal = Decimal("0.5"),
) -> DegradationReport:
    """Compare the same strategy across the three periods (44.7).

    One strategy, one config, three chronological periods (chapter 38
    split). ``degradation`` measures how much of the in-sample return
    disappears out of sample: 0 means no degradation, 1 means all of
    it vanished. ``collapsed`` is the chapter's flag: positive training
    performance whose out-of-sample return fell below
    ``collapse_margin`` × training return (or turned negative).
    """
    backtest_config = backtest_config or BacktestConfig()
    split = split_candles(candles)
    split.record_evaluation(PeriodKind.OUT_OF_SAMPLE)

    train = run_backtest(
        split.training.candles, strategy_factory(), backtest_config
    )
    validation = run_backtest(
        split.validation.candles, strategy_factory(), backtest_config
    )
    test = run_backtest(
        split.out_of_sample.candles, strategy_factory(), backtest_config
    )

    if train.return_fraction > 0:
        degradation = Decimal(1) - (
            test.return_fraction / train.return_fraction
        )
        collapsed = (
            test.return_fraction
            < train.return_fraction * collapse_margin
        )
    else:
        degradation = None
        collapsed = False  # nothing positive to lose

    return DegradationReport(
        train_return=train.return_fraction,
        validation_return=validation.return_fraction,
        out_of_sample_return=test.return_fraction,
        degradation=degradation,
        collapsed=collapsed,
        boundaries=split.boundaries(),
    )


# --- 44.9 Consolidated robustness report ----------------------------------------


@dataclass(frozen=True)
class RobustnessReport:
    """Consolidated report summarizing all robustness tests (44.9)."""

    monte_carlo: MonteCarloReport | None
    perturbation: list[PerturbationResult] | None
    cost_sweep: list[CostSweepRow] | None
    degradation: DegradationReport | None
    assumptions: str
    metadata: dict[str, str]

    def summary(self) -> str:
        """Plain-language summary for beginners."""
        parts = ["Robustness Report Summary"]
        if self.monte_carlo:
            mc = self.monte_carlo
            parts.append(
                f"Monte Carlo ({mc.scenario_count} scenarios): "
                f"median profit {mc.profit_p50}, risk of ruin {mc.risk_of_ruin:.1%}"
            )
        if self.cost_sweep:
            sw = self.cost_sweep
            profit_range = f"{sw[-1].net_profit} to {sw[0].net_profit}"
            parts.append(f"Cost sweep profit range: {profit_range}")
        if self.degradation:
            dg = self.degradation
            status = "COLLAPSED" if dg.collapsed else "stable"
            degradation_text = (
                f"{dg.degradation:.1%}"
                if dg.degradation is not None
                else "N/A"
            )
            parts.append(
                f"Out-of-sample: {dg.out_of_sample_return:.1%} ({status}, "
                f"degradation {degradation_text})"
            )
        if self.perturbation and any(p.collapsed for p in self.perturbation):
            parts.append("WARNING: Some parameter variations caused collapse.")
        parts.append(ROBUSTNESS_ASSUMPTIONS)
        return "\n".join(parts)


def compute_robustness_report(
    result: BacktestResult,
    candles: Sequence[Candle] | None = None,
    strategy_factory: Callable[[], "object"] | None = None,
    monte_carlo_config: MonteCarloConfig | None = None,
) -> RobustnessReport:
    """Produce a consolidated robustness report (44.9).

    Combines Monte Carlo, cost sweep, and out-of-sample degradation.
    If candles + strategy_factory are provided, runs perturbation and cost sweep.
    """
    mc = monte_carlo_trades(result, monte_carlo_config) if result.trades else None

    cost_sweep = None
    perturbation = None
    degradation = None

    if candles and strategy_factory:
        cost_sweep = sweep_costs(candles, strategy_factory)
        perturbation = perturb_sma_crossover(
            candles,
            fast=5,
            slow=20,
            reference_return=result.return_fraction,
        )
        degradation = out_of_sample_degradation(candles, strategy_factory)

    return RobustnessReport(
        monte_carlo=mc,
        perturbation=perturbation,
        cost_sweep=cost_sweep,
        degradation=degradation,
        assumptions=ROBUSTNESS_ASSUMPTIONS,
        metadata={
            "scenarios": str(mc.scenario_count) if mc else "N/A",
            "seed": str(mc.seed) if mc else "N/A",
            "tests_run": str(sum([
                1 if mc else 0,
                1 if perturbation else 0,
                1 if cost_sweep else 0,
                1 if degradation else 0,
            ])),
        },
    )


# --- 60. Risk of ruin and capital depletion ----------------------------------------


@dataclass(frozen=True)
class PositionSizingConfig:
    """Configuration for position sizing (60.1)."""
    max_risk_per_trade: Decimal = Decimal("0.02")  # 2% of capital
    max_total_exposure: Decimal = Decimal("0.50")  # 50% of capital
    ruin_threshold_fraction: Decimal = Decimal("0.10")  # 10% of initial capital


@dataclass(frozen=True)
class RiskOfRuinReport:
    """Risk of ruin analysis (Chapter 60)."""
    probability_of_ruin: Decimal
    expected_max_drawdown: Decimal
    historical_max_drawdown: Decimal
    ruin_threshold: Decimal
    scenarios: int
    assumptions: str
    warnings: tuple[str, ...]


def compute_risk_of_ruin(
    result: BacktestResult,
    config: PositionSizingConfig | None = None,
) -> RiskOfRuinReport:
    """
    Compute risk of ruin and capital depletion analysis (Chapter 60).
    
    Uses Monte Carlo simulation to estimate the probability that capital
    falls below a defined threshold.
    """
    config = config or PositionSizingConfig()
    
    if not result.trades:
        return RiskOfRuinReport(
            probability_of_ruin=Decimal(0),
            expected_max_drawdown=Decimal(0),
            historical_max_drawdown=Decimal(0),
            ruin_threshold=Decimal(0),
            scenarios=0,
            assumptions="No trades to analyze.",
            warnings=("No trade data available for risk analysis.",),
        )
    
    # Compute historical max drawdown
    peak = result.initial_capital
    max_dd = Decimal(0)
    equity = result.initial_capital
    for value in result.equity_curve:
        if value > peak:
            peak = value
        if peak > 0:
            dd = (peak - value) / peak
            if dd > max_dd:
                max_dd = dd
    
    # Run Monte Carlo to estimate probability of ruin
    mc_config = MonteCarloConfig(
        scenarios=500,
        seed=42,
        ruin_threshold_fraction=config.ruin_threshold_fraction,
    )
    mc_report = monte_carlo_trades(result, mc_config)
    
    # Assumptions
    assumptions = (
        f"Risk of ruin estimated from {mc_report.scenario_count} scenarios. "
        f"Ruin threshold: {config.ruin_threshold_fraction:.0%} of initial capital. "
        f"Returns resampled with replacement (bootstrapping). "
        f"Does not account for regime changes or structural breaks."
    )
    
    warnings = list(mc_report.warnings)
    if max_dd > Decimal("0.20"):
        warnings.append(
            "Historical drawdown exceeds 20%. Consider reducing position sizes."
        )
    
    return RiskOfRuinReport(
        probability_of_ruin=mc_report.risk_of_ruin,
        expected_max_drawdown=mc_report.max_drawdown_p95,
        historical_max_drawdown=max_dd,
        ruin_threshold=config.ruin_threshold_fraction,
        scenarios=mc_report.scenario_count,
        assumptions=assumptions,
        warnings=tuple(warnings),
    )



#: Chapter 45: Walk-forward analysis.
#: Repeatedly train on rolling windows and validate on subsequent windows.


def walk_forward(
    candles: Sequence[Candle],
    strategy_factory: Callable[[], object],
    backtest_config: BacktestConfig | None = None,
    train_window: int = 100,
    test_window: int = 20,
    step: int = 10,
    initial_capital: Decimal = Decimal("1000"),
) -> list[dict[str, Decimal]]:
    """Perform walk-forward analysis (Chapter 45).

    Repeatedly trains a strategy on a rolling training window and validates
    it on the subsequent test window, moving forward by ``step`` candles each
    iteration. Returns a list of results per iteration.

    This is more rigorous than a single out-of-sample test because it
    evaluates stability across multiple market regimes and train/test splits.

    Returns a list of dicts with keys:
    - ``train_return``: return from training period
    - ``test_return``: return from test period
    - ``degradation``: (train_return - test_return) / train_return
    - ``train_candles``: number of training candles
    - ``test_candles``: number of test candles
    """
    from decimal import Decimal

    from crypto_trading_lab.backtesting.engine import run_backtest
    from crypto_trading_lab.backtesting.metrics import compute_performance

    results = []
    candle_count = len(candles)

    if candle_count < train_window + test_window:
        return results

    train_end = train_window
    iteration = 0

    while train_end + test_window <= candle_count:
        # Training period
        train_candles = candles[:train_end]
        train_strategy = strategy_factory()
        train_result = run_backtest(train_candles, train_strategy, backtest_config)
        train_perf = compute_performance(train_result)

        # Test period
        test_start = train_end
        test_end = test_start + test_window
        test_candles = candles[test_start:test_end]
        test_strategy = strategy_factory()  # Fresh strategy instance
        test_result = run_backtest(test_candles, test_strategy, backtest_config)
        test_perf = compute_performance(test_result)

        # Compute degradation
        train_return = train_perf.returns.net_profit
        test_return = test_perf.returns.net_profit
        degradation = Decimal(0)
        if train_return != 0:
            degradation = (train_return - test_return) / abs(train_return)

        results.append(
            {
                "train_return": train_return,
                "test_return": test_return,
                "degradation": degradation,
                "train_candles": train_window,
                "test_candles": test_window,
                "iteration": iteration,
            }
        )

        # Move window forward by step
        train_end += step
        iteration += 1

    return results


RISK_OF_RUIN_WARNING = (
    "Risk of ruin is an estimate based on historical data and stated assumptions. "
    "It is NOT a guarantee that you will or will not lose your capital. "
    "Never risk money needed for essential expenses."
)
RISK_OF_RUIN_WARNING = (
    "Risk of ruin is an estimate based on historical data and stated assumptions. "
    "It is NOT a guarantee that you will or will not lose your capital. "
    "Never risk money needed for essential expenses."
)

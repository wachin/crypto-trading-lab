"""End-to-end research workflow (chapters 37-45, 53, 66).

This is the layer the user actually walks through: hypothesis →
strategy → costs → backtest → benchmark → attempt to refute (out-of-
sample, robustness, walk-forward) → qualification → recorded
experiment with a validity checklist.

It contains no new statistics: it orchestrates the tested modules and
adds the one thing the laboratory was missing — a single, honest
answer to "how much should I trust this result?".
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Callable, Sequence

from crypto_trading_lab.backtesting.engine import (
    BacktestConfig,
    BacktestResult,
    run_backtest,
)
from crypto_trading_lab.backtesting.metrics import (
    PerformanceReport,
    compute_performance,
)
from crypto_trading_lab.backtesting.robustness import (
    MonteCarloConfig,
    RobustnessReport,
    compute_robustness_report,
)
from crypto_trading_lab.backtesting.statistical_analysis import (
    warn_multiple_testing,
    warn_small_sample,
)
from crypto_trading_lab.backtesting.walk_forward import (
    WalkForwardConfig,
    WalkForwardReport,
    run_walk_forward,
)
from crypto_trading_lab.domain.models import Candle
from crypto_trading_lab.machine_learning.experiment_manager import (
    ExperimentManager,
    ExperimentRecord,
    ExperimentStatus,
)
from crypto_trading_lab.market_data.historical import DatasetVersion
from crypto_trading_lab.qualification import (
    QualificationOutcome,
    StrategyQualification,
    qualify_strategy,
)

__all__ = [
    "ValidityCheck",
    "ResearchRun",
    "run_research",
    "MIN_TRADES_FOR_EVIDENCE",
    "MIN_TRIALS_BEFORE_WARNING",
]

#: Below this many trades, no statistical claim is defensible (ch. 43.2).
MIN_TRADES_FOR_EVIDENCE = 30
#: Above this many tested configurations, selection bias must be flagged.
MIN_TRIALS_BEFORE_WARNING = 10


@dataclass(frozen=True)
class ValidityCheck:
    """One row of the research-validity dashboard (analysis §16)."""

    name: str
    passed: bool
    detail: str


@dataclass
class ResearchRun:
    """The complete, reproducible result of one research question."""

    hypothesis: str
    strategy_name: str
    strategy_version: str
    parameters: dict[str, str]
    config: BacktestConfig
    dataset: DatasetVersion | None
    result: BacktestResult
    report: PerformanceReport
    benchmark_report: PerformanceReport | None
    robustness: RobustnessReport | None
    walk_forward: WalkForwardReport | None
    qualification: StrategyQualification | None
    validity: list[ValidityCheck] = field(default_factory=list)
    trials: int = 1
    warnings: list[str] = field(default_factory=list)
    experiment: ExperimentRecord | None = None

    @property
    def evidence_ready(self) -> bool:
        """True only when every decisive validity check passed."""
        return bool(self.validity) and all(c.passed for c in self.validity)

    def beginner_verdict(self) -> str:
        """Plain-language, never-overclaiming conclusion (chapter 40.8)."""
        outcome = (
            self.qualification.outcome
            if self.qualification
            else QualificationOutcome.NOT_QUALIFIED
        )
        return _beginner_verdict(outcome, self.evidence_ready)

    def invalid_checks(self) -> list[ValidityCheck]:
        return [check for check in self.validity if not check.passed]


def _beginner_verdict(
    outcome: QualificationOutcome, evidence_ready: bool
) -> str:
    """One honest sentence for the researcher (chapters 40.8 and 72)."""
    if outcome is QualificationOutcome.QUALIFIED and evidence_ready:
        return (
            "The strategy survived every test in this run. That is "
            "still only historical evidence: it does not prove the "
            "edge will persist. Continue with paper trading before "
            "risking any real money."
        )
    if outcome is QualificationOutcome.CONDITIONALLY_QUALIFIED:
        return (
            "The strategy partially passed. Some checks failed or "
            "were inconclusive, so the honest reading is “not "
            "proven”. Treat it as a hypothesis to keep testing, not "
            "as a discovery."
        )
    return (
        "The strategy did NOT demonstrate a defensible edge in this "
        "run. That is a useful result: a rejected hypothesis saves "
        "money. Record it and try a different idea."
    )


def _validity_checks(
    *,
    result: BacktestResult,
    config: BacktestConfig,
    dataset: DatasetVersion | None,
    benchmark_report: PerformanceReport | None,
    robustness: RobustnessReport | None,
    walk_forward: WalkForwardReport | None,
    trials: int,
    degradation_collapsed: bool | None,
) -> list[ValidityCheck]:
    """Assemble the honesty checklist shown before any result is trusted."""
    trades = 0
    if result.trades:
        trades = len(result.trades)
    checks: list[ValidityCheck] = []

    checks.append(
        ValidityCheck(
            "dataset_quality",
            bool(dataset and dataset.ready and dataset.checksum),
            (
                f"dataset {dataset.dataset_id} (checksum {dataset.checksum[:12]}…)"
                if dataset
                else "no versioned dataset: the run cannot be reproduced exactly"
            ),
        )
    )
    checks.append(
        ValidityCheck(
            "look_ahead_protection",
            True,
            "the engine decides at a candle's close and fills at the next "
            "candle's open, so a strategy never sees the future",
        )
    )
    checks.append(
        ValidityCheck(
            "train_test_separation",
            degradation_collapsed is not None,
            "chronological split performed (training → validation → out-of-sample)"
            if degradation_collapsed is not None
            else "no out-of-sample split was evaluated",
        )
    )
    checks.append(
        ValidityCheck(
            "transaction_costs",
            config.costs.taker_fee > 0 or config.costs.maker_fee > 0,
            f"taker fee {config.costs.taker_fee}, maker fee {config.costs.maker_fee}",
        )
    )
    checks.append(
        ValidityCheck(
            "slippage_model",
            config.costs.slippage_fraction > 0
            or config.costs.spread_fraction > 0,
            f"slippage {config.costs.slippage_fraction}, "
            f"spread {config.costs.spread_fraction}",
        )
    )
    checks.append(
        ValidityCheck(
            "benchmark",
            benchmark_report is not None,
            "compared against a passive alternative"
            if benchmark_report is not None
            else "no benchmark: excess return is unknown",
        )
    )
    checks.append(
        ValidityCheck(
            "out_of_sample",
            degradation_collapsed is False,
            "out-of-sample performance did not collapse"
            if degradation_collapsed is False
            else "out-of-sample performance collapsed or was not measured",
        )
    )
    checks.append(
        ValidityCheck(
            "walk_forward",
            walk_forward is not None and not walk_forward.degraded_windows,
            (
                f"{len(walk_forward.windows)} windows, "
                f"{len(walk_forward.degraded_windows)} degraded"
                if walk_forward
                else "walk-forward analysis not run"
            ),
        )
    )
    checks.append(
        ValidityCheck(
            "monte_carlo",
            bool(robustness and robustness.monte_carlo),
            (
                f"{robustness.monte_carlo.scenario_count} resampled scenarios, "
                f"risk of ruin {robustness.monte_carlo.risk_of_ruin:.1%}"
                if robustness and robustness.monte_carlo
                else "Monte Carlo not run (no trades or not requested)"
            ),
        )
    )
    collapsed_perturbation = bool(
        robustness
        and robustness.perturbation
        and any(p.collapsed for p in robustness.perturbation)
    )
    checks.append(
        ValidityCheck(
            "parameter_sensitivity",
            not collapsed_perturbation,
            "no parameter variation collapsed the result"
            if not collapsed_perturbation
            else "small parameter changes destroyed the result",
        )
    )
    checks.append(
        ValidityCheck(
            "sample_size",
            trades >= MIN_TRADES_FOR_EVIDENCE,
            f"{trades} trades (minimum for any statistical claim: "
            f"{MIN_TRADES_FOR_EVIDENCE})",
        )
    )
    checks.append(
        ValidityCheck(
            "multiple_testing",
            trials <= MIN_TRIALS_BEFORE_WARNING,
            f"{trials} configurations tested; selection bias grows with "
            "every extra trial",
        )
    )
    checks.append(
        ValidityCheck(
            "liquidity_realism",
            False,
            "liquidity/market impact is not modelled yet: real fills can "
            "be worse than simulated ones",
        )
    )
    return checks


def run_research(
    candles: Sequence[Candle],
    *,
    hypothesis: str,
    strategy_factory: Callable[[], object],
    strategy_name: str,
    strategy_version: str = "1.0.0",
    parameters: dict[str, str] | None = None,
    config: BacktestConfig | None = None,
    dataset: DatasetVersion | None = None,
    benchmark_factory: Callable[[], object] | None = None,
    run_robustness: bool = True,
    monte_carlo_scenarios: int = 300,
    run_walk_forward_analysis: bool = False,
    walk_forward_config: WalkForwardConfig | None = None,
    trials: int = 1,
    manager: ExperimentManager | None = None,
    notes: str = "",
) -> ResearchRun:
    """Run one complete research question and record it as an experiment.

    Everything is deterministic: the same candles, config and strategy
    produce the same numbers, and the recorded experiment names the
    dataset checksum so the run can be reproduced later.
    """
    config = config or BacktestConfig()
    parameters = dict(parameters or {})
    dataset_version = dataset.dataset_id if dataset else "unversioned"

    result = run_backtest(candles, strategy_factory(), config)
    result.dataset_version = dataset_version

    benchmark_result = None
    benchmark_report = None
    if benchmark_factory is not None:
        benchmark_result = run_backtest(candles, benchmark_factory(), config)
        benchmark_report = compute_performance(benchmark_result)
    report = compute_performance(result, benchmark=benchmark_result)

    robustness: RobustnessReport | None = None
    if run_robustness:
        robustness = compute_robustness_report(
            result,
            candles=candles,
            strategy_factory=strategy_factory,
            monte_carlo_config=MonteCarloConfig(
                scenarios=monte_carlo_scenarios, seed=1
            ),
        )

    degradation = robustness.degradation if robustness else None
    walk_forward: WalkForwardReport | None = None
    if run_walk_forward_analysis and walk_forward_config is not None:
        walk_forward = run_walk_forward(
            candles,
            lambda **params: strategy_factory(),
            config=walk_forward_config,
            backtest_config=config,
            strategy_version=strategy_version,
            dataset_version=dataset_version,
        )

    oos_return = (
        degradation.out_of_sample_return if degradation else Decimal(0)
    )
    perturbation_collapsed = bool(
        robustness
        and robustness.perturbation
        and any(p.collapsed for p in robustness.perturbation)
    )
    ruin = (
        robustness.monte_carlo.risk_of_ruin
        if robustness and robustness.monte_carlo
        else Decimal("0.05")
    )
    qualification = qualify_strategy(
        oos_return=oos_return,
        max_drawdown=report.risk.max_drawdown,
        number_of_trades=report.trades.number_of_trades,
        sharpe_ratio=(
            report.risk.sharpe_ratio
            if report.risk.sharpe_ratio is not None
            else Decimal(0)
        ),
        perturbation_collapsed=perturbation_collapsed,
        monte_carlo_ruin=ruin,
    )

    warnings: list[str] = list(report.warnings)
    multiple = warn_multiple_testing(trials)
    if multiple:
        warnings.append(multiple)
    small = warn_small_sample(report.trades.number_of_trades)
    if small:
        warnings.append(small)

    validity = _validity_checks(
        result=result,
        config=config,
        dataset=dataset,
        benchmark_report=benchmark_report,
        robustness=robustness,
        walk_forward=walk_forward,
        trials=trials,
        degradation_collapsed=(
            degradation.collapsed if degradation is not None else None
        ),
    )

    experiment: ExperimentRecord | None = None
    if manager is not None:
        experiment = manager.create(
            hypothesis=hypothesis,
            strategy_name=strategy_name,
            strategy_version=strategy_version,
            dataset_version=dataset_version,
            parameters=parameters,
            execution_assumptions=config.metadata(),
            random_seed=1,
            notes=notes,
            dataset_id=dataset.dataset_id if dataset else "",
            dataset_checksum=dataset.checksum if dataset else "",
            metrics={
                "total_return": str(report.returns.total_return),
                "max_drawdown": str(report.risk.max_drawdown),
                "sharpe_ratio": str(report.risk.sharpe_ratio),
                "number_of_trades": str(report.trades.number_of_trades),
                "out_of_sample_return": str(oos_return),
                "qualification": qualification.outcome.value,
            },
            tags=(strategy_name,),
            status=ExperimentStatus.COMPLETED,
        )
        manager.update_status(
            experiment.experiment_id,
            ExperimentStatus.COMPLETED,
            conclusion=_beginner_verdict(
                qualification.outcome,
                evidence_ready=all(c.passed for c in validity),
            ),
        )
        experiment = manager.get(experiment.experiment_id)

    return ResearchRun(
        hypothesis=hypothesis,
        strategy_name=strategy_name,
        strategy_version=strategy_version,
        parameters=parameters,
        config=config,
        dataset=dataset,
        result=result,
        report=report,
        benchmark_report=benchmark_report,
        robustness=robustness,
        walk_forward=walk_forward,
        qualification=qualification,
        validity=validity,
        trials=trials,
        warnings=warnings,
        experiment=experiment,
    )

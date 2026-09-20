"""Research-validity dashboard (analysis §9 and §16).

Before a result is trusted, the user must see *how much* of the
research protocol was actually completed. This module renders that
checklist; it makes no new claims and never upgrades an observation
into evidence.

Rendering is pure text (``QCoreApplication.translate``), so it can be
unit-tested without a display and reused by the CLI.
"""

from __future__ import annotations

from PyQt6.QtCore import QCoreApplication
from PyQt6.QtWidgets import QTextBrowser, QVBoxLayout, QWidget

from crypto_trading_lab.research import ResearchRun

__all__ = [
    "render_validity",
    "render_qualification",
    "render_research_run",
    "ValidityDashboard",
]

_CONTEXT = "ValidityDashboard"


def _t(text: str) -> str:
    """Translate a source string in this module's context."""
    return QCoreApplication.translate(_CONTEXT, text)


def render_validity(run: ResearchRun) -> str:
    """Plain-text research-validity report."""
    lines: list[str] = [f"== {_t('RESEARCH VALIDITY')} =="]
    if not run.validity:
        lines.append(_t("No validation was performed for this run."))
        return "\n".join(lines)

    width = max(len(check.name) for check in run.validity)
    for check in run.validity:
        mark = "OK  " if check.passed else "WARN"
        lines.append(f"  [{mark}] {check.name.ljust(width)}  {check.detail}")

    failed = run.invalid_checks()
    lines.append("")
    if not failed:
        lines.append(
            _t(
                "Every check passed. This is still historical evidence, "
                "not a promise about the future."
            )
        )
    else:
        lines.append(
            _t(
                "Checks not satisfied: {count} of {total}. A result with "
                "unmet checks must not be presented as proof of an edge."
            ).format(count=len(failed), total=len(run.validity))
        )

    lines.append("")
    lines.append(
        _t("Evidence level: {level}").format(level=_evidence_level(run))
    )
    return "\n".join(lines)


def _evidence_level(run: ResearchRun) -> str:
    """Chapter 43.1 evidence ladder, in plain words."""
    if (
        run.evidence_ready
        and run.qualification
        and run.qualification.outcome.value == "qualified"
    ):
        return _t(
            "validated evidence (out-of-sample, robustness and "
            "qualification all passed)"
        )
    if run.walk_forward is not None or run.robustness is not None:
        return _t(
            "statistical evidence in progress (some refutation tests "
            "were run, others remain unmet)"
        )
    return _t(
        "observed result only (a single in-sample backtest is not "
        "statistical evidence)"
    )


def render_qualification(run: ResearchRun) -> str:
    """Qualification verdict and criteria (chapter 66)."""
    lines = [f"== {_t('QUALIFICATION')} =="]
    if run.qualification is None:
        lines.append(_t("No qualification was performed."))
        return "\n".join(lines)

    lines.append(
        _t("Outcome: {outcome}").format(
            outcome=run.qualification.outcome.value
        )
    )
    for criterion in run.qualification.criterion_results:
        mark = "OK  " if criterion.passed else "FAIL"
        lines.append(
            f"  [{mark}] {criterion.name}: {criterion.value} "
            f"(required {criterion.threshold})"
        )
    if run.qualification.failed_criteria:
        lines.append(
            _t("Failed criteria: {items}").format(
                items=", ".join(run.qualification.failed_criteria)
            )
        )
    lines.append("")
    lines.append(run.beginner_verdict())
    return "\n".join(lines)


def render_research_run(run: ResearchRun) -> str:
    """Full research report: what was tested, results, validity, verdict."""
    r = run.report.returns
    s = run.report.trades
    risk = run.report.risk
    lines = [
        f"== {_t('What was tested')} ==",
        _t("Hypothesis: {x}").format(x=run.hypothesis),
        _t("Strategy: {name} (version {version})").format(
            name=run.strategy_name, version=run.strategy_version
        ),
        _t("Dataset: {x}").format(
            x=run.dataset.dataset_id if run.dataset else _t("unversioned")
        ),
        "",
        f"== {_t('Observed result (not evidence)')} ==",
        _t("Total return: {x}").format(x=r.total_return),
        _t("Net profit/loss: {x}").format(x=r.net_profit),
        _t("Maximum drawdown: {x}").format(x=risk.max_drawdown),
        _t("Sharpe ratio: {x}").format(x=risk.sharpe_ratio),
        _t("Number of trades: {x}").format(x=s.number_of_trades),
        _t("Profit factor: {x}").format(x=s.profit_factor),
        "",
    ]
    lines.extend(render_validity(run).splitlines())
    lines.append("")
    lines.extend(render_qualification(run).splitlines())
    if run.warnings:
        lines.append("")
        lines.append(f"== {_t('Warnings')} ==")
        lines.extend(f"  - {w}" for w in run.warnings)
    return "\n".join(lines)


class ValidityDashboard(QWidget):
    """A read-only widget showing a research run's validity report."""

    def __init__(self, run: ResearchRun | None = None, parent=None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        self.view = QTextBrowser()
        layout.addWidget(self.view)
        if run is not None:
            self.set_run(run)

    def set_run(self, run: ResearchRun) -> str:
        text = render_research_run(run)
        self.view.setPlainText(text)
        return text

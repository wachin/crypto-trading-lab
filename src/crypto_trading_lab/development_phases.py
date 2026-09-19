"""Development phases (ROADMAP.md chapter 69).

Defines the development phases and progression criteria.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Any


class DevelopmentPhase(Enum):
    """Development phase enumeration (69.1)."""
    PHASE_0 = "phase_0_research"           # Research & foundation
    PHASE_1 = "phase_1_foundation"         # Core infrastructure
    PHASE_2 = "phase_2_data_charts"        # Data & charts
    PHASE_3 = "phase_3_backtesting"        # Backtesting & metrics
    PHASE_4 = "phase_4_research"           # Research infrastructure
    PHASE_5 = "phase_5_paper_trading"      # Paper trading & risk
    PHASE_6 = "phase_6_real_trading"       # Real trading activation
    PHASE_7 = "phase_7_production"         # Production hardening


@dataclass(frozen=True)
class PhaseCriteria:
    """Criteria for completing a development phase."""
    phase: DevelopmentPhase
    name: str
    description: str
    required_chapters: list[int]
    exit_criteria: list[str]
    quality_gates: list[str]


# Phase definitions per ROADMAP
PHASE_DEFINITIONS: dict[DevelopmentPhase, PhaseCriteria] = {
    DevelopmentPhase.PHASE_0: PhaseCriteria(
        phase=DevelopmentPhase.PHASE_0,
        name="Research & Foundation",
        description="Establish scientific principles, risk awareness, and project structure",
        required_chapters=list(range(1, 8)),
        exit_criteria=[
            "Scientific principles documented",
            "Risk warnings implemented",
            "Project structure established",
            "Architecture defined",
        ],
        quality_gates=[
            "No hardcoded secrets",
            "Type hints on all public APIs",
            "Test coverage > 80%",
        ],
    ),
    DevelopmentPhase.PHASE_1: PhaseCriteria(
        phase=DevelopmentPhase.PHASE_1,
        name="Core Infrastructure",
        description="Build core domain models, persistence, and configuration",
        required_chapters=list(range(7, 15)),
        exit_criteria=[
            "Domain models with Decimal precision",
            "SQLite persistence with migrations",
            "XDG configuration",
            "Credential security",
            "Logging with redaction",
        ],
        quality_gates=[
            "100% type coverage on domain models",
            "Migration tests pass",
            "Security audit passed",
        ],
    ),
    DevelopmentPhase.PHASE_2: PhaseCriteria(
        phase=DevelopmentPhase.PHASE_2,
        name="Data & Charts",
        description="Implement market data pipeline and charting",
        required_chapters=list(range(15, 33)),
        exit_criteria=[
            "CSV import with validation",
            "Multiple exchange adapters",
            "PyQtGraph charting backend",
            "Candlestick rendering",
        ],
        quality_gates=[
            "Chart performance < 100ms",
            "Import validation tests pass",
            "No look-ahead bias in charts",
        ],
    ),
    DevelopmentPhase.PHASE_3: PhaseCriteria(
        phase=DevelopmentPhase.PHASE_3,
        name="Backtesting & Metrics",
        description="Build deterministic backtesting engine with full metrics",
        required_chapters=list(range(33, 52)),
        exit_criteria=[
            "Deterministic backtesting engine",
            "All Chapter 40 metrics implemented",
            "Walk-forward analysis",
            "Monte Carlo robustness",
            "Triple-barrier labeling",
        ],
        quality_gates=[
            "Deterministic backtest results",
            "Metric accuracy validated",
            "No look-ahead bias",
            "Statistical tests pass",
        ],
    ),
    DevelopmentPhase.PHASE_4: PhaseCriteria(
        phase=DevelopmentPhase.PHASE_4,
        name="Research Infrastructure",
        description="Build research infrastructure for experimentation",
        required_chapters=[52, 53, 54, 55, 56],
        exit_criteria=[
            "Experiment manager",
            "Reproducibility framework",
            "Research notebooks",
            "AI assistant integration",
            "Execution realism",
        ],
        quality_gates=[
            "Experiments reproducible",
            "Notebooks export/import",
            "AI assistant functional",
        ],
    ),
    DevelopmentPhase.PHASE_5: PhaseCriteria(
        phase=DevelopmentPhase.PHASE_5,
        name="Paper Trading & Risk",
        description="Implement paper trading with full risk management",
        required_chapters=[57, 58, 59, 60, 61, 62, 63],
        exit_criteria=[
            "Paper trading engine",
            "Risk manager with limits",
            "Kill switch",
            "Capital protection",
            "Live monitoring",
            "Drift analysis",
        ],
        quality_gates=[
            "Paper trading matches backtest",
            "Risk limits enforced",
            "Kill switch tested",
        ],
    ),
    DevelopmentPhase.PHASE_5: PhaseCriteria(
        phase=DevelopmentPhase.PHASE_6,
        name="Real Trading Activation",
        description="Multi-step real trading activation with capital protection",
        required_chapters=[68],
        exit_criteria=[
            "Multi-step activation flow",
            "Capital protection active",
            "Safety gates operational",
            "Real trading indicator visible",
        ],
        quality_gates=[
            "Activation flow tested",
            "Capital protection verified",
            "Safety gates tested",
        ],
    ),
    DevelopmentPhase.PHASE_7: PhaseCriteria(
        phase=DevelopmentPhase.PHASE_7,
        name="Production Hardening",
        description="Production hardening and documentation",
        required_chapters=[69, 70, 71, 72],
        exit_criteria=[
            "Development phases documented",
            "Working method documented",
            "Research ethics documented",
            "Debian package built",
        ],
        quality_gates=[
            "All tests pass",
            "Documentation complete",
            "Package builds",
        ],
    ),
}


def get_current_phase(completed_chapters: set[int]) -> DevelopmentPhase:
    """Determine current development phase based on completed chapters."""
    for phase in reversed(list(DevelopmentPhase)):
        criteria = PHASE_DEFINITIONS[phase]
        if all(ch in completed_chapters for ch in criteria.required_chapters):
            return phase
    return DevelopmentPhase.PHASE_0


def get_phase_progress(completed_chapters: set[int]) -> dict[DevelopmentPhase, float]:
    """Calculate progress for each phase (0.0 to 1.0)."""
    progress = {}
    for phase, criteria in PHASE_DEFINITIONS.items():
        completed = sum(1 for ch in criteria.required_chapters if ch in completed_chapters)
        total = len(criteria.required_chapters)
        progress[phase] = completed / total if total > 0 else 1.0
    return progress


def get_next_milestone(completed_chapters: set[int]) -> tuple[DevelopmentPhase, list[int]]:
    """Get next phase and remaining chapters."""
    current = get_current_phase(completed_chapters)
    next_phase = DevelopmentPhase(list(DevelopmentPhase).index(current) + 1)
    if next_phase in PHASE_DEFINITIONS:
        criteria = PHASE_DEFINITIONS[next_phase]
        remaining = [ch for ch in criteria.required_chapters if ch not in completed_chapters]
        return next_phase, remaining
    return current, []


PHASE_WARNING = (
    "Development phases are guidelines, not guarantees. "
    "Progress through phases does not imply readiness for real trading. "
    "Each phase must be validated independently before proceeding."
)


__all__ = [
    "DevelopmentPhase",
    "PhaseCriteria",
    "PHASE_DEFINITIONS",
    "get_current_phase",
    "get_phase_progress",
    "get_next_milestone",
    "PHASE_WARNING",
]

"""Research ethics and honest reporting (ROADMAP.md chapter 72).

Implements ethical guidelines for financial research and trading system
development. Enforces honest reporting, proper disclaimers, and scientific
discipline.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Any


class EvidenceLevel(Enum):
    """Evidence level classification (72.1)."""
    OBSERVED_RESULT = "observed_result"           # Single in-sample backtest
    STATISTICAL_EVIDENCE = "statistical_evidence" # Validated with stats
    RESEARCH_HYPOTHESIS = "research_hypothesis"   # Unproven idea
    VALIDATED_EVIDENCE = "validated_evidence"     # Out-of-sample validated


class WarningType(Enum):
    """Warning type classification."""
    DRIFT = "drift"
    OVERFITTING = "overfitting"
    SAMPLE_SIZE = "sample_size"
    REGIME_CHANGE = "regime_change"
    LOOKAHEAD_BIAS = "lookahead_bias"
    DATA_SNOOPING = "data_snooping"
    MULTIPLE_TESTING = "multiple_testing"
    REGIME_DEPENDENCY = "regime_dependency"


@dataclass(frozen=True)
class EthicalWarning:
    """Ethical warning for research output."""
    warning_type: WarningType
    message: str
    severity: str  # "info", "warning", "critical"
    applicable_chapters: list[int]


@dataclass(frozen=True)
class EvidenceLabel:
    """Evidence level label for research output."""
    level: EvidenceLevel
    rationale: str
    limitations: list[str]
    assumptions: list[str]


@dataclass(frozen=True)
class Disclaimer:
    """Standard disclaimer for research output."""
    text: str
    category: str  # "performance", "risk", "general"


# Standard disclaimers per Chapter 72.2
STANDARD_DISCLAIMERS: dict[str, Disclaimer] = {
    "performance": Disclaimer(
        text=(
            "A profitable backtest is NOT proof of future profitability. "
            "Historical performance does not guarantee future results. "
            "Market conditions change and strategies that worked in the past "
            "may fail in the future."
        ),
        category="performance",
    ),
    "risk": Disclaimer(
        text=(
            "Trading cryptocurrencies involves substantial risk of loss. "
            "You can lose part or all of your invested capital. "
            "Most retail traders lose money. Trading is not a reliable "
            "source of income. Never trade money you cannot afford to lose. "
            "Never borrow money to trade."
        ),
        category="risk",
    ),
    "general": Disclaimer(
        text=(
            "This tool is for educational and research purposes only. "
            "It does not provide financial advice. "
            "All results are based on historical simulations with stated "
            "assumptions. Real trading involves additional risks including "
            "but not limited to: market gaps, liquidity crises, exchange "
            "failures, regulatory changes, and technological failures."
        ),
        category="general",
    ),
    "statistical": Disclaimer(
        text=(
            "Statistical evidence from backtests is model-dependent and "
            "assumes stationarity, independence, and correct model "
            "specification. Violations of these assumptions invalidate "
            "statistical conclusions. Out-of-sample validation does not "
            "guarantee future performance."
        ),
        category="statistical",
    ),
    "multiple_testing": Disclaimer(
        text=(
            "Multiple strategy configurations were tested. The more "
            "configurations tested, the higher the probability of finding "
            "a spurious profitable result by chance (False Discovery / "
            "False Strategy problem). Results must be corrected for "
            "multiple testing."
        ),
        category="statistical",
    ),
    "overfitting": Disclaimer(
        text=(
            "Strategies optimized on historical data are prone to "
            "overfitting. A strategy that appears profitable in backtest "
            "may simply have memorized noise. Out-of-sample and walk-forward "
            "validation are necessary but not sufficient safeguards."
        ),
        category="overfitting",
    ),
}


@dataclass(frozen=True)
class EthicalCheckResult:
    """Result of ethical compliance check."""
    compliant: bool
    violations: list[str]
    warnings: list[str]
    required_disclaimers: list[Disclaimer]


class EthicsChecker:
    """Checks research output for ethical compliance (Chapter 72)."""
    
    # Required disclaimers per output type
    REQUIRED_DISCLAIMERS = {
        "backtest_report": ["performance", "risk", "statistical", "overfitting"],
        "strategy_report": ["performance", "risk", "overfitting"],
        "optimization_report": ["statistical", "multiple_testing", "overfitting"],
        "live_trading": ["risk", "performance"],
        "research_paper": ["performance", "risk", "statistical", "overfitting", "multiple_testing"],
    }
    
    def __init__(self):
        self.violations: list[str] = []
        self.warnings: list[str] = []
    
    def check_report(self, report_type: str, content: str, metadata: dict) -> EthicalCheckResult:
        """Check a research report for ethical compliance."""
        self.violations = []
        self.warnings = []
        
        # Check required disclaimers
        required = self.REQUIRED_DISCLAIMERS.get(report_type, [])
        for disc_key in required:
            disc = STANDARD_DISCLAIMERS.get(disc_key)
            if disc and disc.text[:50] not in content:
                self.violations.append(f"Missing required disclaimer: {disc_key}")
        
        # Check for evidence level labeling
        if "evidence_level" not in metadata:
            self.warnings.append("Missing evidence level label (Chapter 72.1)")
        
        # Check for cherry-picking indicators
        if self._detect_cherry_picking(content):
            self.warnings.append("Possible cherry-picking detected")
        
        # Check for multiple testing acknowledgment
        if "multiple_testing" not in content.lower() and "optimization" in content.lower():
            self.warnings.append("Optimization detected without multiple testing correction")
        
        # Check for out-of-sample validation mention
        if "out_of_sample" not in content.lower() and "oos" not in content.lower():
            self.warnings.append("No out-of-sample validation mentioned")
        
        # Check for regime dependency acknowledgment
        if "regime" not in content.lower():
            self.warnings.append("No market regime dependency discussion")
        
        # Check for assumptions documentation
        if "assumptions" not in content.lower():
            self.warnings.append("Assumptions not explicitly documented")
        
        # Check for profit guarantees
        profit_guarantee_phrases = [
            "guaranteed profit", "guaranteed return", "risk-free profit",
            "guaranteed income", "sure profit", "certain profit"
        ]
        for phrase in profit_guarantee_phrases:
            if phrase in content.lower():
                self.violations.append(f"Profit guarantee language detected: '{phrase}'")
        
        # Check for financial advice disclaimer
        if "financial advice" not in content.lower() and "not financial advice" not in content.lower():
            self.warnings.append("Missing 'not financial advice' disclaimer")
        
        return EthicalCheckResult(
            compliant=len(self.violations) == 0,
            violations=self.violations,
            warnings=self.warnings,
            required_disclaimers=[STANDARD_DISCLAIMERS[k] for k in required],
        )
    
    def _detect_cherry_picking(self, content: str) -> bool:
        """Detect possible cherry-picking indicators."""
        cherry_pick_indicators = [
            "best period", "selected period", "cherry-picked",
            "optimal period", "best performing", "only period",
            "exceptional period", "outlier period"
        ]
        content_lower = content.lower()
        return any(indicator in content_lower for indicator in cherry_pick_indicators)
    
    def generate_required_disclaimers(self, report_type: str) -> list[Disclaimer]:
        """Generate required disclaimers for a report type."""
        keys = self.REQUIRED_DISCLAIMERS.get(report_type, [])
        return [STANDARD_DISCLAIMERS[k] for k in keys if k in STANDARD_DISCLAIMERS]


def generate_evidence_label(
    evidence_level: EvidenceLevel,
    rationale: str,
    limitations: list[str] | None = None,
    assumptions: list[str] | None = None,
) -> EvidenceLabel:
    """Generate evidence level label for research output (72.1)."""
    return EvidenceLabel(
        level=evidence_level,
        rationale=rationale,
        limitations=limitations or [],
        assumptions=assumptions or [],
    )


def format_evidence_label(label: EvidenceLabel) -> str:
    """Format evidence label for display."""
    lines = [
        f"Evidence Level: {label.level.value.replace('_', ' ').title()}",
        f"Rationale: {label.rationale}",
    ]
    if label.limitations:
        lines.append("Limitations:")
        for lim in label.limitations:
            lines.append(f"  - {lim}")
    if label.assumptions:
        lines.append("Assumptions:")
        for asm in label.assumptions:
            lines.append(f"  - {asm}")
    return "\n".join(lines)


ETHICS_WARNING = (
    "Ethical compliance is a continuous responsibility, not a checkbox. "
    "These tools assist but cannot replace human judgment. "
    "The researcher bears ultimate responsibility for honest reporting. "
    "When in doubt, err on the side of more disclosure and more caution."
)


__all__ = [
    "EvidenceLevel",
    "WarningType",
    "EthicalWarning",
    "EvidenceLabel",
    "Disclaimer",
    "STANDARD_DISCLAIMERS",
    "EthicalCheckResult",
    "EthicsChecker",
    "generate_evidence_label",
    "format_evidence_label",
    "ETHICS_WARNING",
]

"""Report ethics and honest reporting (ROADMAP.md chapter 72).

This module gives report generation a way to **fail** when a report would
be dishonest (a profit guarantee, a missing mandatory disclaimer) and to
carry honest warnings when it merely omits a discussion (no out-of-sample
validation, no market-regime analysis).

It was merged from the former top-level ``research_ethics`` module. The
evidence ladder itself lives in ``reporting/report.py`` (``EVIDENCE_LEVEL``)
and ``ui/research/validity.py``; duplicating it here was the reason the old
module was unwired.
"""

from __future__ import annotations

from dataclasses import dataclass

__all__ = [
    "Disclaimer",
    "STANDARD_DISCLAIMERS",
    "EthicalCheckResult",
    "EthicsError",
    "EthicsChecker",
    "ETHICS_WARNING",
]


class EthicsError(Exception):
    """Raised when a report would violate chapter 72."""


@dataclass(frozen=True)
class Disclaimer:
    """A standard disclaimer for research output."""

    text: str
    category: str  # "performance", "risk", "general", "statistical", ...


#: Standard disclaimers per Chapter 72.2. A category must exist here before
#: it can be required by a report type.
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

#: Phrases that promise a profit. Their presence is a hard violation.
PROFIT_GUARANTEE_PHRASES: tuple[str, ...] = (
    "guaranteed profit",
    "guaranteed return",
    "risk_free profit",
    "guaranteed income",
    "sure profit",
    "certain profit",
)


@dataclass(frozen=True)
class EthicalCheckResult:
    """Result of an ethical compliance check."""

    compliant: bool
    violations: list[str]
    warnings: list[str]
    required_disclaimers: list[Disclaimer]


class EthicsChecker:
    """Checks research output for ethical compliance (Chapter 72).

    The check is pure: the same content always yields the same result, and
    concurrent callers cannot interfere through instance state.
    """

    #: Which disclaimers each report type must carry.
    REQUIRED_DISCLAIMERS: dict[str, list[str]] = {
        "backtest_report": ["performance", "risk", "statistical", "overfitting"],
        "strategy_report": ["performance", "risk", "overfitting"],
        "optimization_report": ["statistical", "multiple_testing", "overfitting"],
        "live_trading": ["risk", "performance"],
        "research_paper": [
            "performance",
            "risk",
            "statistical",
            "overfitting",
            "multiple_testing",
        ],
    }

    def check_report(
        self, report_type: str, content: str, metadata: dict
    ) -> EthicalCheckResult:
        """Check a research report for ethical compliance."""
        normalised = content.lower().replace("-", "_")
        violations: list[str] = []
        warnings: list[str] = []

        required = self.REQUIRED_DISCLAIMERS.get(report_type, [])
        for key in required:
            disclaimer = STANDARD_DISCLAIMERS.get(key)
            if disclaimer is not None and disclaimer.text[:50] not in content:
                violations.append(f"Missing required disclaimer: {key}")

        for phrase in PROFIT_GUARANTEE_PHRASES:
            if phrase in normalised:
                violations.append(
                    f"Profit guarantee language detected: '{phrase}'"
                )

        if "evidence_level" not in metadata:
            warnings.append("Missing evidence level label (Chapter 72.1)")

        if self._detect_cherry_picking(normalised):
            warnings.append("Possible cherry-picking detected")

        if "multiple_testing" not in normalised and "optimization" in normalised:
            warnings.append(
                "Optimization detected without multiple testing correction"
            )

        # Hyphenated "out-of-sample" is the normal spelling; normalising the
        # hyphens first is what made this check miss it before.
        if "out_of_sample" not in normalised:
            warnings.append("No out-of-sample validation mentioned")

        if "regime" not in normalised:
            warnings.append("No market regime dependency discussion")

        if "assumption" not in normalised:
            warnings.append("Assumptions not explicitly documented")

        if "financial advice" not in normalised:
            warnings.append("Missing 'not financial advice' disclaimer")

        return EthicalCheckResult(
            compliant=not violations,
            violations=violations,
            warnings=warnings,
            required_disclaimers=[
                STANDARD_DISCLAIMERS[key]
                for key in required
                if key in STANDARD_DISCLAIMERS
            ],
        )

    @staticmethod
    def _detect_cherry_picking(normalised_content: str) -> bool:
        """Detect possible cherry-picking indicators."""
        indicators = (
            "best period",
            "selected period",
            "cherry_picked",
            "optimal period",
            "best performing",
            "only period",
            "exceptional period",
            "outlier period",
        )
        return any(indicator in normalised_content for indicator in indicators)

    def generate_required_disclaimers(self, report_type: str) -> list[Disclaimer]:
        """Return the disclaimers a report type must carry."""
        keys = self.REQUIRED_DISCLAIMERS.get(report_type, [])
        return [
            STANDARD_DISCLAIMERS[key]
            for key in keys
            if key in STANDARD_DISCLAIMERS
        ]


ETHICS_WARNING = (
    "Ethical compliance is a continuous responsibility, not a checkbox. "
    "These tools assist but cannot replace human judgment. "
    "The researcher bears ultimate responsibility for honest reporting. "
    "When in doubt, err on the side of more disclosure and more caution."
)

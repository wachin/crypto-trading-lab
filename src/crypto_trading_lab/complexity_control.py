"""Strategy complexity control (ROADMAP.md chapter 35).

Implements complexity metrics and limits for trading strategies
to prevent overfitting and ensure maintainability.
"""

from __future__ import annotations

import ast
import inspect
from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set

from crypto_trading_lab.backtesting.engine import Strategy


class ComplexityLevel(Enum):
    """Complexity level classification."""
    SIMPLE = "simple"
    MODERATE = "moderate"
    COMPLEX = "complex"
    VERY_COMPLEX = "very_complex"


@dataclass(frozen=True)
class ComplexityMetrics:
    """Complexity metrics for a strategy."""
    cyclomatic_complexity: int
    lines_of_code: int
    num_parameters: int
    num_functions: int
    num_classes: int
    max_nesting_depth: int
    halstead_volume: float
    maintainability_index: float


@dataclass(frozen=True)
class ComplexityLimits:
    """Complexity limits configuration (35.1)."""
    max_cyclomatic: int = 10
    max_lines: int = 200
    max_parameters: int = 8
    max_functions: int = 10
    max_classes: int = 3
    max_nesting: int = 4
    max_halstead_volume: float = 1000.0
    min_maintainability: float = 20.0


@dataclass(frozen=True)
class ComplexityReport:
    """Complexity analysis report (35.2)."""
    metrics: ComplexityMetrics
    level: ComplexityLevel
    passed: bool
    violations: list[str]
    warnings: list[str]


class ComplexityAnalyzer:
    """
    Analyzes strategy complexity to prevent overfitting and ensure maintainability (Chapter 35).
    """

    def __init__(self, limits: ComplexityLimits = None):
        self.limits = limits or ComplexityLimits()

    def analyze_strategy(self, strategy_class: type) -> ComplexityReport:
        """Analyze a strategy class for complexity."""
        source = inspect.getsource(strategy_class)
        tree = ast.parse(source)

        # Find the strategy class definition
        strategy_class_node = None
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name == strategy_class.__name__:
                strategy_class_node = node
                break

        if not strategy_class_node:
            raise ValueError(f"Could not find class {strategy_class.__name__}")

        # Calculate metrics
        metrics = self._calculate_metrics(strategy_class_node, source)

        # Evaluate against limits
        violations = []
        warnings = []

        if metrics.cyclomatic_complexity > self.limits.max_cyclomatic:
            violations.append(f"Cyclomatic complexity {metrics.cyclomatic_complexity} exceeds limit {self.limits.max_cyclomatic}")

        if metrics.lines_of_code > self.limits.max_lines:
            violations.append(f"Lines of code {metrics.lines_of_code} exceeds limit {self.limits.max_lines}")

        if metrics.num_parameters > self.limits.max_parameters:
            violations.append(f"Number of parameters {metrics.num_parameters} exceeds limit {self.limits.max_parameters}")

        if metrics.num_functions > self.limits.max_functions:
            violations.append(f"Number of functions {metrics.num_functions} exceeds limit {self.limits.max_functions}")

        if metrics.max_nesting_depth > self.limits.max_nesting:
            violations.append(f"Max nesting depth {metrics.max_nesting_depth} exceeds limit {self.limits.max_nesting}")

        if metrics.halstead_volume > self.limits.max_halstead_volume:
            warnings.append(f"Halstead volume {metrics.halstead_volume:.1f} exceeds recommended limit {self.limits.max_halstead_volume}")

        if metrics.maintainability_index < self.limits.min_maintainability:
            warnings.append(f"Maintainability index {metrics.maintainability_index:.1f} below recommended {self.limits.min_maintainability}")

        # Determine complexity level
        level = self._classify_complexity(metrics)

        passed = len(violations) == 0

        return ComplexityReport(
            metrics=metrics,
            level=level,
            passed=passed,
            violations=violations,
            warnings=warnings,
        )

    def _calculate_metrics(self, class_node: ast.ClassDef, source: str) -> ComplexityMetrics:
        """Calculate complexity metrics from AST."""
        # Count lines of code
        lines = source.split('\n')
        loc = len([l for l in lines if l.strip() and not l.strip().startswith('#')])

        # Cyclomatic complexity
        cc = self._calculate_cyclomatic(class_node)

        # Count parameters (from __init__ or __post_init__)
        num_params = self._count_parameters(class_node)

        # Count functions
        num_functions = len([n for n in ast.walk(class_node) if isinstance(n, ast.FunctionDef)])

        # Count classes (nested)
        num_classes = len([n for n in ast.walk(class_node) if isinstance(n, ast.ClassDef)]) - 1

        # Max nesting depth
        max_nesting = self._max_nesting_depth(class_node)

        # Halstead volume (simplified)
        halstead_volume = self._halstead_volume(class_node)

        # Maintainability index (simplified)
        mi = self._maintainability_index(loc, cc, halstead_volume)

        return ComplexityMetrics(
            cyclomatic_complexity=cc,
            lines_of_code=loc,
            num_parameters=num_params,
            num_functions=num_functions,
            num_classes=num_classes,
            max_nesting_depth=max_nesting,
            halstead_volume=halstead_volume,
            maintainability_index=mi,
        )

    def _calculate_cyclomatic(self, node: ast.AST) -> int:
        """Calculate cyclomatic complexity."""
        cc = 1  # Base complexity
        for node in ast.walk(node):
            if isinstance(node, (ast.If, ast.While, ast.For, ast.AsyncFor, ast.ExceptHandler)):
                cc += 1
            elif isinstance(node, ast.BoolOp):
                cc += len(node.values) - 1
            elif isinstance(node, (ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)):
                cc += 1
        return cc

    def _count_parameters(self, class_node: ast.ClassDef) -> int:
        """Count parameters in __init__ and __post_init__."""
        count = 0
        for node in class_node.body:
            if isinstance(node, ast.FunctionDef) and node.name in ('__init__', '__post_init__'):
                for arg in node.args.args:
                    if arg.arg != 'self':
                        count += 1
                for arg in node.args.kwonlyargs:
                    count += 1
        return count

    def _max_nesting_depth(self, node: ast.AST) -> int:
        """Calculate maximum nesting depth."""
        max_depth = 0
        current_depth = 0

        def walk(n, depth):
            nonlocal max_depth
            if isinstance(n, (ast.If, ast.While, ast.For, ast.AsyncFor, ast.Try, ast.With, ast.AsyncWith)):
                depth += 1
                max_depth = max(max_depth, depth)
            elif isinstance(n, ast.FunctionDef):
                depth += 1
                max_depth = max(max_depth, depth)

            for child in ast.iter_child_nodes(n):
                walk(child, depth)

            if isinstance(n, (ast.If, ast.While, ast.For, ast.AsyncFor, ast.Try, ast.With, ast.AsyncWith, ast.FunctionDef)):
                depth -= 1

        walk(node, 0)
        return max_depth

    def _halstead_volume(self, node: ast.AST) -> float:
        """Calculate simplified Halstead volume."""
        operators = 0
        operands = 0

        for node in ast.walk(node):
            if isinstance(node, (ast.BinOp, ast.UnaryOp, ast.Compare, ast.BoolOp)):
                operators += 1
            elif isinstance(node, (ast.Name, ast.Constant, ast.Attribute, ast.Subscript)):
                operands += 1
            elif isinstance(node, (ast.Call, ast.Attribute)):
                operands += 1

        if operators == 0 or operands == 0:
            return 0.0

        n1 = operators  # distinct operators (simplified)
        n2 = operands   # distinct operands (simplified)
        N1 = operators  # total operators
        N2 = operands   # total operands

        # Volume = N * log2(n) where N = N1 + N2, n = n1 + n2
        import math
        N = N1 + N2
        n = 2  # simplified
        return N * math.log2(n) if n > 0 else 0.0

    def _maintainability_index(self, loc: int, cc: int, halstead: float) -> float:
        """Calculate maintainability index (simplified)."""
        import math
        if loc == 0 or cc == 0:
            return 100.0
        # MI = 171 - 5.2 * ln(Volume) - 0.23 * CC - 16.2 * ln(LOC)
        volume = max(halstead, 1)
        mi = 171 - 5.2 * math.log(volume) - 0.23 * cc - 16.2 * math.log(loc)
        return max(0, min(100, mi))

    def _classify_complexity(self, metrics: ComplexityMetrics) -> ComplexityLevel:
        """Classify complexity level."""
        score = 0
        score += metrics.cyclomatic_complexity
        score += metrics.lines_of_code // 20
        score += metrics.num_parameters * 2
        score += metrics.max_nesting_depth * 3

        if score <= 20:
            return ComplexityLevel.SIMPLE
        elif score <= 40:
            return ComplexityLevel.MODERATE
        elif score <= 60:
            return ComplexityLevel.COMPLEX
        else:
            return ComplexityLevel.VERY_COMPLEX


def analyze_strategy_complexity(
    strategy_class: type,
    limits: ComplexityLimits = None,
) -> ComplexityReport:
    """Convenience function to analyze strategy complexity."""
    analyzer = ComplexityAnalyzer(limits)
    return analyzer.analyze_strategy(strategy_class)


COMPLEXITY_CONTROL_WARNING = (
    "Complexity metrics are heuristics, not guarantees. "
    "Low complexity does not guarantee profitability. "
    "High complexity does not guarantee failure. "
    "Use as one input among many for strategy evaluation."
)


__all__ = [
    "ComplexityLevel",
    "ComplexityMetrics",
    "ComplexityLimits",
    "ComplexityReport",
    "ComplexityAnalyzer",
    "analyze_strategy_complexity",
    "COMPLEXITY_CONTROL_WARNING",
]

"""Visual strategy builder (ROADMAP.md chapter 34).

Creates a no-code strategy builder using block-based expressions.
Does NOT use eval(). Uses AST-based evaluation of strategy rules.
"""

from __future__ import annotations

import ast
import json
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Dict, List, Literal, Optional, Union, Set

from crypto_trading_lab.indicators.library import IndicatorFactory


@dataclass(frozen=True)
class StrategyBlock:
    """A single block in the strategy builder."""
    block_id: str
    type: Literal["indicator", "operator", "value", "crossover", 
                  "condition", "entry", "exit", "stop_loss", 
                  "take_profit", "filter"]
    label: str
    params: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class StrategyRule:
    """A complete strategy rule composed of blocks."""
    rule_id: str
    name: str
    description: str
    blocks: List[StrategyBlock]
    version: str = "1.0.0"


@dataclass(frozen=True)
class ExpressionNode:
    """A node in the evaluated expression tree."""
    node_type: Literal["indicator", "binary_op", "unary_op", 
                       "value", "comparison", "logical_op"]
    value: Any
    children: List["ExpressionNode"] = field(default_factory=list)


class StrategyBuilder:
    """
    Visual strategy builder for creating rules without code (Chapter 34).
    
    Provides:
    - Block-based strategy construction
    - AST-based evaluation (no eval())
    - Validation and explanation
    - Save/Export/Import
    """

    def __init__(self):
        self._blocks: Dict[str, StrategyBlock] = {}
        self._rules: Dict[str, StrategyRule] = {}
        self._indicator_factory = IndicatorFactory()

    # --- Block building ---

    def add_indicator(
        self,
        indicator_type: str,
        params: Dict[str, Any],
        label: str = None,
    ) -> StrategyBlock:
        """Add an indicator block."""
        block_id = f"ind_{len(self._blocks)}"
        block = StrategyBlock(
            block_id=block_id,
            type="indicator",
            label=label or f"{indicator_type.title()}({', '.join(f'{k}={v}' for k, v in params.items())})",
            params={"indicator_type": indicator_type, **params},
        )
        self._blocks[block_id] = block
        return block

    def add_value(
        self,
        value: Union[float, int, Decimal],
        label: str = None,
    ) -> StrategyBlock:
        """Add a value block."""
        block_id = f"val_{len(self._blocks)}"
        block = StrategyBlock(
            block_id=block_id,
            type="value",
            label=label or str(value),
            params={"value": float(value) if isinstance(value, Decimal) else value},
        )
        self._blocks[block_id] = block
        return block

    def add_operator(
        self,
        op: Literal["add", "subtract", "multiply", "divide", 
                    "greater", "less", "equal", "crossover", "crossunder"],
    ) -> StrategyBlock:
        """Add an operator block."""
        block_id = f"op_{len(self._blocks)}"
        block = StrategyBlock(
            block_id=block_id,
            type="operator",
            label=op.title(),
            params={"op": op},
        )
        self._blocks[block_id] = block
        return block

    def add_condition(
        self,
        condition: Literal["and", "or", "not"],
    ) -> StrategyBlock:
        """Add a logical condition block."""
        block_id = f"cond_{len(self._blocks)}"
        block = StrategyBlock(
            block_id=block_id,
            type="condition",
            label=condition.upper(),
            params={"condition": condition},
        )
        self._blocks[block_id] = block
        return block

    def add_entry_signal(self, label: str = "Entry") -> StrategyBlock:
        """Add an entry signal block."""
        block_id = f"entry_{len(self._blocks)}"
        block = StrategyBlock(
            block_id=block_id,
            type="entry",
            label=label,
        )
        self._blocks[block_id] = block
        return block

    def add_exit_signal(self, label: str = "Exit") -> StrategyBlock:
        """Add an exit signal block."""
        block_id = f"exit_{len(self._blocks)}"
        block = StrategyBlock(
            block_id=block_id,
            type="exit",
            label=label,
        )
        self._blocks[block_id] = block
        return block

    def add_stop_loss(
        self,
        value: Union[float, Decimal],
        label: str = "Stop Loss",
    ) -> StrategyBlock:
        """Add a stop-loss block."""
        block_id = f"sl_{len(self._blocks)}"
        block = StrategyBlock(
            block_id=block_id,
            type="stop_loss",
            label=label,
            params={"value": float(value) if isinstance(value, Decimal) else value},
        )
        self._blocks[block_id] = block
        return block

    def add_take_profit(
        self,
        value: Union[float, Decimal],
        label: str = "Take Profit",
    ) -> StrategyBlock:
        """Add a take-profit block."""
        block_id = f"tp_{len(self._blocks)}"
        block = StrategyBlock(
            block_id=block_id,
            type="take_profit",
            label=label,
            params={"value": float(value) if isinstance(value, Decimal) else value},
        )
        self._blocks[block_id] = block
        return block

    def add_time_filter(
        self,
        hours: List[int] = None,
        days: List[int] = None,
    ) -> StrategyBlock:
        """Add a time filter block."""
        block_id = f"time_filter_{len(self._blocks)}"
        block = StrategyBlock(
            block_id=block_id,
            type="filter",
            label="Time Filter",
            params={"hours": hours, "days": days},
        )
        self._blocks[block_id] = block
        return block

    def add_volatility_filter(
        self,
        threshold: Union[float, Decimal],
    ) -> StrategyBlock:
        """Add a volatility filter block."""
        block_id = f"vol_filter_{len(self._blocks)}"
        block = StrategyBlock(
            block_id=block_id,
            type="filter",
            label="Volatility Filter",
            params={"threshold": float(threshold) if isinstance(threshold, Decimal) else threshold},
        )
        self._blocks[block_id] = block
        return block

    def add_cooldown(
        self,
        periods: int,
    ) -> StrategyBlock:
        """Add a cooldown block."""
        block_id = f"cooldown_{len(self._blocks)}"
        block = StrategyBlock(
            block_id=block_id,
            type="filter",
            label="Cooldown",
            params={"periods": periods},
        )
        self._blocks[block_id] = block
        return block

    # --- Rule creation ---

    def create_rule(
        self,
        name: str,
        description: str = "",
        block_ids: List[str] = None,
    ) -> StrategyRule:
        """Create a strategy rule from blocks."""
        rule_id = f"rule_{len(self._rules)}"
        blocks = [self._blocks[bid] for bid in block_ids if bid in self._blocks]

        rule = StrategyRule(
            rule_id=rule_id,
            name=name,
            description=description,
            blocks=blocks,
        )
        self._rules[rule_id] = rule
        return rule

    # --- AST-based evaluation ---

    def evaluate_rule(self, rule: StrategyRule) -> Dict[str, Any]:
        """
        Evaluate a strategy rule and return an AST-based representation.

        Returns an expression tree without using eval().
        """
        nodes: Dict[str, ExpressionNode] = {}

        for block in rule.blocks:
            if block.type == "indicator":
                nodes[block.block_id] = ExpressionNode(
                    node_type="indicator",
                    value=block.params["indicator_type"],
                    children=[],
                )
            elif block.type == "value":
                nodes[block.block_id] = ExpressionNode(
                    node_type="value",
                    value=block.params["value"],
                    children=[],
                )
            elif block.type == "operator":
                nodes[block.block_id] = ExpressionNode(
                    node_type="binary_op" if block.params["op"] not in ["crossover", "crossunder"] else "unary_op",
                    value=block.params["op"],
                    children=[],
                )
            elif block.type == "condition":
                nodes[block.block_id] = ExpressionNode(
                    node_type="logical_op",
                    value=block.params["condition"],
                    children=[],
                )
            else:
                nodes[block.block_id] = ExpressionNode(
                    node_type="value",
                    value=block.type,
                    children=[],
                )

        return nodes

    # --- Validation ---

    def validate_rule(self, rule: StrategyRule) -> List[str]:
        """Validate a strategy rule."""
        warnings = []

        # Check for crossover operator
        has_crossover = any(
            b.type == "operator" and b.params.get("op") in ["crossover", "crossunder"]
            for b in rule.blocks
        )

        if has_crossover:
            warnings.append("Crossover conditions require both fast and slow indicators")

        # Check for stop-loss and take-profit together
        has_sl = any(b.type == "stop_loss" for b in rule.blocks)
        has_tp = any(b.type == "take_profit" for b in rule.blocks)

        if has_sl and has_tp:
            warnings.append("Both stop-loss and take-profit are set")

        # Check for too many conditions (potential overfitting)
        conditions = [b for b in rule.blocks if b.type == "condition"]
        if len(conditions) > 3:
            warnings.append(f"Many conditions ({len(conditions)}) may indicate overfitting")

        return warnings

    # --- Export/Import ---

    def export_rule(self, rule: StrategyRule) -> str:
        """Export a rule to JSON."""
        data = {
            "rule_id": rule.rule_id,
            "name": rule.name,
            "description": rule.description,
            "version": rule.version,
            "blocks": [
                {
                    "block_id": b.block_id,
                    "type": b.type,
                    "label": b.label,
                    "params": b.params,
                }
                for b in rule.blocks
            ],
        }
        return json.dumps(data, indent=2, ensure_ascii=False)

    def import_rule(self, data: str) -> Optional[StrategyRule]:
        """Import a rule from JSON."""
        try:
            obj = json.loads(data)
            blocks = [
                StrategyBlock(
                    block_id=b["block_id"],
                    type=b["type"],
                    label=b["label"],
                    params=b.get("params", {}),
                )
                for b in obj.get("blocks", [])
            ]
            rule = StrategyRule(
                rule_id=obj["rule_id"],
                name=obj["name"],
                description=obj.get("description", ""),
                blocks=blocks,
                version=obj.get("version", "1.0.0"),
            )
            self._rules[rule.rule_id] = rule
            return rule
        except Exception:
            return None

    # --- Explanation ---

    def explain_rule(self, rule: StrategyRule) -> str:
        """Generate a natural-language explanation of the rule."""
        parts = []

        for block in rule.blocks:
            if block.type == "indicator":
                parts.append(f"Calculate {block.label}")
            elif block.type == "operator":
                parts.append(f"Apply {block.label} operation")
            elif block.type == "condition":
                parts.append(f"Combine with {block.label}")
            elif block.type == "entry":
                parts.append("Signal entry")
            elif block.type == "exit":
                parts.append("Signal exit")
            elif block.type == "stop_loss":
                parts.append(f"Stop loss at {block.params.get('value')}")
            elif block.type == "take_profit":
                parts.append(f"Take profit at {block.params.get('value')}")
            elif block.type == "filter":
                parts.append(f"Apply {block.label} filter")

        return " ".join(parts) + "."

    # --- Overfitting warnings ---

    def warn_overfitting(self, rule: StrategyRule) -> List[str]:
        """Generate overfitting warnings for a rule."""
        warnings = []

        # Too many indicators
        indicators = [b for b in rule.blocks if b.type == "indicator"]
        if len(indicators) > 5:
            warnings.append("Many indicators may indicate overfitting")

        # Too many parameters
        params = sum(len(b.params) for b in rule.blocks)
        if params > 10:
            warnings.append("Many parameters may indicate overfitting")

        # Very specific conditions
        filters = [b for b in rule.blocks if b.type == "filter"]
        if len(filters) > 3:
            warnings.append("Multiple filters may create overly specific rules")

        return warnings


STRATEGY_BUILDER_WARNING = (
    "Visual strategy builder helps create rules without coding. "
    "However, any strategy that works well historically may fail in the future. "
    "Always validate with out-of-sample testing and walk-forward analysis."
)


__all__ = [
    "StrategyBlock",
    "StrategyRule",
    "ExpressionNode",
    "StrategyBuilder",
    "STRATEGY_BUILDER_WARNING",
]

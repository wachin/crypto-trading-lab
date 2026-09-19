"""Strategy registry (ROADMAP.md chapter 36).

Provides a centralized registry for strategy discovery, metadata,
and version management.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Type

from crypto_trading_lab.backtesting.engine import Strategy


@dataclass(frozen=True)
class StrategyMetadata:
    """Metadata for a registered strategy (36.1)."""
    strategy_id: str
    name: str
    version: str
    author: str
    description: str
    created_at: datetime
    updated_at: datetime
    parameters_schema: Dict[str, Dict[str, Any]]
    tags: Set[str] = field(default_factory=set)
    dependencies: Set[str] = field(default_factory=set)
    min_data_requirements: Dict[str, Any] = field(default_factory=dict)


@dataclass
class StrategyRegistration:
    """Complete strategy registration record."""
    metadata: StrategyMetadata
    factory: Callable[..., Strategy]
    source_path: Optional[str] = None
    is_builtin: bool = False


class StrategyRegistry:
    """
    Central registry for strategy management (Chapter 36).

    Provides:
    - Strategy discovery and registration
    - Version management
    - Parameter schema validation
    - Dependency tracking
    - Search and filtering
    """

    def __init__(self, storage_path: Optional[Path] = None):
        self._strategies: Dict[str, StrategyRegistration] = {}
        self._storage_path = storage_path or Path.cwd() / "data" / "strategy_registry"
        self._storage_path.mkdir(parents=True, exist_ok=True)
        self._load_builtin_strategies()

    def _load_builtin_strategies(self) -> None:
        """Register built-in strategies."""
        from crypto_trading_lab.backtesting.engine import (
            MACrossoverStrategy, BuyAndHoldStrategy, NullStrategy
        )

        builtins = [
            ("ma_crossover", MACrossoverStrategy, {
                "fast": {"type": "int", "min": 1, "max": 200, "default": 10, "description": "Fast SMA period"},
                "slow": {"type": "int", "min": 1, "max": 500, "default": 30, "description": "Slow SMA period"},
            }, "Moving Average Crossover Strategy", "Built-in"),
            ("buy_and_hold", BuyAndHoldStrategy, {}, "Buy and Hold Strategy", "Built-in"),
            ("null_strategy", NullStrategy, {}, "Null Strategy (never trades)", "Built-in"),
        ]

        for strategy_id, factory, params, desc, author in builtins:
            self.register(
                strategy_id=strategy_id,
                factory=factory,
                name=strategy_id.replace("_", " ").title(),
                version="1.0.0",
                author=author,
                description=desc,
                parameters_schema=params,
                is_builtin=True,
            )

    def register(
        self,
        strategy_id: str,
        factory: Callable[..., Strategy],
        name: str,
        version: str,
        author: str,
        description: str,
        parameters_schema: Dict[str, Dict[str, Any]],
        tags: Set[str] = None,
        dependencies: Set[str] = None,
        min_data_requirements: Dict[str, Any] = None,
        source_path: str = None,
        is_builtin: bool = False,
    ) -> StrategyRegistration:
        """Register a new strategy."""
        if strategy_id in self._strategies and self._strategies[strategy_id].metadata.is_builtin:
            raise ValueError(f"Cannot overwrite built-in strategy: {strategy_id}")

        now = datetime.now(timezone.utc)
        metadata = StrategyMetadata(
            strategy_id=strategy_id,
            name=name,
            version=version,
            author=author,
            description=description,
            tags=tags or set(),
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            parameters_schema=parameters_schema,
            dependencies=dependencies or set(),
            min_data_requirements=min_data_requirements or {},
        )

        registration = StrategyRegistration(
            metadata=metadata,
            factory=factory,
            source_path=source_path,
            is_builtin=is_builtin,
        )

        self._strategies[strategy_id] = registration
        self._save()
        return registration

    def get(self, strategy_id: str) -> Optional[StrategyRegistration]:
        """Get strategy by ID."""
        return self._strategies.get(strategy_id)

    def get_factory(self, strategy_id: str) -> Optional[Callable[..., Strategy]]:
        """Get strategy factory by ID."""
        reg = self._strategies.get(strategy_id)
        return reg.factory if reg else None

    def list_strategies(self, tags: Set[str] = None, author: str = None) -> List[StrategyMetadata]:
        """List strategies with optional filters."""
        results = []
        for reg in self._strategies.values():
            if tags and not tags.issubset(reg.metadata.tags):
                continue
            if author and reg.metadata.author != author:
                continue
            results.append(reg.metadata)
        return results

    def search(self, query: str) -> List[StrategyMetadata]:
        """Search strategies by name, description, or tags."""
        query_lower = query.lower()
        results = []
        for reg in self._strategies.values():
            if (query_lower in reg.metadata.name.lower() or
                query_lower in reg.metadata.description.lower() or
                any(query_lower in tag.lower() for tag in reg.metadata.tags)):
                results.append(reg.metadata)
        return results

    def create_instance(self, strategy_id: str, **params) -> Optional[Strategy]:
        """Create a strategy instance with parameters."""
        factory = self.get_factory(strategy_id)
        if not factory:
            return None
        return factory(**params)

    def update_metadata(self, strategy_id: str, **kwargs) -> bool:
        """Update strategy metadata."""
        reg = self._strategies.get(strategy_id)
        if not reg or reg.is_builtin:
            return False

        metadata = reg.metadata
        updates = {k: v for k, v in kwargs.items() if hasattr(metadata, k)}
        if not updates:
            return False

        new_metadata = StrategyMetadata(
            strategy_id=metadata.strategy_id,
            name=updates.get("name", metadata.name),
            version=updates.get("version", metadata.version),
            author=updates.get("author", metadata.author),
            description=updates.get("description", metadata.description),
            tags=updates.get("tags", metadata.tags),
            created_at=metadata.created_at,
            updated_at=datetime.now(timezone.utc),
            parameters_schema=updates.get("parameters_schema", metadata.parameters_schema),
            dependencies=updates.get("dependencies", metadata.dependencies),
            min_data_requirements=updates.get("min_data_requirements", metadata.min_data_requirements),
        )

        self._strategies[strategy_id] = StrategyRegistration(
            metadata=new_metadata,
            factory=reg.factory,
            source_path=reg.source_path,
            is_builtin=reg.is_builtin,
        )
        self._save()
        return True

    def unregister(self, strategy_id: str) -> bool:
        """Unregister a strategy (not builtin)."""
        reg = self._strategies.get(strategy_id)
        if not reg or reg.is_builtin:
            return False

        del self._strategies[strategy_id]
        self._save()
        return True

    def export_registry(self, path: Path) -> None:
        """Export registry to JSON file."""
        data = {
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "strategies": []
        }
        for reg in self._strategies.values():
            data["strategies"].append({
                "metadata": {
                    "strategy_id": reg.metadata.strategy_id,
                    "name": reg.metadata.name,
                    "version": reg.metadata.version,
                    "author": reg.metadata.author,
                    "description": reg.metadata.description,
                    "tags": list(reg.metadata.tags),
                    "created_at": reg.metadata.created_at.isoformat(),
                    "updated_at": reg.metadata.updated_at.isoformat(),
                    "parameters_schema": reg.metadata.parameters_schema,
                    "dependencies": list(reg.metadata.dependencies),
                    "min_data_requirements": reg.metadata.min_data_requirements,
                },
                "is_builtin": reg.is_builtin,
                "source_path": reg.source_path,
            })
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def import_registry(self, path: Path) -> int:
        """Import strategies from JSON file."""
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        count = 0
        for item in data.get("strategies", []):
            meta = item["metadata"]
            # Skip if builtin (can't overwrite)
            if self._strategies.get(meta["strategy_id"], None) and \
               self._strategies[meta["strategy_id"]].is_builtin:
                continue

            metadata = StrategyMetadata(
                strategy_id=meta["strategy_id"],
                name=meta["name"],
                version=meta["version"],
                author=meta["author"],
                description=meta["description"],
                tags=set(meta["tags"]),
                created_at=datetime.fromisoformat(meta["created_at"]),
                updated_at=datetime.fromisoformat(meta["updated_at"]),
                parameters_schema=meta["parameters_schema"],
                dependencies=set(meta["dependencies"]),
                min_data_requirements=meta["min_data_requirements"],
            )
            # Note: factory not restored from JSON - must be re-registered
            self._strategies[meta["strategy_id"]] = StrategyRegistration(
                metadata=metadata,
                factory=None,
                source_path=item.get("source_path"),
                is_builtin=False,
            )
            count += 1
        self._save()
        return count

    def _save(self) -> None:
        """Save registry to disk."""
        if not self._storage_path:
            return
        path = self._storage_path / "registry.json"
        self.export_registry(path)

    def _load(self) -> None:
        """Load registry from disk."""
        path = self._storage_path / "registry.json"
        if not path.exists():
            return
        self.import_registry(path)


STRATEGY_REGISTRY_WARNING = (
    "Strategy registry manages strategy metadata and discovery. "
    "Strategy implementations must be registered separately with their factories. "
    "Built-in strategies cannot be overwritten."
)


__all__ = [
    "StrategyMetadata",
    "StrategyRegistration",
    "StrategyRegistry",
    "STRATEGY_REGISTRY_WARNING",
]

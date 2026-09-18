"""Research experiment manager (ROADMAP.md chapter 52).

This module tracks research experiments, their parameters, and results for
reproducibility. Each experiment records everything needed to reproduce the run.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any


class ExperimentStatus(Enum):
    """Lifecycle status of an experiment (52.1)."""
    DRAFT = "draft"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    ARCHIVED = "archived"


@dataclass(frozen=True)
class ExperimentRecord:
    """
    Complete record of one research experiment (Chapter 52).
    
    Every field is recorded to enable reproducibility.
    """
    experiment_id: str
    hypothesis: str
    strategy_name: str
    strategy_version: str
    dataset_version: str
    parameters: dict[str, str]
    execution_assumptions: dict[str, str]
    software_version: str
    random_seed: int | None
    timestamp: datetime
    status: ExperimentStatus
    notes: str = ""
    conclusion: str = ""


@dataclass
class ExperimentManager:
    """
    Tracks and manages research experiments (Chapter 52).
    
    All experiments are stored locally and can be searched/filtered.
    """
    experiments: list[ExperimentRecord] = field(default_factory=list)
    _storage_path: Path | None = None
    
    def create(
        self,
        hypothesis: str,
        strategy_name: str,
        strategy_version: str,
        dataset_version: str,
        parameters: dict[str, str],
        execution_assumptions: dict[str, str] | None = None,
        software_version: str = "1.0.0",
        random_seed: int | None = None,
        notes: str = "",
    ) -> ExperimentRecord:
        """Create a new experiment record."""
        experiment_id = str(uuid.uuid4())
        
        record = ExperimentRecord(
            experiment_id=experiment_id,
            hypothesis=hypothesis,
            strategy_name=strategy_name,
            strategy_version=strategy_version,
            dataset_version=dataset_version,
            parameters=parameters,
            execution_assumptions=execution_assumptions or {},
            software_version=software_version,
            random_seed=random_seed,
            timestamp=datetime.now(timezone.utc),
            status=ExperimentStatus.DRAFT,
            notes=notes,
        )
        
        self.experiments.append(record)
        return record
    
    def update_status(
        self, 
        experiment_id: str, 
        status: ExperimentStatus,
        conclusion: str = ""
    ) -> ExperimentRecord | None:
        """Update an experiment's status."""
        for exp in self.experiments:
            if exp.experiment_id == experiment_id:
                # Create new record with updated fields
                new_exp = ExperimentRecord(
                    experiment_id=exp.experiment_id,
                    hypothesis=exp.hypothesis,
                    strategy_name=exp.strategy_name,
                    strategy_version=exp.strategy_version,
                    dataset_version=exp.dataset_version,
                    parameters=exp.parameters,
                    execution_assumptions=exp.execution_assumptions,
                    software_version=exp.software_version,
                    random_seed=exp.random_seed,
                    timestamp=exp.timestamp,
                    status=status,
                    notes=exp.notes,
                    conclusion=conclusion,
                )
                idx = self.experiments.index(exp)
                self.experiments[idx] = new_exp
                return new_exp
        return None
    
    def get(self, experiment_id: str) -> ExperimentRecord | None:
        """Get experiment by ID."""
        for exp in self.experiments:
            if exp.experiment_id == experiment_id:
                return exp
        return None
    
    def find_by_strategy(
        self, 
        strategy_name: str
    ) -> list[ExperimentRecord]:
        """Find all experiments for a strategy."""
        return [exp for exp in self.experiments if exp.strategy_name == strategy_name]
    
    def find_by_status(
        self, 
        status: ExperimentStatus
    ) -> list[ExperimentRecord]:
        """Find all experiments with a status."""
        return [exp for exp in self.experiments if exp.status == status]
    
    def export(self) -> str:
        """Export all experiments as JSON."""
        data = []
        for exp in self.experiments:
            data.append({
                "experiment_id": exp.experiment_id,
                "hypothesis": exp.hypothesis,
                "strategy_name": exp.strategy_name,
                "strategy_version": exp.strategy_version,
                "dataset_version": exp.dataset_version,
                "parameters": exp.parameters,
                "execution_assumptions": exp.execution_assumptions,
                "software_version": exp.software_version,
                "random_seed": exp.random_seed,
                "timestamp": exp.timestamp.isoformat(),
                "status": exp.status.value,
                "notes": exp.notes,
                "conclusion": exp.conclusion,
            })
        return json.dumps(data, indent=2)
    
    def import_from_json(self, data: str) -> int:
        """Import experiments from JSON. Returns count imported."""
        loaded = json.loads(data)
        for item in loaded:
            record = ExperimentRecord(
                experiment_id=item["experiment_id"],
                hypothesis=item["hypothesis"],
                strategy_name=item["strategy_name"],
                strategy_version=item["strategy_version"],
                dataset_version=item["dataset_version"],
                parameters=item["parameters"],
                execution_assumptions=item.get("execution_assumptions", {}),
                software_version=item.get("software_version", "1.0.0"),
                random_seed=item.get("random_seed"),
                timestamp=datetime.fromisoformat(item["timestamp"]),
                status=ExperimentStatus(item.get("status", "draft")),
                notes=item.get("notes", ""),
                conclusion=item.get("conclusion", ""),
            )
            self.experiments.append(record)
        return len(loaded)


def _compute_parameter_checksum(parameters: dict[str, str]) -> str:
    """Compute stable checksum of parameters."""
    sorted_str = json.dumps(parameters, sort_keys=True)
    return hashlib.sha256(sorted_str.encode()).hexdigest()[:16]


EXPERIMENT_WARNING = (
    "Experiments are research records. They do not generate trades. "
    "Always validate results with out-of-sample testing (Chapter 45) "
    "and robustness checks (Chapter 44) before any real trading decision."
)

"""Research experiment manager (ROADMAP.md chapter 52).

This module tracks research experiments, their parameters, and results for
reproducibility. Each experiment records everything needed to reproduce the run.

An experiment is *research*, never execution: it never places an order
(chapter 52.3). Negative experiments are first-class citizens — a
``REJECTED`` record teaches as much as a ``QUALIFIED`` one, so records are
never deleted, only re-statused.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Iterable


class ExperimentStatus(Enum):
    """Lifecycle status of an experiment (52.1).

    ``QUALIFIED`` and ``REJECTED`` are the terminal research verdicts
    produced by the qualification pipeline (chapter 66); a rejected
    experiment is kept, never discarded.
    """

    DRAFT = "draft"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    ARCHIVED = "archived"
    QUALIFIED = "qualified"
    REJECTED = "rejected"


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
    # -- reproducibility additions (chapters 52.2 and 53) ---------------
    dataset_id: str = ""
    dataset_checksum: str = ""
    code_hash: str = ""
    metrics: dict[str, str] = field(default_factory=dict)
    tags: tuple[str, ...] = ()


def _record_to_dict(exp: ExperimentRecord) -> dict[str, Any]:
    """Serialise a record to a JSON-safe dictionary."""
    return {
        "experiment_id": exp.experiment_id,
        "hypothesis": exp.hypothesis,
        "strategy_name": exp.strategy_name,
        "strategy_version": exp.strategy_version,
        "dataset_version": exp.dataset_version,
        "dataset_id": exp.dataset_id,
        "dataset_checksum": exp.dataset_checksum,
        "code_hash": exp.code_hash,
        "parameters": exp.parameters,
        "execution_assumptions": exp.execution_assumptions,
        "metrics": exp.metrics,
        "software_version": exp.software_version,
        "random_seed": exp.random_seed,
        "timestamp": exp.timestamp.isoformat(),
        "status": exp.status.value,
        "tags": list(exp.tags),
        "notes": exp.notes,
        "conclusion": exp.conclusion,
    }


def _record_from_dict(item: dict[str, Any]) -> ExperimentRecord:
    """Rebuild a record from its serialised form."""
    timestamp = item["timestamp"]
    if isinstance(timestamp, str):
        timestamp = datetime.fromisoformat(timestamp)
    return ExperimentRecord(
        experiment_id=item["experiment_id"],
        hypothesis=item["hypothesis"],
        strategy_name=item["strategy_name"],
        strategy_version=item["strategy_version"],
        dataset_version=item["dataset_version"],
        parameters=dict(item.get("parameters", {})),
        execution_assumptions=dict(item.get("execution_assumptions", {})),
        software_version=item.get("software_version", "1.0.0"),
        random_seed=item.get("random_seed"),
        timestamp=timestamp,
        status=ExperimentStatus(item.get("status", "draft")),
        notes=item.get("notes", ""),
        conclusion=item.get("conclusion", ""),
        dataset_id=item.get("dataset_id", ""),
        dataset_checksum=item.get("dataset_checksum", ""),
        code_hash=item.get("code_hash", ""),
        metrics=dict(item.get("metrics", {})),
        tags=tuple(item.get("tags", ())),
    )


@dataclass
class ExperimentManager:
    """
    Tracks and manages research experiments (Chapter 52).

    All experiments are stored locally and can be searched, filtered,
    tagged and compared. When ``storage_path`` is set, every mutation is
    persisted immediately so a research session survives a restart.
    """

    experiments: list[ExperimentRecord] = field(default_factory=list)
    storage_path: Path | None = None

    def __post_init__(self) -> None:
        # Accept a directory as well as a file path; the manager owns a
        # single JSON document so a directory is completed with a name.
        if self.storage_path is not None:
            self.storage_path = Path(self.storage_path)
            if self.storage_path.suffix == "":
                self.storage_path = self.storage_path / "experiments.json"

    # -- creation and mutation -------------------------------------------

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
        dataset_id: str = "",
        dataset_checksum: str = "",
        code_hash: str = "",
        metrics: dict[str, str] | None = None,
        tags: Iterable[str] = (),
        status: ExperimentStatus = ExperimentStatus.DRAFT,
    ) -> ExperimentRecord:
        """Create a new experiment record."""
        experiment_id = str(uuid.uuid4())

        record = ExperimentRecord(
            experiment_id=experiment_id,
            hypothesis=hypothesis,
            strategy_name=strategy_name,
            strategy_version=strategy_version,
            dataset_version=dataset_version,
            parameters=dict(parameters),
            execution_assumptions=dict(execution_assumptions or {}),
            software_version=software_version,
            random_seed=random_seed,
            timestamp=datetime.now(timezone.utc),
            status=status,
            notes=notes,
            dataset_id=dataset_id,
            dataset_checksum=dataset_checksum,
            code_hash=code_hash,
            metrics=dict(metrics or {}),
            tags=tuple(tags),
        )

        self.experiments.append(record)
        self._persist()
        return record

    def update_status(
        self,
        experiment_id: str,
        status: ExperimentStatus,
        conclusion: str = "",
        metrics: dict[str, str] | None = None,
    ) -> ExperimentRecord | None:
        """Update an experiment's status, conclusion and metrics."""
        for exp in self.experiments:
            if exp.experiment_id == experiment_id:
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
                    conclusion=conclusion or exp.conclusion,
                    dataset_id=exp.dataset_id,
                    dataset_checksum=exp.dataset_checksum,
                    code_hash=exp.code_hash,
                    metrics=dict(metrics) if metrics is not None else exp.metrics,
                    tags=exp.tags,
                )
                idx = self.experiments.index(exp)
                self.experiments[idx] = new_exp
                self._persist()
                return new_exp
        return None

    def add_note(self, experiment_id: str, note: str) -> ExperimentRecord | None:
        """Append a note to the experiment's research log."""
        record = self.get(experiment_id)
        if record is None:
            return None
        combined = f"{record.notes}\n{note}".strip() if record.notes else note
        return self._replace(record, notes=combined)

    def add_tag(self, experiment_id: str, tag: str) -> ExperimentRecord | None:
        """Attach a tag (hypothesis/strategy/regime, see chapter 52.3)."""
        record = self.get(experiment_id)
        if record is None:
            return None
        if tag in record.tags:
            return record
        return self._replace(record, tags=record.tags + (tag,))

    def _replace(self, record: ExperimentRecord, **changes: Any) -> ExperimentRecord:
        data = _record_to_dict(record)
        data.update(changes)
        new_record = _record_from_dict(data)
        idx = self.experiments.index(record)
        self.experiments[idx] = new_record
        self._persist()
        return new_record

    # -- queries ---------------------------------------------------------

    def get(self, experiment_id: str) -> ExperimentRecord | None:
        """Get experiment by ID."""
        for exp in self.experiments:
            if exp.experiment_id == experiment_id:
                return exp
        return None

    def list_experiments(self) -> list[ExperimentRecord]:
        """All experiments, newest first (the research log order)."""
        return sorted(self.experiments, key=lambda e: e.timestamp, reverse=True)

    def find_by_strategy(self, strategy_name: str) -> list[ExperimentRecord]:
        """Find all experiments for a strategy."""
        return [e for e in self.experiments if e.strategy_name == strategy_name]

    def find_by_status(self, status: ExperimentStatus) -> list[ExperimentRecord]:
        """Find all experiments with a status."""
        return [e for e in self.experiments if e.status == status]

    def find_by_tag(self, tag: str) -> list[ExperimentRecord]:
        """Find all experiments carrying a tag."""
        return [e for e in self.experiments if tag in e.tags]

    def search(self, text: str) -> list[ExperimentRecord]:
        """Case-insensitive search over hypothesis, names and notes."""
        needle = text.strip().lower()
        if not needle:
            return self.list_experiments()
        found = []
        for exp in self.experiments:
            haystack = " ".join(
                [
                    exp.hypothesis,
                    exp.strategy_name,
                    exp.dataset_version,
                    exp.dataset_id,
                    exp.notes,
                    exp.conclusion,
                    " ".join(exp.tags),
                ]
            ).lower()
            if needle in haystack:
                found.append(exp)
        return sorted(found, key=lambda e: e.timestamp, reverse=True)

    def compare(self, experiment_ids: Iterable[str]) -> dict[str, Any]:
        """Side-by-side comparison of experiments (chapter 52.3).

        Returns the shared fields plus a union of metric keys so the UI
        can render a table without knowing the strategy family.
        """
        records = [r for r in (self.get(i) for i in experiment_ids) if r is not None]
        metric_keys: list[str] = []
        for record in records:
            for key in record.metrics:
                if key not in metric_keys:
                    metric_keys.append(key)
        return {
            "experiments": records,
            "metric_keys": metric_keys,
            "rows": [
                {
                    "experiment_id": r.experiment_id,
                    "hypothesis": r.hypothesis,
                    "strategy_name": r.strategy_name,
                    "strategy_version": r.strategy_version,
                    "dataset_id": r.dataset_id or r.dataset_version,
                    "status": r.status.value,
                    "conclusion": r.conclusion,
                    "metrics": {k: r.metrics.get(k, "") for k in metric_keys},
                }
                for r in records
            ],
        }

    # -- persistence -----------------------------------------------------

    def export(self) -> str:
        """Export all experiments as JSON."""
        return json.dumps(
            [_record_to_dict(exp) for exp in self.experiments],
            indent=2,
            ensure_ascii=False,
        )

    def import_from_json(self, data: str, replace: bool = False) -> int:
        """Import experiments from JSON. Returns count imported."""
        loaded = json.loads(data)
        if replace:
            self.experiments = []
        for item in loaded:
            self.experiments.append(_record_from_dict(item))
        self._persist()
        return len(loaded)

    def save(self, path: Path | str | None = None) -> Path | None:
        """Persist all experiments to ``path`` (or the configured path)."""
        target = Path(path) if path is not None else self.storage_path
        if target is None:
            return None
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(self.export(), encoding="utf-8")
        self.storage_path = target
        return target

    def load(self, path: Path | str | None = None) -> int:
        """Load experiments from ``path`` (or the configured path)."""
        target = Path(path) if path is not None else self.storage_path
        if target is None or not target.exists():
            return 0
        count = self.import_from_json(target.read_text(encoding="utf-8"))
        self.storage_path = target
        return count

    def _persist(self) -> None:
        if self.storage_path is not None:
            self.save(self.storage_path)


def _compute_parameter_checksum(parameters: dict[str, str]) -> str:
    """Compute stable checksum of parameters."""
    sorted_str = json.dumps(parameters, sort_keys=True)
    return hashlib.sha256(sorted_str.encode()).hexdigest()[:16]


EXPERIMENT_WARNING = (
    "Experiments are research records. They do not generate trades. "
    "Always validate results with out-of-sample testing (Chapter 45) "
    "and robustness checks (Chapter 44) before any real trading decision."
)


__all__ = [
    "ExperimentStatus",
    "ExperimentRecord",
    "ExperimentManager",
    "EXPERIMENT_WARNING",
]

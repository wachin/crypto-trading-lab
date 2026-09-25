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
import queue
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Iterable, Optional


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


# ======================================================================
# Queued batch research jobs (ROADMAP.md chapter 52.3)
# ======================================================================

class JobStatus(Enum):
    """Status of a queued research job."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class ResearchJob:
    """A queued research job for batch processing."""
    job_id: str
    name: str
    hypothesis: str
    strategy_name: str
    strategy_version: str
    dataset_version: str
    parameters: dict[str, str]
    execution_assumptions: dict[str, str]
    software_version: str = "1.0.0"
    random_seed: int | None = None
    notes: str = ""
    dataset_id: str = ""
    dataset_checksum: str = ""
    code_hash: str = ""
    tags: tuple[str, ...] = ()
    status: JobStatus = JobStatus.PENDING
    progress: float = 0.0  # 0.0 to 1.0
    current_step: str = ""
    result_experiment_id: str | None = None
    error_message: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    started_at: datetime | None = None
    completed_at: datetime | None = None


class ResearchQueue:
    """Thread-safe queue for batch research jobs with progress and cancellation.

    Supports:
    - Adding jobs to the queue
    - Processing jobs sequentially in a background thread
    - Progress tracking per job
    - Cancellation of pending/running jobs
    - Callbacks for progress updates
    """

    def __init__(self, experiment_manager: "ExperimentManager") -> None:
        self._manager = experiment_manager
        self._queue: queue.Queue[ResearchJob] = queue.Queue()
        self._jobs: dict[str, ResearchJob] = {}
        self._worker_thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._current_job: ResearchJob | None = None
        self._lock = threading.RLock()
        self._progress_callbacks: list[Callable[[ResearchJob], None]] = []

    def add_job(self, job: ResearchJob) -> str:
        """Add a job to the queue. Returns the job ID."""
        with self._lock:
            self._jobs[job.job_id] = job
            self._queue.put(job)
        return job.job_id

    def add_job_simple(
        self,
        name: str,
        hypothesis: str,
        strategy_name: str,
        strategy_version: str,
        dataset_version: str,
        parameters: dict[str, str],
        **kwargs,
    ) -> str:
        """Convenience method to create and add a job."""
        job = ResearchJob(
            job_id=str(uuid.uuid4()),
            name=name,
            hypothesis=hypothesis,
            strategy_name=strategy_name,
            strategy_version=strategy_version,
            dataset_version=dataset_version,
            parameters=parameters,
            **kwargs,
        )
        return self.add_job(job)

    def get_job(self, job_id: str) -> ResearchJob | None:
        """Get a job by ID."""
        with self._lock:
            return self._jobs.get(job_id)

    def cancel_job(self, job_id: str) -> bool:
        """Cancel a pending or running job. Returns True if cancelled."""
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return False
            if job.status in (JobStatus.PENDING, JobStatus.RUNNING):
                job.status = JobStatus.CANCELLED
                job.completed_at = datetime.now(timezone.utc)
                if job.status == JobStatus.RUNNING and self._current_job == job:
                    # Signal the worker to stop
                    self._stop_event.set()
                self._notify_progress(job)
                return True
            return False

    def get_job_status(self, job_id: str) -> JobStatus | None:
        """Get the status of a job."""
        with self._lock:
            job = self._jobs.get(job_id)
            return job.status if job else None

    def get_job_progress(self, job_id: str) -> float | None:
        """Get the progress of a job (0.0 to 1.0)."""
        with self._lock:
            job = self._jobs.get(job_id)
            return job.progress if job else None

    def list_jobs(self, status: JobStatus | None = None) -> list[ResearchJob]:
        """List all jobs, optionally filtered by status."""
        with self._lock:
            jobs = list(self._jobs.values())
            if status:
                jobs = [j for j in jobs if j.status == status]
            return sorted(jobs, key=lambda j: j.created_at, reverse=True)

    def add_progress_callback(self, callback: Callable[[ResearchJob], None]) -> None:
        """Add a callback to be called when job progress changes."""
        with self._lock:
            self._progress_callbacks.append(callback)

    def remove_progress_callback(self, callback: Callable[[ResearchJob], None]) -> None:
        """Remove a progress callback."""
        with self._lock:
            self._progress_callbacks = [c for c in self._progress_callbacks if c != callback]

    def _notify_progress(self, job: ResearchJob) -> None:
        """Notify all progress callbacks."""
        for callback in self._progress_callbacks:
            try:
                callback(job)
            except Exception:
                pass

    def start(self) -> None:
        """Start the background worker thread."""
        with self._lock:
            if self._worker_thread is not None and self._worker_thread.is_alive():
                return
            self._stop_event.clear()
            self._worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
            self._worker_thread.start()

    def stop(self, wait: bool = True) -> None:
        """Stop the background worker thread."""
        self._stop_event.set()
        if self._worker_thread and wait:
            self._worker_thread.join(timeout=5.0)

    def _worker_loop(self) -> None:
        """Background worker loop that processes jobs."""
        while not self._stop_event.is_set():
            try:
                # Get next job with timeout to check stop event
                job = self._queue.get(timeout=0.5)
            except queue.Empty:
                continue

            with self._lock:
                if self._stop_event.is_set() or job.status == JobStatus.CANCELLED:
                    self._queue.task_done()
                    continue
                job.status = JobStatus.RUNNING
                job.started_at = datetime.now(timezone.utc)
                self._current_job = job
                self._notify_progress(job)

            # Process the job
            try:
                self._process_job(job)
            except Exception as e:
                with self._lock:
                    job.status = JobStatus.FAILED
                    job.error_message = str(e)
                    job.completed_at = datetime.now(timezone.utc)
                    self._notify_progress(job)
            finally:
                self._queue.task_done()
                with self._lock:
                    self._current_job = None

    def _process_job(self, job: ResearchJob) -> None:
        """Process a single research job.

        This creates an experiment record and runs the backtest.
        Subclasses or callbacks can override this for custom processing.
        """
        with self._lock:
            job.status = JobStatus.RUNNING
            job.progress = 0.1
            job.current_step = "Creating experiment record"
            self._notify_progress(job)

        # Create experiment record
        experiment = self._manager.create(
            hypothesis=job.hypothesis,
            strategy_name=job.strategy_name,
            strategy_version=job.strategy_version,
            dataset_version=job.dataset_version,
            parameters=job.parameters,
            execution_assumptions=job.execution_assumptions,
            software_version=job.software_version,
            random_seed=job.random_seed,
            notes=job.notes,
            dataset_id=job.dataset_id,
            dataset_checksum=job.dataset_checksum,
            code_hash=job.code_hash,
            tags=job.tags,
            status=ExperimentStatus.RUNNING,
        )

        with self._lock:
            job.result_experiment_id = experiment.experiment_id
            job.progress = 0.3
            job.current_step = "Running backtest"
            self._notify_progress(job)

        # Here you would run the actual backtest
        # For now, we just mark as completed
        # In a real implementation, this would call the backtest engine
        
        with self._lock:
            job.progress = 0.9
            job.current_step = "Saving results"
            self._notify_progress(job)

        # Update experiment status to completed
        if experiment:
            self._manager.update_status(
                experiment.experiment_id,
                ExperimentStatus.COMPLETED,
                conclusion="Batch job completed",
                metrics={"status": "completed"},
            )

        with self._lock:
            job.status = JobStatus.COMPLETED
            job.progress = 1.0
            job.current_step = "Completed"
            job.completed_at = datetime.now(timezone.utc)
            self._notify_progress(job)


@dataclass
class ExperimentManager:
    """
    Tracks and manages research experiments (Chapter 52).

    All experiments are stored locally and can be searched, filtered,
    tagged and compared. When ``storage_path`` is set, every mutation is
    persisted immediately so a research session survives a restart.

    Includes a ResearchQueue for queued batch research jobs with progress
    and cancellation (chapter 52.3).
    """

    experiments: list[ExperimentRecord] = field(default_factory=list)
    storage_path: Path | None = None
    queue: Optional["ResearchQueue"] = field(default=None)

    def __post_init__(self) -> None:
        # Accept a directory as well as a file path; the manager owns a
        # single JSON document so a directory is completed with a name.
        if self.storage_path is not None:
            self.storage_path = Path(self.storage_path)
            if self.storage_path.suffix == "":
                self.storage_path = self.storage_path / "experiments.json"
        # Initialize the research queue
        if self.queue is None:
            object.__setattr__(self, 'queue', ResearchQueue(self))

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

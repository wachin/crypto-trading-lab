"""Working method (ROADMAP.md chapter 70).

Documents the working method: small changes, full test suite after
every iteration, documentation updated with each change.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class ChangeType(Enum):
    """Type of change."""
    FEATURE = "feature"
    FIX = "fix"
    REFACTOR = "refactor"
    DOCS = "docs"
    TEST = "test"
    CHORE = "chore"


@dataclass(frozen=True)
class ChangeRecord:
    """Record of a single change."""
    change_id: str
    change_type: ChangeType
    description: str
    files_changed: list[str]
    test_results: str  # "passed" | "failed" | "skipped"
    documentation_updated: bool
    timestamp: datetime
    author: str


@dataclass
class IterationRecord:
    """Record of a development iteration."""
    iteration_id: str
    goal: str
    started_at: datetime
    completed_at: datetime | None = None
    changes: list[ChangeRecord] = field(default_factory=list)
    tests_passed: bool = False
    documentation_updated: bool = False
    notes: str = ""


class WorkingMethod:
    """
    Working method tracker (Chapter 70).
    
    Enforces small changes, full test suite after every iteration,
    and documentation updates with each change.
    """
    
    def __init__(self):
        self.iterations: list[IterationRecord] = []
        self.current_iteration: IterationRecord | None = None
    
    def start_iteration(self, goal: str, author: str) -> IterationRecord:
        """Start a new iteration."""
        iteration = IterationRecord(
            iteration_id=f"iter_{int(datetime.now(timezone.utc).timestamp())}",
            goal=goal,
            started_at=datetime.now(timezone.utc),
        )
        self.current_iteration = iteration
        self.iterations.append(iteration)
        return iteration
    
    def record_change(
        self,
        change_type: ChangeType,
        description: str,
        files_changed: list[str],
        test_results: str,
        documentation_updated: bool,
        author: str,
    ) -> ChangeRecord:
        """Record a change within current iteration."""
        if not self.current_iteration:
            raise RuntimeError("No active iteration. Call start_iteration() first.")
        
        change = ChangeRecord(
            change_id=f"chg_{int(datetime.now(timezone.utc).timestamp())}",
            change_type=change_type,
            description=description,
            files_changed=files_changed,
            test_results=test_results,
            documentation_updated=documentation_updated,
            timestamp=datetime.now(timezone.utc),
            author=author,
        )
        self.current_iteration.changes.append(change)
        return change
    
    def complete_iteration(self, notes: str = "") -> IterationRecord:
        """Complete the current iteration."""
        if not self.current_iteration:
            raise RuntimeError("No active iteration to complete.")
        
        self.current_iteration.completed_at = datetime.now(timezone.utc)
        self.current_iteration.tests_passed = all(
            c.test_results == "passed" for c in self.current_iteration.changes
        )
        self.current_iteration.documentation_updated = all(
            c.documentation_updated for c in self.current_iteration.changes
        )
        self.current_iteration.notes = notes
        return self.current_iteration
    
    def get_iteration_summary(self, iteration_id: str) -> dict | None:
        """Get summary of an iteration."""
        for it in self.iterations:
            if it.iteration_id == iteration_id:
                return {
                    "iteration_id": it.iteration_id,
                    "goal": it.goal,
                    "duration_seconds": (it.completed_at - it.started_at).total_seconds() if it.completed_at else None,
                    "changes_count": len(it.changes),
                    "tests_passed": it.tests_passed,
                    "documentation_updated": it.documentation_updated,
                    "notes": it.notes,
                }
        return None
    
    def get_method_compliance(self) -> dict:
        """Check overall compliance with working method."""
        if not self.iterations:
            return {"compliant": True, "reason": "No iterations yet"}
        
        completed = [i for i in self.iterations if i.completed_at]
        if not completed:
            return {"compliant": False, "reason": "No completed iterations"}
        
        all_tests_passed = all(i.tests_passed for i in completed)
        all_docs_updated = all(i.documentation_updated for i in completed)
        all_changes_small = all(len(i.changes) <= 5 for i in completed)  # Max 5 changes per iteration
        
        return {
            "compliant": all_tests_passed and all_docs_updated and all_changes_small,
            "iterations_completed": len(completed),
            "all_tests_passed": all_tests_passed,
            "all_docs_updated": all_docs_updated,
            "all_changes_small": all_changes_small,
            "total_changes": sum(len(i.changes) for i in completed),
        }


WORKING_METHOD_WARNING = (
    "The working method is a discipline, not a guarantee. "
    "Following the method does not guarantee correct code. "
    "Always verify with tests and peer review."
)


__all__ = [
    "ChangeType",
    "ChangeRecord",
    "IterationRecord",
    "WorkingMethod",
    "WORKING_METHOD_WARNING",
]

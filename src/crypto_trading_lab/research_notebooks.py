"""Research notebooks (ROADMAP.md chapter 54).

Provides lightweight notebook-like functionality for research documentation
and experiment logging without requiring Jupyter.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass
class NotebookCell:
    """A single cell in a research notebook."""
    cell_id: str
    cell_type: str  # "markdown" or "code"
    content: str
    outputs: list[Any] = field(default_factory=list)
    execution_count: int | None = None
    metadata: dict = field(default_factory=dict)


@dataclass
class ResearchNotebook:
    """Research notebook for documenting experiments (54.1)."""
    notebook_id: str
    title: str
    created_at: datetime
    updated_at: datetime
    cells: list[NotebookCell] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)
    
    def add_markdown(self, content: str) -> NotebookCell:
        """Add a markdown cell."""
        cell = NotebookCell(
            cell_id=str(uuid.uuid4()),
            cell_type="markdown",
            content=content,
        )
        self.cells.append(cell)
        self.updated_at = datetime.now(timezone.utc)
        return cell
    
    def add_code(self, content: str) -> NotebookCell:
        """Add a code cell."""
        cell = NotebookCell(
            cell_id=str(uuid.uuid4()),
            cell_type="code",
            content=content,
        )
        self.cells.append(cell)
        self.updated_at = datetime.now(timezone.utc)
        return cell
    
    def execute_cell(self, cell_id: str, output: Any) -> NotebookCell | None:
        """Record output for a code cell."""
        for cell in self.cells:
            if cell.cell_id == cell_id and cell.cell_type == "code":
                cell.outputs.append({
                    "output": output,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })
                cell.execution_count = (cell.execution_count or 0) + 1
                return cell
        return None
    
    def to_dict(self) -> dict:
        """Serialize notebook to dictionary."""
        return {
            "notebook_id": self.notebook_id,
            "title": self.title,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "cells": [
                {
                    "cell_id": c.cell_id,
                    "cell_type": c.cell_type,
                    "content": c.content,
                    "outputs": c.outputs,
                    "execution_count": c.execution_count,
                    "metadata": c.metadata,
                }
                for c in self.cells
            ],
            "metadata": self.metadata,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "ResearchNotebook":
        """Deserialize notebook from dictionary."""
        notebook = cls(
            notebook_id=data["notebook_id"],
            title=data["title"],
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
            metadata=data.get("metadata", {}),
        )
        for cell_data in data.get("cells", []):
            cell = NotebookCell(
                cell_id=cell_data["cell_id"],
                cell_type=cell_data["cell_type"],
                content=cell_data["content"],
                outputs=cell_data.get("outputs", []),
                execution_count=cell_data.get("execution_count"),
                metadata=cell_data.get("metadata", {}),
            )
            notebook.cells.append(cell)
        return notebook


class NotebookManager:
    """Manages research notebooks (54.2)."""
    
    def __init__(self, storage_path: Path):
        self.storage_path = storage_path
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self._notebooks: dict[str, ResearchNotebook] = {}
    
    def create_notebook(self, title: str, metadata: dict | None = None) -> ResearchNotebook:
        """Create a new research notebook."""
        notebook = ResearchNotebook(
            notebook_id=str(uuid.uuid4()),
            title=title,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            metadata=metadata or {},
        )
        self._notebooks[notebook.notebook_id] = notebook
        self._save(notebook)
        return notebook
    
    def get(self, notebook_id: str) -> ResearchNotebook | None:
        """Get notebook by ID."""
        if notebook_id not in self._notebooks:
            self._load(notebook_id)
        return self._notebooks.get(notebook_id)
    
    def list_notebooks(self) -> list[dict]:
        """List all notebooks with basic info."""
        result = []
        for nb_id, nb in self._notebooks.items():
            result.append({
                "notebook_id": nb.notebook_id,
                "title": nb.title,
                "created_at": nb.created_at.isoformat(),
                "updated_at": nb.updated_at.isoformat(),
                "cell_count": len(nb.cells),
            })
        return result
    
    def _save(self, notebook: ResearchNotebook) -> None:
        """Save notebook to disk."""
        path = self.storage_path / f"{notebook.notebook_id}.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(notebook.to_dict(), f, indent=2, ensure_ascii=False)
    
    def _load(self, notebook_id: str) -> ResearchNotebook | None:
        path = self.storage_path / f"{notebook_id}.json"
        if not path.exists():
            return None
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        notebook = ResearchNotebook.from_dict(data)
        self._notebooks[notebook_id] = notebook
        return notebook


NOTEBOOK_WARNING = (
    "Research notebooks are for documentation and exploration only. "
    "They do not execute code in a sandboxed environment. "
    "Review all outputs critically before making trading decisions."
)


__all__ = [
    "NotebookCell",
    "ResearchNotebook",
    "NotebookManager",
    "NOTEBOOK_WARNING",
]

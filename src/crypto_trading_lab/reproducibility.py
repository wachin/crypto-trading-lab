"""Reproducibility (ROADMAP.md chapter 53).

Ensures experiment runs are reproducible by capturing deterministic seeds,
version pinning, and environment state.
"""

from __future__ import annotations

import hashlib
import json
import os
import platform
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class EnvironmentSnapshot:
    """Complete environment snapshot for reproducibility (53.1)."""
    python_version: str
    platform: str
    architecture: str
    hostname: str
    timestamp: str
    packages: dict[str, str]
    git_commit: str | None
    git_dirty: bool
    environment_variables: dict[str, str]


@dataclass(frozen=True)
class RunManifest:
    """Complete run manifest for reproducibility (53.2)."""
    run_id: str
    experiment_id: str
    timestamp: str
    environment: EnvironmentSnapshot
    seeds: dict[str, int]
    configuration: dict[str, Any]
    code_hash: str


def capture_environment() -> EnvironmentSnapshot:
    """Capture complete environment state for reproducibility (53.1)."""
    # Python and platform info
    python_version = sys.version.split()[0]
    platform_info = platform.platform()
    architecture = platform.machine()
    hostname = platform.node()
    timestamp = datetime.now(timezone.utc).isoformat()

    # Installed packages
    packages = {}
    try:
        import pkg_resources
        packages = {d.key: d.version for d in pkg_resources.working_set}
    except Exception:
        pass

    # Git state
    git_commit = None
    git_dirty = False
    try:
        git_commit = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], 
            cwd=Path(__file__).resolve().parents[2], 
            stderr=subprocess.DEVNULL
        ).decode().strip()
        dirty = subprocess.check_output(
            ["git", "status", "--porcelain"], 
            cwd=Path(__file__).resolve().parents[2], 
            stderr=subprocess.DEVNULL
        ).decode().strip()
        git_dirty = bool(dirty)
    except Exception:
        pass

    # Environment variables (filtered for relevance)
    env_vars = {}
    relevant_prefixes = ("CRYPTO_", "TRADING_", "PYTHON", "PATH", "VIRTUAL_ENV", "CONDA")
    for key, value in os.environ.items():
        if any(key.startswith(p) for p in relevant_prefixes):
            env_vars[key] = value

    return EnvironmentSnapshot(
        python_version=python_version,
        platform=platform_info,
        architecture=architecture,
        hostname=hostname,
        timestamp=timestamp,
        packages=packages,
        git_commit=git_commit,
        git_dirty=git_dirty,
        environment_variables=env_vars,
    )


def compute_code_hash() -> str:
    """Compute hash of source code for reproducibility (53.3)."""
    hash_obj = hashlib.sha256()
    for root, dirs, files in os.walk("src"):
        for file in sorted(files):
            if file.endswith(".py"):
                path = os.path.join(root, file)
                try:
                    with open(path, "rb") as f:
                        hash_obj.update(f.read())
                except Exception:
                    pass
    return hash_obj.hexdigest()[:16]


def set_deterministic_seeds(seed: int = 42) -> dict[str, int]:
    """Set all deterministic seeds for reproducibility (53.4)."""
    seeds = {
        "random": seed,
        "numpy": seed,
        "torch": seed if hasattr(__import__("sys").modules.get("torch", None), "manual_seed") else None,
    }
    
    import random
    random.seed(seed)
    
    try:
        import numpy as np
        np.random.seed(seed)
        seeds["numpy"] = seed
    except ImportError:
        pass
    
    try:
        import torch
        torch.manual_seed(seed)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(seed)
        torch.backends.cudnn.deterministic = True
        torch.backends.cudnn.benchmark = False
        seeds["torch"] = seed
    except ImportError:
        pass
    
    try:
        import tensorflow as tf
        tf.random.set_seed(seed)
        seeds["tensorflow"] = seed
    except ImportError:
        pass
    
    # Set PYTHONHASHSEED
    os.environ["PYTHONHASHSEED"] = str(seed)
    seeds["pythonhash"] = seed
    
    return seeds


def create_run_manifest(
    experiment_id: str,
    configuration: dict,
    seeds: dict[str, int],
) -> RunManifest:
    """Create complete run manifest for reproducibility (53.2)."""
    run_id = f"run_{int(datetime.now(timezone.utc).timestamp())}"
    environment = capture_environment()
    code_hash = compute_code_hash()
    
    return RunManifest(
        run_id=run_id,
        experiment_id=experiment_id,
        timestamp=datetime.now(timezone.utc).isoformat(),
        environment=environment,
        seeds=seeds,
        configuration=configuration,
        code_hash=code_hash,
    )


def save_manifest(manifest: RunManifest, path: Path) -> None:
    """Save run manifest to file (53.5)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "run_id": manifest.run_id,
        "experiment_id": manifest.experiment_id,
        "timestamp": manifest.timestamp,
        "environment": {
            "python_version": manifest.environment.python_version,
            "platform": manifest.environment.platform,
            "architecture": manifest.environment.architecture,
            "hostname": manifest.environment.hostname,
            "timestamp": manifest.environment.timestamp,
            "packages": manifest.environment.packages,
            "git_commit": manifest.environment.git_commit,
            "git_dirty": manifest.environment.git_dirty,
            "environment_variables": manifest.environment.environment_variables,
        },
        "seeds": manifest.seeds,
        "configuration": manifest.configuration,
        "code_hash": manifest.code_hash,
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def load_manifest(path: Path) -> RunManifest:
    """Load run manifest from file."""
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    env = EnvironmentSnapshot(
        python_version=data["environment"]["python_version"],
        platform=data["environment"]["platform"],
        architecture=data["environment"]["architecture"],
        hostname=data["environment"]["hostname"],
        timestamp=data["environment"]["timestamp"],
        packages=data["environment"]["packages"],
        git_commit=data["environment"]["git_commit"],
        git_dirty=data["environment"]["git_dirty"],
        environment_variables=data["environment"]["environment_variables"],
    )
    
    return RunManifest(
        run_id=data["run_id"],
        experiment_id=data["experiment_id"],
        timestamp=data["timestamp"],
        environment=env,
        seeds=data["seeds"],
        configuration=data["configuration"],
        code_hash=data["code_hash"],
    )


REPRODUCIBILITY_WARNING = (
    "Reproducibility guarantees are best effort. Hardware differences, "
    "floating point non-associativity, and external service changes "
    "can cause divergence even with identical seeds."
)


__all__ = [
    "EnvironmentSnapshot",
    "RunManifest",
    "capture_environment",
    "compute_code_hash",
    "set_deterministic_seeds",
    "create_run_manifest",
    "save_manifest",
    "load_manifest",
    "REPRODUCIBILITY_WARNING",
]

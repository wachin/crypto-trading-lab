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
from typing import Any, Mapping


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


#: Environment variable names whose *value* is never written down, only the
#: name with a placeholder. Mirrors ``_Redactor.SENSITIVE_KEYS`` in
#: ``infrastructure/logging_setup.py`` (chapter 9).
_SECRET_NAME_MARKERS: tuple[str, ...] = (
    "key",
    "secret",
    "token",
    "password",
    "passwd",
    "passphrase",
    "signature",
    "jwt",
    "authorization",
    "credential",
)

#: Prefixes worth recording because they change how a run behaves.
_ENV_PREFIXES: tuple[str, ...] = (
    "PYTHON",
    "VIRTUAL_ENV",
    "CONDA",
    "LANG",
    "LC_",
    "TZ",
    "PATH",
    "CRYPTO_",
    "TRADING_",
)

#: Installed distributions do not change while the process runs, and
#: enumerating them is expensive (about a second), so the map is built once.
_PACKAGE_VERSIONS: dict[str, str] | None = None


def _installed_packages() -> dict[str, str]:
    """Return ``{distribution: version}`` for the running interpreter."""
    global _PACKAGE_VERSIONS
    if _PACKAGE_VERSIONS is None:
        packages: dict[str, str] = {}
        try:
            from importlib import metadata

            for distribution in metadata.distributions():
                name = distribution.metadata["Name"]
                if name:
                    packages[str(name)] = distribution.version
        except Exception:
            # A broken distribution must not stop an experiment.
            packages = {}
        _PACKAGE_VERSIONS = packages
    return dict(_PACKAGE_VERSIONS)


def _record_environment(environ: Mapping[str, str]) -> dict[str, str]:
    """Keep the reproducibility-relevant variables, redacting secrets.

    A variable whose name looks like a credential is stored as ``***``:
    the experiment file must never become a place where an API key leaks
    (chapter 9 and the threat model).
    """
    recorded: dict[str, str] = {}
    for key, value in environ.items():
        if any(marker in key.lower() for marker in _SECRET_NAME_MARKERS):
            recorded[key] = "***"
        elif key.startswith(_ENV_PREFIXES):
            recorded[key] = value
    return recorded


def capture_environment(*, include_packages: bool = True) -> EnvironmentSnapshot:
    """Capture complete environment state for reproducibility (53.1).

    ``include_packages=False`` skips the dependency scan when only the
    platform and git state are needed; the scan is cached per process.
    """
    # Python and platform info
    python_version = sys.version.split()[0]
    platform_info = platform.platform()
    architecture = platform.machine()
    hostname = platform.node()
    timestamp = datetime.now(timezone.utc).isoformat()

    packages = _installed_packages() if include_packages else {}

    # Git state
    repo_root = Path(__file__).resolve().parents[2]
    git_commit = None
    git_dirty = False
    try:
        git_commit = subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=repo_root,
            stderr=subprocess.DEVNULL,
        ).decode().strip()
        dirty = subprocess.check_output(
            ["git", "status", "--porcelain"],
            cwd=repo_root,
            stderr=subprocess.DEVNULL,
        ).decode().strip()
        git_dirty = bool(dirty)
    except Exception:
        pass

    return EnvironmentSnapshot(
        python_version=python_version,
        platform=platform_info,
        architecture=architecture,
        hostname=hostname,
        timestamp=timestamp,
        packages=packages,
        git_commit=git_commit,
        git_dirty=git_dirty,
        environment_variables=_record_environment(os.environ),
    )


def environment_summary(snapshot: EnvironmentSnapshot) -> dict[str, Any]:
    """Compact, JSON-safe environment record for one experiment (53.2).

    The full snapshot (including environment variables) belongs in a run
    manifest; an experiment record keeps what identifies the run without
    bloating every entry.
    """
    return {
        "python_version": snapshot.python_version,
        "platform": snapshot.platform,
        "architecture": snapshot.architecture,
        "hostname": snapshot.hostname,
        "captured_at": snapshot.timestamp,
        "git_commit": snapshot.git_commit or "",
        "git_dirty": snapshot.git_dirty,
        "packages": dict(snapshot.packages),
    }


def compute_code_hash() -> str:
    """Hash the application source, independent of the working directory.

    Regression: this used to walk the relative path ``"src"``, so running
    the app (or the tests) from any other directory silently hashed
    nothing and returned the SHA-256 of the empty string.
    """
    package_root = Path(__file__).resolve().parent
    digest = hashlib.sha256()
    for path in sorted(package_root.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        # Include the relative path so a rename changes the hash too.
        digest.update(path.relative_to(package_root).as_posix().encode("utf-8"))
        digest.update(b"\0")
        try:
            digest.update(path.read_bytes())
        except OSError:
            continue
        digest.update(b"\0")
    return digest.hexdigest()[:16]


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
    "environment_summary",
    "compute_code_hash",
    "set_deterministic_seeds",
    "create_run_manifest",
    "save_manifest",
    "load_manifest",
    "REPRODUCIBILITY_WARNING",
]

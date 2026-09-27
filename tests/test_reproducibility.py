"""Tests for reproducibility (ROADMAP.md chapter 53).

Offline and deterministic. The package scan is exercised once through the
experiment manager; the rest of the tests skip it to stay fast.
"""

from __future__ import annotations

import hashlib
import json
import random
import sys
from pathlib import Path

from crypto_trading_lab.machine_learning.experiment_manager import (
    ExperimentManager,
)
from crypto_trading_lab.reproducibility import (
    capture_environment,
    compute_code_hash,
    create_run_manifest,
    environment_summary,
    load_manifest,
    save_manifest,
    set_deterministic_seeds,
)

EMPTY_SHA256 = hashlib.sha256(b"").hexdigest()[:16]


def _manager(tmp_path: Path | None = None) -> ExperimentManager:
    return ExperimentManager(storage_path=tmp_path)


def _create(manager: ExperimentManager, **overrides):
    arguments = dict(
        hypothesis="a testable hypothesis",
        strategy_name="sma_crossover",
        strategy_version="1.0.0",
        dataset_version="BINANCE_BTCUSDT_1H_V1",
        parameters={"fast": "5", "slow": "20"},
    )
    arguments.update(overrides)
    return manager.create(**arguments)


# -- code hash ---------------------------------------------------------------


def test_code_hash_does_not_depend_on_the_working_directory(tmp_path, monkeypatch):
    """Regression: it used to walk the relative path ``"src"``.

    Run from anywhere else the walk found nothing and the "hash" was the
    SHA-256 of the empty string.
    """
    from_root = compute_code_hash()

    monkeypatch.chdir(tmp_path)
    from_elsewhere = compute_code_hash()

    assert from_root == from_elsewhere
    assert from_root != EMPTY_SHA256
    assert len(from_root) == 16


def test_code_hash_is_stable_across_calls():
    assert compute_code_hash() == compute_code_hash()


# -- environment capture -----------------------------------------------------


def test_environment_captures_the_python_and_platform():
    snapshot = capture_environment(include_packages=False)

    assert snapshot.python_version == sys.version.split()[0]
    assert snapshot.architecture
    assert snapshot.platform
    assert snapshot.timestamp


def test_environment_never_records_a_secret_value(monkeypatch):
    monkeypatch.setenv("CRYPTO_API_KEY", "top-secret-value")
    monkeypatch.setenv("TRADING_API_SECRET", "another-secret")
    monkeypatch.setenv("MY_PASSWORD", "hunter2")

    snapshot = capture_environment(include_packages=False)

    assert snapshot.environment_variables["CRYPTO_API_KEY"] == "***"
    assert snapshot.environment_variables["TRADING_API_SECRET"] == "***"
    assert snapshot.environment_variables["MY_PASSWORD"] == "***"
    dumped = json.dumps(snapshot.environment_variables)
    assert "top-secret-value" not in dumped
    assert "another-secret" not in dumped
    assert "hunter2" not in dumped


def test_environment_keeps_relevant_non_secret_variables(monkeypatch):
    monkeypatch.setenv("CRYPTO_BACKTEST_WINDOW", "500")

    snapshot = capture_environment(include_packages=False)

    assert snapshot.environment_variables["CRYPTO_BACKTEST_WINDOW"] == "500"


def test_environment_summary_is_json_safe():
    summary = environment_summary(capture_environment(include_packages=False))

    assert set(summary) == {
        "python_version",
        "platform",
        "architecture",
        "hostname",
        "captured_at",
        "git_commit",
        "git_dirty",
        "packages",
    }
    json.dumps(summary)  # must not raise


# -- seeds and manifests -----------------------------------------------------


def test_deterministic_seeds_make_random_reproducible():
    seeds = set_deterministic_seeds(1234)

    assert seeds["random"] == 1234
    assert seeds["pythonhash"] == 1234
    first = random.random()
    set_deterministic_seeds(1234)
    assert random.random() == first


def test_manifest_round_trips(tmp_path):
    manifest = create_run_manifest(
        experiment_id="exp-1",
        configuration={"fast": "5"},
        seeds={"random": 42},
    )
    path = tmp_path / "nested" / "manifest.json"
    save_manifest(manifest, path)

    restored = load_manifest(path)

    assert restored.run_id == manifest.run_id
    assert restored.experiment_id == "exp-1"
    assert restored.seeds == {"random": 42}
    assert restored.code_hash == manifest.code_hash
    assert restored.environment.python_version == manifest.environment.python_version


# -- experiment records ------------------------------------------------------


def test_experiment_records_code_hash_and_environment(tmp_path):
    record = _create(_manager(tmp_path))

    assert record.code_hash
    assert record.code_hash != EMPTY_SHA256
    assert record.environment["python_version"] == sys.version.split()[0]
    assert "packages" in record.environment


def test_experiment_respects_an_explicit_code_hash(tmp_path):
    record = _create(_manager(tmp_path), code_hash="custom-hash")

    assert record.code_hash == "custom-hash"


def test_environment_is_captured_once_per_manager(tmp_path):
    manager = _manager(tmp_path)
    first = _create(manager)
    second = _create(manager)

    assert first.environment["captured_at"] == second.environment["captured_at"]
    assert first.environment == second.environment


def test_environment_survives_persistence(tmp_path):
    path = tmp_path / "experiments.json"
    manager = ExperimentManager(storage_path=path)
    record = _create(manager)

    reloaded = ExperimentManager(storage_path=path)
    reloaded.load()

    restored = reloaded.get(record.experiment_id)
    assert restored is not None
    assert restored.environment == record.environment
    assert restored.code_hash == record.code_hash
    assert path.read_text(encoding="utf-8").count("python_version") >= 1

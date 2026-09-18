"""Tests for experiment manager (ROADMAP.md chapter 52)."""

from __future__ import annotations

import json

from crypto_trading_lab.machine_learning.experiment_manager import (
    ExperimentManager,
    ExperimentRecord,
    ExperimentStatus,
    _compute_parameter_checksum,
)


def test_experiment_manager_creates():
    """Should create experiment record."""
    manager = ExperimentManager()
    
    record = manager.create(
        hypothesis="SMA crossover works in trending markets",
        strategy_name="MACrossover",
        strategy_version="1.0.0",
        dataset_version="v1",
        parameters={"fast": "5", "slow": "20"},
    )
    
    assert record.experiment_id != ""
    assert record.hypothesis == "SMA crossover works in trending markets"
    assert record.strategy_name == "MACrossover"


def test_experiment_manager_update_status():
    """Should update experiment status."""
    manager = ExperimentManager()
    record = manager.create(
        hypothesis="Test",
        strategy_name="Test",
        strategy_version="1.0.0",
        dataset_version="v1",
        parameters={},
    )
    
    result = manager.update_status(record.experiment_id, ExperimentStatus.COMPLETED, "Works")
    
    assert result is not None
    assert result.status == ExperimentStatus.COMPLETED
    assert result.conclusion == "Works"


def test_experiment_manager_find_by_strategy():
    """Should find experiments by strategy."""
    manager = ExperimentManager()
    manager.create(
        hypothesis="Test",
        strategy_name="MACrossover",
        strategy_version="1.0.0",
        dataset_version="v1",
        parameters={},
    )
    manager.create(
        hypothesis="Test",
        strategy_name="RSI",
        strategy_version="1.0.0",
        dataset_version="v1",
        parameters={},
    )
    
    results = manager.find_by_strategy("MACrossover")
    
    assert len(results) == 1
    assert results[0].strategy_name == "MACrossover"


def test_experiment_manager_find_by_status():
    """Should find experiments by status."""
    manager = ExperimentManager()
    record = manager.create(
        hypothesis="Test",
        strategy_name="Test",
        strategy_version="1.0.0",
        dataset_version="v1",
        parameters={},
    )
    manager.update_status(record.experiment_id, ExperimentStatus.COMPLETED)
    
    results = manager.find_by_status(ExperimentStatus.COMPLETED)
    
    assert len(results) == 1


def test_experiment_manager_export_import():
    """Should export and import correctly."""
    manager = ExperimentManager()
    manager.create(
        hypothesis="Test hypothesis",
        strategy_name="TestStrategy",
        strategy_version="1.0.0",
        dataset_version="v1",
        parameters={"param": "value"},
    )
    
    exported = manager.export()
    count = manager.import_from_json(exported)
    
    assert count == 1


def test_compute_parameter_checksum():
    """Should compute stable checksum."""
    params1 = {"fast": "5", "slow": "20"}
    params2 = {"slow": "20", "fast": "5"}
    
    assert _compute_parameter_checksum(params1) == _compute_parameter_checksum(params2)


def test_experiment_manager_get():
    """Should get experiment by ID."""
    manager = ExperimentManager()
    record = manager.create(
        hypothesis="Test",
        strategy_name="Test",
        strategy_version="1.0.0",
        dataset_version="v1",
        parameters={},
    )
    
    result = manager.get(record.experiment_id)
    
    assert result is not None
    assert result.experiment_id == record.experiment_id

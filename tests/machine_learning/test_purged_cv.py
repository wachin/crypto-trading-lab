"""Tests for purged K-Fold cross-validation (ROADMAP.md chapter 49.4)."""

from __future__ import annotations

from decimal import Decimal

import pytest

from crypto_trading_lab.machine_learning.purged_cv import (
    LabelInterval,
    PurgedKFoldConfig,
    compute_label_uniqueness,
    create_purged_splits,
)


def test_create_purged_splits_basic():
    """Should generate correct number of splits."""
    n_samples = 100
    labels = [LabelInterval(i, i, i + 1) for i in range(n_samples)]
    config = PurgedKFoldConfig(n_splits=5, embargo_pct=Decimal("0.0"))
    
    splits = list(create_purged_splits(n_samples, labels, config))
    
    assert len(splits) == 5
    for train, test in splits:
        assert len(test) == 20  # 100 / 5


def test_create_purged_splits_exhaustive():
    """All samples should appear in test at least once."""
    n_samples = 100
    labels = [LabelInterval(i, i, i + 1) for i in range(n_samples)]
    config = PurgedKFoldConfig(n_splits=5)
    
    splits = list(create_purged_splits(n_samples, labels, config))
    
    all_test = set()
    for _, test in splits:
        all_test.update(test)
    
    assert len(all_test) == n_samples


def test_purged_splits_no_overlap():
    """When no labels overlap, all samples should be usable."""
    n_samples = 100
    # Non-overlapping labels
    labels = [LabelInterval(i, i, i) for i in range(n_samples)]
    config = PurgedKFoldConfig(n_splits=5)
    
    train, test = next(create_purged_splits(n_samples, labels, config))
    
    assert len(train) > 0
    assert len(test) > 0


def test_compute_uniqueness_non_overlapping():
    """Non-overlapping labels should have high uniqueness."""
    labels = [LabelInterval(i, i, i) for i in range(10)]
    uniqueness = compute_label_uniqueness(labels)
    
    assert len(uniqueness) == 10
    assert all(u == Decimal(1) for u in uniqueness)


def test_compute_uniqueness_overlapping():
    """Overlapping labels should have reduced uniqueness."""
    labels = [LabelInterval(i, i, i + 5) for i in range(10)]
    uniqueness = compute_label_uniqueness(labels)
    
    assert len(uniqueness) == 10
    assert any(u < Decimal(1) for u in uniqueness)


def test_compute_uniqueness_empty():
    """Should handle empty labels."""
    uniqueness = compute_label_uniqueness([])
    
    assert uniqueness == []


def test_create_purged_splits_single():
    """Should handle single sample."""
    n_samples = 1
    labels = [LabelInterval(0, 0, 0)]
    config = PurgedKFoldConfig(n_splits=1)
    
    splits = list(create_purged_splits(n_samples, labels, config))
    assert len(splits) == 1

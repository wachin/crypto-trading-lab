"""Purged K-Fold cross-validation with embargo (ROADMAP.md chapter 49.4).

This implements the canonical purged/embargoed cross-validation from López
de Prado (2018), which prevents data leakage when labels have overlapping
time intervals.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Generator, Sequence


@dataclass(frozen=True)
class LabelInterval:
    """Time interval for a labeled observation (49.4)."""
    index: int
    start: int  # Index where label computation starts
    end: int  # Index where label ends (first barrier hit)


@dataclass(frozen=True)
class PurgedKFoldConfig:
    """Configuration for purged/embargoed CV (49.4)."""
    n_splits: int = 5
    embargo_pct: Decimal = Decimal("0.01")  # 1% embargo


def create_purged_splits(
    n_samples: int,
    labels: Sequence[LabelInterval],
    config: PurgedKFoldConfig | None = None,
) -> Generator[tuple[list[int], list[int]], None, None]:
    """
    Generate purged/embargoed train/test splits (49.4).
    
    - Training observations whose label intervals overlap any test
      label interval are removed from training (purging)
    - Additional observations after test blocks are also removed (embargo)
    
    Yields: (train_indices, test_indices) tuples
    """
    config = config or PurgedKFoldConfig()
    
    # Group samples into n_splits groups
    group_size = n_samples // config.n_splits
    groups = list(range(n_samples))
    
    for fold in range(config.n_splits):
        # Test fold
        start = fold * group_size
        end = start + group_size if fold < config.n_splits - 1 else n_samples
        
        test_indices = list(range(start, end))
        
        # Find label intervals that overlap with test
        test_label_indices = set()
        for idx in test_indices:
            if 0 <= idx < len(labels):
                test_label_indices.add(idx)
        
        # Purge: find training indices whose labels overlap test
        purge_indices = set()
        for idx in range(n_samples):
            if idx in test_indices:
                continue
            if 0 <= idx < len(labels):
                label_int = labels[idx]
                # Check if label interval overlaps any test interval
                for t_idx in test_label_indices:
                    if 0 <= t_idx < len(labels):
                        t_int = labels[t_idx]
                        # Overlap check
                        if not (label_int.end < t_int.start or label_int.start > t_int.end):
                            purge_indices.add(idx)
                            break
        
        # Embargo: remove additional samples after test block
        embargo_size = max(1, int(group_size * config.embargo_pct))
        embargo_start = end
        embargo_end = min(embargo_start + embargo_size, n_samples)
        embargo_indices = set(range(embargo_start, embargo_end))
        
        # Build train set
        train_indices = [
            idx for idx in range(n_samples)
            if idx not in test_indices and idx not in purge_indices
            and idx not in embargo_indices
        ]
        
        yield train_indices, test_indices


def compute_label_uniqueness(
    labels: Sequence[LabelInterval],
) -> list[Decimal]:
    """
    Compute average uniqueness for each observation (49.3).
    
    Overlapping label intervals reduce effective sample size.
    """
    n = len(labels)
    if n == 0:
        return []
    
    uniqueness = []
    for i in range(n):
        if i >= len(labels):
            uniqueness.append(Decimal(0))
            continue
        
        interval = labels[i]
        overlap_count = 0
        
        for j in range(n):
            if i == j:
                continue
            if j >= len(labels):
                continue
            other = labels[j]
            
            # Check overlap
            if not (interval.end < other.start or interval.start > other.end):
                overlap_count += 1
        
        # Uniqueness: 1 - (overlap_count / (n - 1))
        if n > 1:
            u = Decimal(1) - Decimal(overlap_count) / Decimal(n - 1)
        else:
            u = Decimal(1)
        
        uniqueness.append(max(Decimal(0), u))
    
    return uniqueness


PURGED_KFOLD_WARNING = (
    "Purged/embargoed cross-validation is used when labels have "
    "overlapping time intervals. Purging removes training samples "
    "whose labels overlap test samples. Embargo adds a buffer after "
    "test blocks. Both prevent data leakage but reduce effective "
    "training size."
)

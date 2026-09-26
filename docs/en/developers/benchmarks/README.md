# Benchmarks - Numba vs Decimal

## What was measured

Performance comparison between Python's `Decimal` type and Numba JIT compilation for financial calculations:

1. **Drawdown calculation** - Maximum drawdown computation over equity curves
2. **Equity returns** - Return calculation from equity curves

## When

Run date: 2026-09-26

## Results Summary

| Operation | N=1,000 | N=10,000 | N=100,000 | N=1,000,000 |
|-----------|---------|----------|-----------|-------------|
| Drawdowns | 3.1x slower | 2.9x slower | 2.8x slower | 2.4x slower |
| Equity Returns | 5.4x slower | - | 2.8x slower | - |

## Accuracy

| Metric | Decimal | Numba+float64 | Difference |
|--------|---------|---------------|------------|
| Max Drawdown | 0.03927534670222325261 | 0.03927534670222339000 | 1.37e-16 |

## Why Numba Was Discarded

1. **Conversion overhead dominates**: Converting `Decimal` → `float64` for Numba consumes >99% of execution time. The raw JIT speedup (~250x-1500x) is completely negated by conversion overhead.

2. **Precision loss**: Numba uses `float64` which cannot represent decimal values exactly. The drawdown results differ by ~1e-16, violating the project's requirement for exact decimal arithmetic (AGENTS.md §4, ROADMAP.md Chapter 7: "Money is Decimal, never float").

3. **No net benefit**: After conversion overhead, Numba is 2.4x-5.4x **slower** than pure Python `Decimal`.

## Decision

**Numba was removed from the project.** The pure Python `Decimal` implementation is:
- Correct (exact arithmetic)
- Faster in practice (no conversion overhead)
- Simpler (no JIT compilation step)
- Compliant with project requirements (exact decimal arithmetic)

## Files

- `numba-vs-decimal-2026-09-26.py` - This benchmark script
- Original location: `benchmarks/numba_vs_decimal.py`
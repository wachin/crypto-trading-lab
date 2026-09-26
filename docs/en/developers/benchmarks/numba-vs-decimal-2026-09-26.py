#!/usr/bin/env python3
"""Empirical benchmark: does numba actually help Crypto Trading Lab?

Answers one question with measurements, not opinions:
given the project's rule "money is Decimal, never float"
(AGENTS.md §4, ROADMAP chapter 7), does the numba-accelerated
path in performance/numba_accel.py earn its dependency?

Run:
    python3 benchmarks/numba_vs_decimal.py

What it measures, for each size N:
  1. Pure-Python Decimal path — the code that actually ships in
     backtesting/metrics.py today.
  2. Numba + conversion — Decimal tuple -> numpy float64 -> numba.
     This is what any real integration must pay.
  3. Numba raw — numpy array already in memory -> numba. Upper bound,
     not free in practice.
  4. Accuracy — max |Decimal - numba result| on the same input.

Decision rule printed at the end.
"""

from __future__ import annotations

import random
import statistics
import time
from decimal import Decimal
from typing import Callable, Sequence


# --- the shipping implementation (imported, not re-implemented) ---------

from crypto_trading_lab.backtesting.metrics import (
    _drawdowns as decimal_drawdowns,
    _equity_returns as decimal_equity_returns,
)


def numba_available() -> bool:
    try:
        from crypto_trading_lab.performance.numba_accel import (
            NUMBA_AVAILABLE,
        )
        return NUMBA_AVAILABLE
    except Exception:
        return False


def numba_drawdowns(equity_curve: tuple[Decimal, ...]):
    """The numba path as it exists today, conversion included."""
    from crypto_trading_lab.performance.numba_accel import drawdowns
    return drawdowns(equity_curve)


def numba_drawdowns_raw(curve_array):
    """Numba on an already-converted array (upper bound)."""
    from crypto_trading_lab.performance.numba_accel import _drawdowns_numba
    return _drawdowns_numba(curve_array)


def numba_equity_returns(equity_curve: tuple[Decimal, ...]):
    from crypto_trading_lab.performance.numba_accel import equity_returns
    return equity_returns(equity_curve)


# --- synthetic data -----------------------------------------------------

def synthetic_equity_curve(n: int, seed: int = 42) -> tuple[Decimal, ...]:
    """A realistic equity curve: drifting random walk with drawdowns."""
    rng = random.Random(seed)
    value = Decimal("10000")
    curve = [value]
    for _ in range(n - 1):
        delta = Decimal(str(rng.uniform(-0.005, 0.0055)))
        value = value * (Decimal(1) + delta)
        curve.append(value)
    return tuple(curve)


# --- timing -------------------------------------------------------------

def time_call(fn: Callable[[], object], repeats: int = 3) -> float:
    """Median wall time in seconds over ``repeats`` runs."""
    times = []
    for _ in range(repeats):
        start = time.perf_counter()
        fn()
        times.append(time.perf_counter() - start)
    return statistics.median(times)


def fmt(seconds: float) -> str:
    if seconds != seconds:  # NaN
        return "     n/a"
    if seconds < 1e-3:
        return f"{seconds * 1e6:6.0f} us"
    if seconds < 1:
        return f"{seconds * 1e3:6.1f} ms"
    return f"{seconds:6.3f} s "


# --- benchmarks ---------------------------------------------------------

def benchmark_drawdowns(sizes: Sequence[int]) -> None:
    print("=" * 82)
    print("DRAWDOWNS — pure Python Decimal vs numba")
    print("=" * 82)
    print(f"{'N':>9}  {'decimal':>9}  {'numba+conv':>11}  "
          f"{'numba raw':>10}  {'raw speedup':>12}")
    print("-" * 82)

    for n in sizes:
        curve = synthetic_equity_curve(n)

        t_dec = time_call(lambda: decimal_drawdowns(curve))
        t_conv = time_call(lambda: numba_drawdowns(curve))

        if numba_available():
            import numpy as np
            raw = np.array([float(x) for x in curve], dtype=np.float64)
            t_raw = time_call(lambda: numba_drawdowns_raw(raw))
            speedup = t_dec / t_raw if t_raw > 0 else float("inf")
            speedup_s = f"{speedup:10.1f}x"
        else:
            t_raw = float("nan")
            speedup_s = "       n/a"

        print(f"{n:>9}  {fmt(t_dec):>9}  {fmt(t_conv):>11}  "
              f"{fmt(t_raw):>10}  {speedup_s:>12}")
    print()


def benchmark_equity_returns(sizes: Sequence[int]) -> None:
    print("=" * 82)
    print("EQUITY RETURNS — pure Python Decimal vs numba")
    print("=" * 82)
    print(f"{'N':>9}  {'decimal':>9}  {'numba+conv':>11}  {'raw speedup':>14}")
    print("-" * 82)

    for n in sizes:
        curve = synthetic_equity_curve(n)
        t_dec = time_call(lambda: decimal_equity_returns(curve))
        t_conv = time_call(lambda: numba_equity_returns(curve))
        # raw speedup needs the underlying array; estimate from previous run
        if numba_available():
            import numpy as np
            from crypto_trading_lab.performance.numba_accel import (
                _equity_returns_numba,
            )
            raw = np.array([float(x) for x in curve], dtype=np.float64)
            t_raw = time_call(lambda: _equity_returns_numba(raw))
            speedup_s = f"{t_dec / t_raw:10.1f}x" if t_raw > 0 else "       n/a"
        else:
            speedup_s = "       n/a"
        print(f"{n:>9}  {fmt(t_dec):>9}  {fmt(t_conv):>11}  {speedup_s:>14}")
    print()


def benchmark_accuracy(sizes: Sequence[int]) -> None:
    print("=" * 82)
    print("ACCURACY — can numba reproduce the Decimal result exactly?")
    print("=" * 82)
    for n in sizes:
        curve = synthetic_equity_curve(n)
        dd_dec, _ = decimal_drawdowns(curve)
        if not dd_dec:
            continue

        result = numba_drawdowns(curve)
        # The current numba_accel.py has inconsistent return shapes:
        # 3-tuple from the numba branch, 2-tuple from the fallback.
        dd_num_list = result[0] if result else []
        if not dd_num_list:
            print(f"  N = {n:>8}  -> numba path returned empty "
                  f"(check numba_accel.py fallback)")
            continue

        max_dd_dec = max(dd_dec)
        max_dd_num = max(dd_num_list)
        diff = abs(max_dd_dec - max_dd_num)

        exact = "EXACT" if diff == 0 else f"differs by {diff}"
        print(f"  N = {n:>8}  max_dd Decimal = {max_dd_dec:.20f}")
        print(f"  {'':>13}  max_dd numba   = {max_dd_num:.20f}")
        print(f"  {'':>13}  {exact}")
    print()


# --- verdict ------------------------------------------------------------

def verdict() -> None:
    print("=" * 82)
    print("VERDICT — read the numbers, then decide")
    print("=" * 82)
    print()
    print("Three questions, in order:")
    print()
    print("1. SPEEDUP: is 'raw speedup' > 5x at the sizes you use?")
    print("   If not, numba adds a dependency for nothing.")
    print()
    print("2. CONVERSION COST: compare 'decimal' vs 'numba+conv'.")
    print("   If they are within 2x of each other, the Decimal -> float")
    print("   conversion eats almost all the win; numba buys little.")
    print()
    print("3. ACCURACY: is the numba result EXACTLY equal to Decimal?")
    print("   float64 has ~15-17 significant digits. Decimal does not")
    print("   round. If the accuracy block shows any difference, the")
    print("   numba path violates AGENTS.md §4 and ROADMAP chapter 7")
    print("   ('money is Decimal, never float') for any value derived")
    print("   from money.")
    print()
    print("Decision:")
    print("  * speedup > 5x AND accuracy EXACT     -> integrate")
    print("  * speedup > 5x AND accuracy differs   -> do NOT integrate")
    print("                                           into the money path")
    print("  * speedup <= 5x                        -> remove")
    print("                                           numba_accel.py and")
    print("                                           drop the dependency.")
    print("                                           The best part is no part.")
    print()


def main() -> int:
    print()
    print(f"numba available: {numba_available()}")
    print()
    sizes = (1_000, 10_000, 100_000, 1_000_000)
    benchmark_drawdowns(sizes)
    benchmark_equity_returns(sizes)
    benchmark_accuracy(sizes)
    verdict()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

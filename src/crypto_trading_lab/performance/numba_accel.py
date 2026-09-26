"""Performance-optimized functions using Numba JIT compilation (ROADMAP.md chapter 373).

This module provides Numba-accelerated versions of performance-critical
functions. Falls back to pure Python implementations when Numba is not available.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Optional

try:
    import numba
    from numba import jit
    import numpy as np
    NUMBA_AVAILABLE = True
except ImportError:
    NUMBA_AVAILABLE = False
    # Fallback decorator that does nothing
    def jit(*args, **kwargs):
        def decorator(func):
            return func
        return decorator


if NUMBA_AVAILABLE:
    import numpy as np

    @jit(nopython=True, cache=True)
    def _std_numba(values: np.ndarray, mean: float) -> float:
        """Numba-accelerated standard deviation calculation."""
        variance = np.sum((values - mean) ** 2) / len(values)
        return np.sqrt(variance)

    @jit(nopython=True, cache=True)
    def _equity_returns_numba(equity_curve: np.ndarray) -> np.ndarray:
        """Numba-accelerated equity returns calculation."""
        n = len(equity_curve)
        returns = np.empty(n - 1, dtype=np.float64)
        for i in range(n - 1):
            prev = equity_curve[i]
            if prev == 0:
                returns[i] = np.nan
            else:
                returns[i] = (equity_curve[i + 1] - equity_curve[i]) / equity_curve[i]
        return returns

    @jit(nopython=True, cache=True)
    def _drawdowns_numba(equity_curve: np.ndarray):
        """Numba-accelerated drawdown calculation."""
        n = len(equity_curve)
        drawdowns = np.empty(n - 1, dtype=np.float64)
        peak = equity_curve[0]
        streak = 0
        max_streak = 0
        
        for i in range(1, n):
            equity = equity_curve[i]
            if equity > peak:
                peak = equity_curve[i]
            if peak > 0 and equity < peak:
                drawdowns[i - 1] = (peak - equity) / peak
                streak += 1
                if streak > max_streak:
                    max_streak = streak
            else:
                streak = 0
        
        max_dd = np.max(drawdowns) if len(drawdowns) > 0 else 0.0
        return drawdowns, max_dd, max_streak


# Fallback implementations when Numba is not available
def _equity_returns_fallback(equity_curve: tuple[Decimal, ...]) -> list[Decimal]:
    """Fallback equity returns calculation using pure Python Decimal."""
    from decimal import Decimal
    returns: list[Decimal] = []
    for previous, current in zip(equity_curve, equity_curve[1:]):
        if previous == 0:
            continue
        returns.append((current - previous) / previous)
    return returns


def _drawdowns_fallback(
    equity_curve: tuple[Decimal, ...]
) -> tuple[list[Decimal], int]:
    """Fallback drawdown calculation using pure Python Decimal."""
    from decimal import Decimal
    peak = equity_curve[0]
    drawdowns: list[Decimal] = []
    streak = 0
    max_streak = 0
    for equity in equity_curve[1:]:
        if equity > peak:
            peak = equity
        if peak > 0:
            drawdown = (peak - equity) / peak
            if equity < peak:
                streak += 1
            else:
                streak = 0
    max_dd = max(drawdowns) if drawdowns else Decimal(0)
    return drawdowns, max_streak


# Public API - automatically uses Numba if available
def equity_returns(equity_curve):
    """Calculate equity returns, using Numba if available."""
    if NUMBA_AVAILABLE:
        import numpy as np
        curve = np.array([float(x) for x in equity_curve], dtype=np.float64)
        returns = _equity_returns_numba(curve)
        return [Decimal(str(r)) for r in returns if not np.isnan(r)]
    else:
        return _equity_returns_fallback(equity_curve)


def drawdowns(equity_curve):
    """Calculate drawdowns, using Numba if available."""
    if NUMBA_AVAILABLE:
        import numpy as np
        curve = np.array([float(x) for x in equity_curve], dtype=np.float64)
        drawdowns_np, max_dd, max_dd_duration = _drawdowns_numba(curve)
        max_dd_decimal = Decimal(str(max_dd))
        return [Decimal(str(d)) for d in drawdowns_np], max_dd_decimal, int(max_dd_duration)
    else:
        return _drawdowns_fallback(equity_curve)


def std(values, mean):
    """Calculate standard deviation, using Numba if available."""
    if NUMBA_AVAILABLE:
        import numpy as np
        values_np = np.array([float(v) for v in values], dtype=np.float64)
        mean_f = float(mean)
        return Decimal(str(_std_numba(values_np, mean_f)))
    else:
        from decimal import Decimal
        variance = sum((v - mean) ** 2 for v in values) / len(values)
        return variance.sqrt()
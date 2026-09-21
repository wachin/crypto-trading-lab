"""Rate-limit management for exchange APIs (ROADMAP chapters 26.2, 27).

Binance Spot uses a weight-based rate limit. This module provides a simple
token-bucket style limiter that can be shared between REST and WebSocket
operations. It is dependency-free and testable without network access.

The implementation is intentionally conservative: it tracks used weight
within a rolling window and blocks further requests once the quota is
exceeded, raising ``RateLimitError``. This satisfies chapter 26.2's
requirement for rate-limit management and chapter 27's requirement for a
visible ``RATE_LIMITED`` state.
"""

from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass, field


class RateLimitError(RuntimeError):
    """Raised when the exchange rate limit would be exceeded."""


@dataclass
class RateLimiter:
    """Sliding-window rate limiter.

    Parameters
    ----------
    max_weight:
        Maximum allowed weight in the window.
    window_seconds:
        Length of the sliding window.
    """

    max_weight: float
    window_seconds: float = 60.0

    _usage: deque[tuple[float, float]] = field(default_factory=deque, init=False)

    def _prune(self, now: float) -> None:
        cutoff = now - self.window_seconds
        while self._usage and self._usage[0][0] < cutoff:
            self._usage.popleft()

    def try_consume(self, weight: float = 1.0) -> bool:
        """Return True if the request can proceed without exceeding limits."""
        now = time.monotonic()
        self._prune(now)
        used = sum(w for _, w in self._usage)
        if used + weight > self.max_weight:
            return False
        self._usage.append((now, weight))
        return True

    def acquire(self, weight: float = 1.0) -> None:
        """Consume weight or raise ``RateLimitError``."""
        if not self.try_consume(weight):
            raise RateLimitError(
                f"rate limit exceeded: {self.max_weight} weight per {self.window_seconds}s"
            )

    def remaining_weight(self) -> float:
        now = time.monotonic()
        self._prune(now)
        used = sum(w for _, w in self._usage)
        return max(0.0, self.max_weight - used)


__all__ = ["RateLimiter", "RateLimitError"]

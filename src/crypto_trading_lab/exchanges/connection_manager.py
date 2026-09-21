"""Connection state management for live market data (ROADMAP chapter 27).

This module provides the reusable primitives for WebSocket reconnection with
exponential backoff, circuit breaking and stale-data detection required by
chapters 26.2 and 27. The implementation is dependency-free and testable
without network access.

Every public class documents the beginner-facing purpose of its behaviour so
the UI can show plain-language status labels as required by chapter 27.
"""

from __future__ import annotations

import random
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional


class CircuitState(str, Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class ReconnectionPolicy:
    """Exponential backoff with jitter for WebSocket reconnection.

    Parameters
    ----------
    base_delay:
        Initial delay in seconds for the first retry.
    max_delay:
        Upper bound for the delay; prevents unbounded growth.
    max_retries:
        Maximum number of attempts before giving up. ``None`` means retry
        indefinitely.
    jitter:
        Fraction of the delay to randomise (0.0–1.0). A jitter of 0.2 adds
        +-20 % randomness to avoid thundering herds.
    """

    base_delay: float = 1.0
    max_delay: float = 60.0
    max_retries: Optional[int] = None
    jitter: float = 0.2

    def next_delay(self, attempt: int) -> float:
        """Return the next retry delay for ``attempt`` (1-indexed)."""
        if attempt < 1:
            raise ValueError("attempt must be >= 1")
        if self.max_retries is not None and attempt > self.max_retries:
            raise StopIteration("maximum retries exceeded")
        raw = self.base_delay * (2 ** (attempt - 1))
        capped = min(raw, self.max_delay)
        if self.jitter <= 0:
            return capped
        jitter_factor = 1.0 + random.uniform(-self.jitter, self.jitter)
        return max(0.0, capped * jitter_factor)

    def should_retry(self, attempt: int) -> bool:
        """Return True if another attempt is allowed."""
        return self.max_retries is None or attempt <= self.max_retries


@dataclass
class CircuitBreaker:
    """Circuit breaker to stop hammering a failing exchange endpoint.

    The breaker opens after ``failure_threshold`` consecutive failures and
    stays open for ``reset_timeout`` seconds. While open, further attempts are
    rejected immediately to protect both the client and the exchange
    (chapter 27).
    """

    failure_threshold: int = 5
    reset_timeout: float = 60.0

    _state: CircuitState = field(default=CircuitState.CLOSED, init=False)
    _failures: int = field(default=0, init=False)
    _opened_at: Optional[float] = field(default=None, init=False)

    def record_success(self) -> None:
        self._failures = 0
        self._opened_at = None
        if self._state != CircuitState.CLOSED:
            self._state = CircuitState.CLOSED

    def record_failure(self) -> None:
        self._failures += 1
        if self._state == CircuitState.CLOSED and self._failures >= self.failure_threshold:
            self._state = CircuitState.OPEN
            self._opened_at = time.monotonic()
        elif self._state == CircuitState.HALF_OPEN:
            # failure in half-open trips the breaker again
            self._state = CircuitState.OPEN
            self._opened_at = time.monotonic()

    def can_attempt(self) -> bool:
        if self._state == CircuitState.CLOSED:
            return True
        if self._state == CircuitState.OPEN:
            if self._opened_at is None:
                return False
            elapsed = time.monotonic() - self._opened_at
            if elapsed >= self.reset_timeout:
                self._state = CircuitState.HALF_OPEN
                return True
            return False
        # HALF_OPEN: allow a single probe
        return True

    @property
    def state(self) -> CircuitState:
        return self._state


@dataclass
class StaleDataDetector:
    """Detects when the last market update is too old.

    Chapter 27 requires stale-data detection that halts strategy evaluation
    and surfaces a visible DEGRADED warning. This detector tracks the most
    recent update timestamp and reports staleness against a configurable
    maximum age.
    """

    max_age_seconds: float = 30.0
    _last_update: Optional[float] = field(default=None, init=False)

    def touch(self, when: Optional[datetime] = None) -> None:
        """Record a fresh data arrival."""
        ts = when
        if ts is None:
            ts = datetime.now(timezone.utc)
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        self._last_update = ts.timestamp()

    def is_stale(self, now: Optional[datetime] = None) -> bool:
        if self._last_update is None:
            return True
        if now is None:
            now = datetime.now(timezone.utc)
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)
        age = now.timestamp() - self._last_update
        return age > self.max_age_seconds

    @property
    def age_seconds(self) -> Optional[float]:
        if self._last_update is None:
            return None
        return time.time() - self._last_update


__all__ = [
    "ReconnectionPolicy",
    "CircuitBreaker",
    "CircuitState",
    "StaleDataDetector",
]

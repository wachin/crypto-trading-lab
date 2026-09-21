"""Tests for rate limiter (ROADMAP chapters 26.2, 27)."""

import time

import pytest

from crypto_trading_lab.exchanges.rate_limiter import RateLimitError, RateLimiter


class TestRateLimiter:
    def test_allows_within_limit(self):
        rl = RateLimiter(max_weight=10, window_seconds=1.0)
        for i in range(10):
            assert rl.try_consume(1.0)

    def test_blocks_over_limit(self):
        rl = RateLimiter(max_weight=5, window_seconds=1.0)
        for _ in range(5):
            rl.acquire(1.0)
        assert not rl.try_consume(1.0)
        with pytest.raises(RateLimitError):
            rl.acquire(1.0)

    def test_window_expiry(self):
        rl = RateLimiter(max_weight=2, window_seconds=0.05)
        rl.acquire(1.0)
        rl.acquire(1.0)
        with pytest.raises(RateLimitError):
            rl.acquire(1.0)
        time.sleep(0.06)
        assert rl.try_consume(1.0)

    def test_remaining_weight(self):
        rl = RateLimiter(max_weight=10, window_seconds=1.0)
        rl.acquire(3.0)
        assert rl.remaining_weight() == 7.0

    def test_weighted_requests(self):
        rl = RateLimiter(max_weight=10, window_seconds=1.0)
        rl.acquire(6.0)
        assert rl.remaining_weight() == 4.0
        with pytest.raises(RateLimitError):
            rl.acquire(5.0)
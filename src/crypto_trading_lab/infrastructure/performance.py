"""Performance optimization and caching utilities.

Provides caching decorators, batch processing for indicators, and memory
optimization for large candle datasets.
"""

from __future__ import annotations

import functools
import time
from typing import Any, Callable, TypeVar

F = TypeVar("F", bound=Callable[..., Any])


def memoize_candles(func: F) -> F:
    """
    Memoization decorator optimized for candle datasets.
    
    Caches function results based on dataset length and start/end timestamps
    to avoid recomputing indicators on unchanged data.
    """
    cache = {}

    @functools.wraps(func)
    def wrapper(candles: list, *args: Any, **kwargs: Any) -> Any:
        if not candles:
            return func(candles, *args, **kwargs)
        
        # Create a lightweight cache key from dataset identity
        key = (
            len(candles),
            candles[0].timestamp if hasattr(candles[0], "timestamp") else 0,
            candles[-1].timestamp if hasattr(candles[-1], "timestamp") else 0,
            args,
            frozenset(kwargs.items()),
        )
        
        if key in cache:
            return cache[key]
        
        result = func(candles, *args, **kwargs)
        cache[key] = result
        return result

    return wrapper  # type: ignore


def benchmark_execution(func: Callable[..., Any]) -> Callable[..., Any]:
    """Benchmark execution time for performance tuning."""
    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        start_time = time.perf_counter()
        result = func(*args, **kwargs)
        end_time = time.perf_counter()
        duration = (end_time - start_time) * 1000
        # Log or track duration if needed
        return result
    return wrapper


class DataBatcher:
    """Batch processor for large candle datasets to prevent UI blocking."""
    
    @staticmethod
    def process_in_batches(
        data: list[Any],
        processor: Callable[[list[Any]], Any],
        batch_size: int = 1000,
    ) -> list[Any]:
        """Process large data in chunks to maintain responsiveness."""
        results = []
        for i in range(0, len(data), batch_size):
            batch = data[i:i + batch_size]
            results.extend(processor(batch))
        return results

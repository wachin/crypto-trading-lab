"""Performance optimization and caching utilities.

Provides caching decorators, batch processing for indicators, and memory
optimization for large candle datasets.
"""
from __future__ import annotations

import time
import functools
from typing import Any, Callable, TypeVar, Optional

F = TypeVar("F", bound=Callable[..., Any])

def memoize_candles(ttl_seconds: int = 300) -> Callable:
    """Memoization decorator for candle data processing."""
    def decorator(func: F) -> F:
        cache = {}
        access_times = {}
        
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            key = str(args) + str(kwargs)
            now = time.monotonic()
            
            if key in cache and (now - access_times.get(key, 0) < ttl_seconds):
                return cache[key]
            
            result = func(*args, **kwargs)
            cache[key] = result
            access_times[key] = now
            return result
        return wrapper # type: ignore
    return decorator

class DataBatcher:
    """Batch processor for large candle datasets."""
    @staticmethod
    def process_in_batches(data: list, processor: Callable[[list], Any], batch_size: int = 100) -> list:
        results = []
        for i in range(0, len(data), batch_size):
            results.extend(processor(data[i:i + batch_size]))
        return results

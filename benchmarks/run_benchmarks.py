#!/usr/bin/env python3
"""Performance benchmarks (ROADMAP.md chapter 13).

Run with: python3 benchmarks/run_benchmarks.py
"""

import time
import sys
import tempfile
import csv
import sqlite3
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from crypto_trading_lab.domain.models import Candle
from crypto_trading_lab.domain.models import Symbol
from decimal import Decimal
from datetime import datetime, timedelta, timezone


def generate_candles(n: int) -> list[Candle]:
    """Generate N test candles."""
    candles = []
    start = datetime(2024, 1, 1, tzinfo=timezone.utc)
    sym = Symbol("BTC/USDT")
    for i in range(n):
        price = Decimal(50000 + i * 10)
        t = start + timedelta(minutes=i * 5)
        candles.append(Candle(
            symbol=sym,
            interval="5m",
            open_time=t,
            close_time=t + timedelta(minutes=5),
            open=price,
            high=price + Decimal(100),
            low=price - Decimal(100),
            close=price + Decimal(50),
            volume=Decimal(1000)
        ))
    return candles


def benchmark_csv_loading(candles: list[Candle]) -> float:
    """Benchmark CSV export and load."""
    from io import StringIO

    # Export to CSV string
    buffer = StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["symbol", "interval", "open_time", "close_time",
                     "open", "high", "low", "close", "volume"])
    for c in candles:
        writer.writerow([
            str(c.symbol), c.interval,
            c.open_time.isoformat(), c.close_time.isoformat(),
            str(c.open), str(c.high), str(c.low), str(c.close), str(c.volume)
        ])
    csv_data = buffer.getvalue()

    # Benchmark loading
    start = time.perf_counter()
    reader = csv.DictReader(StringIO(csv_data))
    for row in reader:
        pass  # just parse
    elapsed = time.perf_counter() - start
    return elapsed


def benchmark_sqlite_insertion(candles: list[Candle]) -> float:
    """Benchmark SQLite insertion."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "bench.db"
        conn = sqlite3.connect(db_path)
        conn.execute("""
            CREATE TABLE candles (
                id INTEGER PRIMARY KEY,
                symbol TEXT NOT NULL,
                interval TEXT NOT NULL,
                open_time TEXT NOT NULL,
                close_time TEXT NOT NULL,
                open_price TEXT NOT NULL,
                high_price TEXT NOT NULL,
                low_price TEXT NOT NULL,
                close_price TEXT NOT NULL,
                volume TEXT NOT NULL
            )
        """)
        conn.commit()

        start = time.perf_counter()
        cursor = conn.cursor()
        for c in candles:
            cursor.execute(
                "INSERT INTO candles (symbol, interval, open_time, close_time, open_price, high_price, low_price, close_price, volume) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (str(c.symbol), c.interval, c.open_time.isoformat(), c.close_time.isoformat(),
                 str(c.open), str(c.high), str(c.low), str(c.close), str(c.volume))
            )
        conn.commit()
        elapsed = time.perf_counter() - start
    return elapsed


def benchmark_backtest(candles: list[Candle]) -> float:
    """Benchmark backtest execution."""
    from crypto_trading_lab.backtesting.engine import run_backtest, MACrossoverStrategy
    strategy = MACrossoverStrategy(fast=20, slow=50)
    start = time.perf_counter()
    result = run_backtest(candles, strategy)
    elapsed = time.perf_counter() - start
    return elapsed


def main():
    sizes = [1000, 10000, 50000, 100000]

    print("=" * 70)
    print("CRYPTO TRADING LAB — PERFORMANCE BENCHMARKS")
    print("=" * 70)

    for n in sizes:
        candles = generate_candles(n)

        # CSV loading
        csv_time = benchmark_csv_loading(candles)
        print(f"\n{n:>6} candles:")
        print(f"  CSV loading:      {csv_time*1000:.2f} ms")

        # SQLite insertion
        sqlite_time = benchmark_sqlite_insertion(candles)
        print(f"  SQLite insertion: {sqlite_time*1000:.2f} ms")

        # Backtest
        bt_time = benchmark_backtest(candles)
        print(f"  Backtest:         {bt_time*1000:.2f} ms")

    print("\n" + "=" * 70)


if __name__ == "__main__":
    main()
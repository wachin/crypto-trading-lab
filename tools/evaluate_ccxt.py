#!/usr/bin/env python3
"""Decide whether the optional ``ccxt`` dependency is worth adopting.

Read-only and **offline by default**: it inspects what is installed and
whether the project's own adapter accepts a real ccxt client. Pass
``--network`` to also touch one public endpoint.

Run it inside the virtualenv described in
``docs/en/developers/venv-setup.md``:

    source .venv/bin/activate
    python tools/evaluate_ccxt.py

It never installs anything. If ccxt is missing it prints the exact commands
for the maintainer to run.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

#: Exchanges that would justify the dependency (chapter 26.3 needs Coinbase).
EXCHANGES_OF_INTEREST = ("binance", "coinbase")

#: The snake_case ccxt surface our adapter calls on the injected client.
REQUIRED_SURFACE = (
    "fetch_markets",
    "fetch_ticker",
    "fetch_ohlcv",
    "fetch_balance",
    "fetch_open_orders",
    "precisionMode",
)

INSTALL_HINT = """\
ccxt is not installed. It is a PyPI-only extra; the maintainer installs it
inside a virtualenv (never with --break-system-packages):

    cd {root}
    python3 -m venv --system-site-packages .venv
    source .venv/bin/activate
    python -m pip install ccxt

Then re-run: python tools/evaluate_ccxt.py
See docs/en/developers/venv-setup.md for the full guide.
"""


def _report_exchange(ccxt, name: str) -> bool:
    """Print one exchange's coverage; return True when it is usable."""
    factory = getattr(ccxt, name, None)
    if factory is None:
        print(f"  {name:<9} MISSING from this ccxt build")
        return False
    try:
        client = factory({"enableRateLimit": True})
    except Exception as error:  # report, never crash the evaluation
        print(f"  {name:<9} cannot be instantiated: {error}")
        return False

    missing = [item for item in REQUIRED_SURFACE if not hasattr(client, item)]
    has = getattr(client, "has", {}) or {}
    print(f"  {name:<9} id={getattr(client, 'id', '?')}")
    print(
        "            fetchOHLCV={} fetchTicker={} fetchMarkets={}".format(
            has.get("fetchOHLCV"),
            has.get("fetchTicker"),
            has.get("fetchMarkets"),
        )
    )
    if missing:
        print(f"            MISSING surface: {', '.join(missing)}")
        return False
    print("            required surface: OK")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Evaluate whether ccxt is worth adopting."
    )
    parser.add_argument(
        "--network",
        action="store_true",
        help="also call one public endpoint (off by default)",
    )
    args = parser.parse_args()

    try:
        import ccxt
    except ImportError:
        print(INSTALL_HINT.format(root=ROOT))
        return 1

    print(f"ccxt {getattr(ccxt, '__version__', '?')}")
    exchanges = list(getattr(ccxt, "exchanges", []))
    print(f"exchanges covered: {len(exchanges)}")

    results = {
        name: _report_exchange(ccxt, name) for name in EXCHANGES_OF_INTEREST
    }

    print("\nProject adapter:")
    adapter_ok = True
    try:
        from crypto_trading_lab.exchanges.ccxt.adapter import (
            CcxtExchangeAdapter,
        )

        client = getattr(ccxt, EXCHANGES_OF_INTEREST[0])({"enableRateLimit": True})
        adapter = CcxtExchangeAdapter(client)
        print(f"  accepts a real ccxt client: {type(adapter).__name__}")
        print(f"  capabilities: {adapter.capabilities}")
    except Exception as error:  # a failure here is a finding, not a crash
        adapter_ok = False
        print(f"  check failed: {error}")

    if args.network:
        print("\nNetwork probe (--network):")
        try:
            ticker = getattr(ccxt, EXCHANGES_OF_INTEREST[0])().fetch_ticker(
                "BTC/USDT"
            )
            print(f"  BTC/USDT last={ticker.get('last')}")
        except Exception as error:
            print(f"  probe failed (network or geo-block): {error}")

    print("\nVerdict checklist:")
    print("  [x] ccxt importable")
    for name, usable in results.items():
        print(f"  [{'x' if usable else ' '}] {name} usable by our adapter")
    print(f"  [{'x' if adapter_ok else ' '}] adapter accepts a real client")
    print(
        "\nAdopt ccxt only if it buys a second exchange (Coinbase) or removes\n"
        "an adapter we maintain by hand; keep the standard-library path if it\n"
        "only re-wraps Binance. A new dependency is a chapter-4 decision and\n"
        "the maintainer runs the install. See venv-setup.md section 6."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

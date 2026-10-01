#!/usr/bin/env python3
"""Functional verification of Crypto Trading Lab on a new machine.

Run it from the repository root after installing the package:

    python Experiments/verify.py              # fast checks, offline
    python Experiments/verify.py --tests      # also run the full test suite
    python Experiments/verify.py --gui        # also open the real window
    python Experiments/verify.py --network    # also probe ccxt over the network

It writes ``Experiments/verify-report.md`` with everything needed to report a
result back, and never modifies the repository. Nothing here touches real
money: the application is research and paper-trading only.
"""

from __future__ import annotations

import argparse
import os
import platform
import subprocess
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
SAMPLE = HERE / "sample-data" / "btc-usdt-1h-sample.csv"
REPORT = HERE / "verify-report.md"
MIN_PYTHON = (3, 11)

RESULTS: list[tuple[str, str, str]] = []


class Skip(Exception):
    """Raised by an optional check that does not apply on this machine."""


def record(name: str, status: str, detail: str = "") -> None:
    RESULTS.append((name, status, detail))
    suffix = f" — {detail}" if detail else ""
    print(f"[{status:<4}] {name}{suffix}", flush=True)


def check(name: str, fn) -> None:
    """Run one check; a failure is recorded, never fatal."""
    try:
        detail = fn()
    except Skip as reason:
        record(name, "SKIP", str(reason))
    except Exception as error:  # noqa: BLE001 - the point is to report it
        record(name, "FAIL", f"{type(error).__name__}: {error}")
        traceback.print_exc()
    else:
        record(name, "PASS", detail or "")


def _ensure_package_importable() -> None:
    src = str(ROOT / "src")
    if src not in sys.path:
        sys.path.insert(0, src)


# -- checks ------------------------------------------------------------------


def check_python() -> str:
    if sys.version_info < MIN_PYTHON:
        raise RuntimeError(
            f"Python {MIN_PYTHON[0]}.{MIN_PYTHON[1]}+ required, "
            f"found {platform.python_version()}"
        )
    return f"Python {platform.python_version()}"


def check_platform() -> str:
    return f"{platform.platform()} ({platform.machine()})"


def check_runtime_imports() -> str:
    import PyQt6.QtCore
    import platformdirs
    import pyqtgraph
    import sqlalchemy

    return (
        f"PyQt6 {PyQt6.QtCore.PYQT_VERSION_STR}, "
        f"pyqtgraph {pyqtgraph.__version__}, "
        f"SQLAlchemy {sqlalchemy.__version__}, "
        f"platformdirs {platformdirs.__version__}"
    )


def check_numpy() -> str:
    import numpy

    return f"numpy {numpy.__version__}"


def check_package() -> str:
    _ensure_package_importable()
    import crypto_trading_lab

    return f"crypto_trading_lab {crypto_trading_lab.__version__}"


def check_cli() -> str:
    _ensure_package_importable()
    env = _child_env()
    proc = subprocess.run(
        [sys.executable, "-m", "crypto_trading_lab", "--help"],
        capture_output=True,
        text=True,
        env=env,
        cwd=ROOT,
        timeout=60,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"exit {proc.returncode}: {proc.stderr.strip()[:200]}")
    if "doctor" not in proc.stdout:
        raise RuntimeError("the CLI help does not list its commands")
    return "the command-line interface answers"


def check_sample_data() -> str:
    if not SAMPLE.exists():
        raise FileNotFoundError(f"missing {SAMPLE}")
    rows = SAMPLE.read_text(encoding="utf-8").strip().splitlines()
    return f"{len(rows) - 1} candles in {SAMPLE.name}"


def _sample_candles():
    """The bundled 1h dataset, parsed the way the UI does it."""
    _ensure_package_importable()
    from crypto_trading_lab.market_data.importer import parse_csv

    summary = parse_csv(SAMPLE, interval_default="1h")
    if not summary.ok:
        raise RuntimeError(
            f"sample CSV rejected: {[str(e) for e in summary.errors][:2]}"
        )
    return summary


def check_importer() -> str:
    summary = _sample_candles()
    return (
        f"{summary.rows_valid} rows, symbol={summary.symbol}, "
        f"interval={summary.interval}"
    )


def check_backtest() -> str:
    from crypto_trading_lab.backtesting.engine import (
        MACrossoverStrategy,
        run_backtest,
    )

    result = run_backtest(
        _sample_candles().candles, MACrossoverStrategy(fast=5, slow=20)
    )
    return (
        f"return={result.return_fraction:.4%}, trades={len(result.trades)}, "
        f"final equity={result.final_equity}"
    )


def check_paper_trading() -> str:
    from crypto_trading_lab.backtesting.engine import MACrossoverStrategy
    from crypto_trading_lab.paper_session import (
        PaperSessionConfig,
        run_paper_session,
    )

    result = run_paper_session(
        _sample_candles().candles,
        MACrossoverStrategy(fast=5, slow=20),
        config=PaperSessionConfig(interval="1h"),
    )
    return (
        f"final equity={result.final_equity}, "
        f"closed trades={len(result.journal.closed_trades())}, "
        f"fees={result.total_fees}"
    )


def check_qt_window_offscreen() -> str:
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    _ensure_package_importable()
    from PyQt6.QtWidgets import QApplication

    from crypto_trading_lab.ui.main_window.window import MainWindow

    app = QApplication.instance() or QApplication([])
    window = MainWindow()
    window.close()
    del app
    return "MainWindow constructed and closed offscreen"


def check_ccxt() -> str:
    try:
        import ccxt
    except ImportError as error:
        raise Skip("ccxt is not installed (optional extra)") from error
    record(
        "ccxt installed",
        "PASS",
        f"ccxt {ccxt.__version__}, {len(ccxt.exchanges)} exchanges",
    )

    _ensure_package_importable()
    from crypto_trading_lab.exchanges.ccxt.adapter import CcxtExchangeAdapter

    client = ccxt.binance({"enableRateLimit": True})
    CcxtExchangeAdapter(client)
    return "the project adapter accepts a real ccxt client"


def check_optional_extras() -> str:
    found = []
    for module in ("keyring", "pypdf", "aiohttp", "websockets"):
        try:
            __import__(module)
        except ImportError:
            found.append(f"{module}: no")
        else:
            found.append(f"{module}: yes")
    return ", ".join(found)


# -- optional stages ---------------------------------------------------------


def _child_env() -> dict[str, str]:
    env = dict(os.environ)
    env.setdefault("PYTHONPATH", str(ROOT / "src"))
    return env


def run_test_suite() -> str:
    env = _child_env()
    env["QT_QPA_PLATFORM"] = "offscreen"
    print("\nRunning the full test suite (about a minute)...", flush=True)
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", str(ROOT / "tests"), "-q"],
        capture_output=True,
        text=True,
        env=env,
        cwd=ROOT,
        timeout=1800,
    )
    lines = [line for line in proc.stdout.strip().splitlines() if line.strip()]
    summary = lines[-1] if lines else "(no output)"
    stderr_tail = " | ".join(proc.stderr.strip().splitlines()[-8:])

    if proc.returncode == 0:
        record("full test suite", "PASS", summary)
    elif not any(word in summary.lower() for word in ("failed", "error")):
        # The suite said everything passed, yet the process exited non-zero.
        # On Windows that is usually a crash while the interpreter shuts down
        # (Qt objects outliving the application); pytest prints the "Windows
        # fatal exception" traceback to stderr, which used to be discarded.
        record(
            "full test suite",
            "FAIL",
            (
                f"the suite reported success but the process exited "
                f"{proc.returncode} — likely a crash during interpreter "
                f"shutdown; stderr tail: {stderr_tail[:500] or '(empty)'}"
            ),
        )
    else:
        record(
            "full test suite",
            "FAIL",
            f"exit {proc.returncode}: {summary} | stderr: {stderr_tail[:400]}",
        )
    return summary


def run_gui() -> str:
    """Open the real application window for a few seconds."""
    env = _child_env()
    env.pop("QT_QPA_PLATFORM", None)  # use the real platform plugin
    seconds = 8
    print(f"\nOpening the application for {seconds} seconds...", flush=True)
    try:
        proc = subprocess.run(
            [sys.executable, "-m", "crypto_trading_lab"],
            capture_output=True,
            text=True,
            env=env,
            cwd=ROOT,
            timeout=seconds,
        )
    except subprocess.TimeoutExpired:
        record("application window", "PASS", f"stayed open for {seconds}s, no crash")
        return "window opened"
    if proc.returncode != 0 or "Traceback" in proc.stderr:
        combined = (proc.stdout + proc.stderr).lower()
        headless_markers = (
            "could not connect to display",
            "platform plugin",
            "no display",
            "failed to load platform plugin",
        )
        if any(marker in combined for marker in headless_markers):
            record(
                "application window",
                "SKIP",
                "no display on this machine — run this stage on a desktop",
            )
            return "headless"
        record(
            "application window",
            "FAIL",
            f"exit {proc.returncode}: {proc.stderr.strip()[:300]}",
        )
        return "failed"
    record("application window", "SKIP", "the process exited immediately")
    return "exited early"


def run_network() -> str:
    try:
        import ccxt
    except ImportError:
        record("ccxt network probe", "SKIP", "ccxt not installed")
        return "skipped"
    try:
        ticker = ccxt.binance({"enableRateLimit": True}).fetch_ticker("BTC/USDT")
        record("ccxt network probe", "PASS", f"BTC/USDT last={ticker.get('last')}")
        return str(ticker.get("last"))
    except Exception as error:  # noqa: BLE001
        record(
            "ccxt network probe",
            "FAIL",
            f"{type(error).__name__}: {str(error)[:200]} (network or geo-block?)",
        )
        return "failed"


# -- report ------------------------------------------------------------------


def write_report(args: argparse.Namespace) -> None:
    lines = [
        "# Verification report",
        "",
        f"- Generated: `{datetime.now(timezone.utc).isoformat()}`",
        f"- Operating system: `{platform.platform()}`",
        f"- Architecture: `{platform.machine()}`",
        f"- Python: `{platform.python_version()}` (`{sys.executable}`)",
        f"- Repository: `{ROOT}`",
        f"- Flags: `tests={args.tests} gui={args.gui} network={args.network}`",
        "",
        "| Check | Result | Detail |",
        "|---|---|---|",
    ]
    for name, status, detail in RESULTS:
        safe = detail.replace("|", "\\|").replace("\n", " ")
        lines.append(f"| {name} | {status} | {safe} |")
    passed = sum(1 for _, s, _ in RESULTS if s == "PASS")
    failed = sum(1 for _, s, _ in RESULTS if s == "FAIL")
    skipped = sum(1 for _, s, _ in RESULTS if s == "SKIP")
    lines += [
        "",
        f"**{passed} passed, {failed} failed, {skipped} skipped.**",
        "",
        "Fill in `Experiments/CHECKLIST.md` as well and send both files back.",
        "",
    ]
    REPORT.write_text("\n".join(lines), encoding="utf-8")
    print(f"\n{passed} passed, {failed} failed, {skipped} skipped")
    print(f"Report written to {REPORT}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tests", action="store_true", help="run the full test suite")
    parser.add_argument("--gui", action="store_true", help="open the application window")
    parser.add_argument(
        "--network",
        action="store_true",
        help="probe ccxt against a public endpoint",
    )
    args = parser.parse_args()

    print("Crypto Trading Lab — functional verification")
    print("=" * 46)

    check("python version", check_python)
    check("operating system", check_platform)
    check("runtime imports", check_runtime_imports)
    check("numpy (via pyqtgraph)", check_numpy)
    check("package imports", check_package)
    check("sample dataset present", check_sample_data)
    check("CSV importer", check_importer)
    check("backtest engine", check_backtest)
    check("paper trading", check_paper_trading)
    check("Qt window (offscreen)", check_qt_window_offscreen)
    check("ccxt adapter", check_ccxt)
    check("optional extras", check_optional_extras)

    if args.network:
        run_network()
    if args.gui:
        run_gui()
    if args.tests:
        run_test_suite()

    write_report(args)
    failed = sum(1 for _, status, _ in RESULTS if status == "FAIL")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())

# Using a virtualenv

Crypto Trading Lab is built **Debian-first**: every runtime dependency is a
Debian system package, and that is the supported configuration (see
[`debian-dependencies.md`](debian-dependencies.md)). This document covers the
*second*, optional path: a Python **virtualenv** (`.venv`).

You need a virtualenv when:

- you want a **PyPI-only** package that has no Debian equivalent — today that
  is `ccxt` (the read-only CCXT adapter) and `pypdf` for PDF reports;
- you want a throwaway environment to try something without touching the
  system Python;
- you are on a machine where you cannot install Debian packages.

You do **not** need one to run the application or the test suite on Debian.

> **Dependency stop rule (`AGENTS.md` rule 2).** The maintainer — not the AI
> agent — creates the virtualenv and runs every `apt`/`pip` command below.
> An agent may use an existing `.venv` afterwards, never create or install
> into one.

`.venv/` is already in [`.gitignore`](../../../.gitignore); never commit it.

---

## 1. The packages, Debian name vs PyPI name

Runtime — required to run the application:

| What it is for | Debian package | PyPI name (inside the venv) |
|---|---|---|
| Qt 6 widgets (the GUI) | `python3-pyqt6` | `PyQt6` |
| Charts | `python3-pyqtgraph` | `pyqtgraph` (pulls `numpy`) |
| Database (SQLite) | `python3-sqlalchemy` | `SQLAlchemy` |
| XDG config/data/log paths | `python3-platformdirs` | `platformdirs` |

Development and tests:

| What it is for | Debian package | PyPI name |
|---|---|---|
| Test runner | `python3-pytest` | `pytest` |
| Qt test helpers | `python3-pytest-qt` | `pytest-qt` |
| Property-based tests | `python3-hypothesis` | `hypothesis` |
| Runtime type checks in tests | `python3-typeguard` | `typeguard` |

Optional extras:

| What it is for | Debian package | PyPI name |
|---|---|---|
| PDF report export (chapter 41) | `python3-pypdf` | `pypdf` |
| Read-only CCXT adapter (multi-exchange) | **none — PyPI only** | `ccxt` |
| Live WebSocket feed (chapter 27) | **none — PyPI only** | `aiohttp`, `websockets` |
| Translation tooling | `qt6-l10n-tools` | (Qt SDK) |

`numpy` is not installed directly: it arrives with `pyqtgraph` (or with the
Debian `python3-pyqtgraph` package).

The same lists live in `pyproject.toml` as the `venv`, `dev`, `pdf`, `ccxt`,
`aiohttp` and `websockets` optional-dependency groups, so a virtualenv can be
filled with one command (path B below).

---

## 2. Path A — venv on top of the Debian packages (recommended)

The Qt stack is large. Reusing the Debian build keeps the venv small and
matches the supported configuration; the venv then carries only what Debian
does not provide.

```bash
# Once, with sudo: the venv module and the Qt stack to reuse.
sudo apt update
sudo apt install python3-venv python3-pyqt6 python3-pyqtgraph \
                 python3-sqlalchemy python3-platformdirs

# From the repository root:
cd /path/to/crypto-trading-lab
python3 -m venv --system-site-packages .venv
source .venv/bin/activate
python -m pip install --upgrade pip

# Only the PyPI-only extras:
python -m pip install ccxt          # add pypdf for PDF reports
```

`--system-site-packages` is what makes the Debian Qt, pyqtgraph, SQLAlchemy
and platformdirs visible inside the venv.

Verify:

```bash
python -c "import PyQt6, pyqtgraph, sqlalchemy, platformdirs; print('deps OK')"
QT_QPA_PLATFORM=offscreen python -m pytest tests/ -q   # → 698 passed, 2 skipped
PYTHONPATH=src python -m crypto_trading_lab            # launch the app
```

---

## 3. Path B — fully isolated venv (everything from PyPI)

Use this when you cannot install Debian packages, or when you want the venv
to pin its own Qt.

```bash
# The venv module itself is still a Debian package.
sudo apt install python3-venv

cd /path/to/crypto-trading-lab
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip

# Installs the project in editable mode plus every group declared in
# pyproject.toml: PyQt6, pyqtgraph, SQLAlchemy, platformdirs, the test
# tools, ccxt and pypdf.
python -m pip install -e ".[venv,dev,ccxt,pdf]"
```

The editable install adds the `crypto-trading-lab` command and makes
`crypto_trading_lab` importable without `PYTHONPATH`:

```bash
QT_QPA_PLATFORM=offscreen python -m pytest tests/ -q
python -m crypto_trading_lab
# or, after the editable install:
crypto-trading-lab --version
```

---

## 4. Leaving the venv

```bash
deactivate            # back to the system Python
rm -rf .venv          # delete the environment entirely
```

---

## 5. Troubleshooting

| Symptom | Cause and fix |
|---|---|
| `No module named venv` / `ensurepip is not available` | Install `python3-venv` (`sudo apt install python3-venv`). |
| `error: externally-managed-environment` | You ran `pip` *outside* the venv. Activate it first. Do **not** pass `--break-system-packages`: that defeats the Debian-first policy. |
| `Not uninstalling X at /usr/lib/python3/dist-packages, outside environment .venv` | Normal with `--system-site-packages`. pip sees the Debian copy, correctly refuses to touch anything outside the venv, and installs its own copy inside `.venv` instead. Nothing is broken. |
| `ERROR: pip's dependency resolver ... weasyprint ... requires html5lib` | A **system** package (Debian's `weasyprint`) whose dependency pip cannot see across the `--system-site-packages` boundary. This project does not use weasyprint, and the install still succeeded. pip prints `ERROR:` here but exits 0 — check for the final `Successfully installed …` line. `python -m pip check` reports venv-local conflicts only. |
| `Could not load the Qt platform plugin "xcb"` | Headless machine. Use `QT_QPA_PLATFORM=offscreen`, and install `libgl1 libegl1 libxkbcommon-x11-0 libdbus-1-3` (the CI does exactly this). |
| `pip install PyQt6` inside a `--system-site-packages` venv | The PyPI copy shadows the Debian one. Pick one route (A or B) and stay there. |
| Tests pass on the system but not in the venv | Check `python -c "import sys; print(sys.prefix)"` points at `.venv`, and that you did not mix routes. |

---

## 6. Evaluating whether `ccxt` is worth adopting

`ccxt` is a large, multi-exchange library. The project already downloads
Binance Spot history with the standard library only
(`market_data/historical.py`), so `ccxt` has to earn its place.

**Reasons it could:** a second exchange (Coinbase, chapter 26.3), one unified
API across exchanges, and built-in rate limiting / pagination — replacing
hand-written adapters.

**Reasons it might not:** it is a large PyPI dependency, it is asynchronous
under the hood, and if it only re-wraps Binance it adds nothing we lack.

The repository vendors the ccxt source as a study reference under
[`external/ccxt`](../../../external/ccxt) (an optional submodule, not an
install). To evaluate it against the project:

```bash
source .venv/bin/activate
python tools/evaluate_ccxt.py              # offline inspection
python tools/evaluate_ccxt.py --network    # also hits a public endpoint
```

The script is read-only. Offline it reports the installed version, how many
exchanges it covers, whether Binance and Coinbase expose the methods our
adapter calls (`fetch_markets`, `fetch_ticker`, `fetch_ohlcv`,
`fetch_balance`, `precisionMode`), and whether the project's own
`CcxtExchangeAdapter` accepts a real client.

**Decision rule.** Adopt `ccxt` if the offline checks pass and it buys us a
second exchange (Coinbase) or removes an adapter we maintain by hand. Keep
the standard-library path if it only re-wraps Binance. A new dependency is a
chapter-4 decision and always lands with the maintainer running the install.

---

## 7. What we measured (2026-09-27)

Environment: Debian 13, Python 3.13.5, `python3 -m venv
--system-site-packages .venv`, pip upgraded to 26.2.1, then
`python -m pip install ccxt`.

| Check | Result |
|---|---|
| `import ccxt` | **4.5.84** |
| Exchanges covered | **104** |
| Binance surface (`fetch_markets`/`fetch_ticker`/`fetch_ohlcv`/`fetch_balance`/`precisionMode`) | complete |
| Coinbase surface | complete |
| `CcxtExchangeAdapter` accepts a real client | yes |
| `--network` probe | `BTC/USDT last=84411.09` |
| Adapter `fetch_candles()` over Binance | normalised `Decimal` + UTC candles |
| Adapter `fetch_candles()` over **Coinbase** | normalised `Decimal` + UTC candles |
| Full test suite inside the venv | **698 passed, 2 skipped** (same as the system Python) |

The decisive result is the Coinbase row: the standard-library downloader
reaches Binance only, so `ccxt` is what makes chapter 26.3 possible at all.
`fetch_candles()` returns the same normalised shape from both exchanges, so
no domain code changes are needed to use it.

**One finding worth keeping.** On Coinbase the liquid pair is **BTC/USD**
(volume 52.75 in the sample) while **BTC/USDT** is thin (0.53); on Binance it
is the opposite. Choose the trading pair deliberately per exchange rather
than assuming `BTC/USDT` everywhere.

**Verdict:** `ccxt` is worth adopting for chapter 26.3. The Debian-first
default and the standard-library Binance downloader stay as they are; the
dependency belongs to the optional CCXT path, which is still not exposed in
the UI.

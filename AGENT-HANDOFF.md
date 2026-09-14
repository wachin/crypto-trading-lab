# AGENT-HANDOFF.md — Repository Migration & Continuation Guide

**Purpose:** complete, self-contained instructions for moving this
project to a fresh repository and continuing development 

A new AI Agent should read this file **before** doing anything else.

---

## 1. Project state at handoff (2026-09-13)

- **Tests:** 229 passed, 2 skipped (`python3 -m pytest tests/ -q`,
  run with `QT_QPA_PLATFORM=offscreen` on headless machines)
- **Source:** 39 Python files under `src/crypto_trading_lab/`
- **Tests:** 37 Python files under `tests/`
- **Specification:** `ROADMAP.md` — 72 chapters in checklist format,
  228 items marked `[x]`
- **Phases completed:** Phase 0 (research), Phase 1 (foundation),
  Phase 2 (data & charts), Phase 3 in progress (backtesting engine done)
- **Last commit:** `3fbc029 Implementado — Motor de backtesting (cap. 37)`

### Implemented modules (all with passing tests)

| Module | Path | Roadmap chapter |
|---|---|---|
| Domain models (Decimal, UTC) | `src/crypto_trading_lab/domain/models.py` | 7 |
| Exchange adapters + Mock + CCXT | `src/crypto_trading_lab/exchanges/` | 26-27, 30 |
| Credential store (keyring/memory) | `src/crypto_trading_lab/security/credentials.py` | 9 |
| Logging + redaction + audit | `src/crypto_trading_lab/infrastructure/logging_setup.py` | 10 |
| SQLite persistence + candle repo | `src/crypto_trading_lab/persistence/` | 8 |
| XDG configuration | `src/crypto_trading_lab/configuration/xdg.py` | 71.1 |
| i18n (en default, es) | `src/crypto_trading_lab/i18n/` | 20 |
| Main window + Learning Center | `src/crypto_trading_lab/ui/` | 71.1, 23 |
| Charts (PyQtGraph backend) | `src/crypto_trading_lab/ui/charts/` | 32, 4.2 |
| CSV import + validation | `src/crypto_trading_lab/market_data/importer.py` | 28 |
| Indicators (SMA/EMA/RSI/BB/ATR/ROC) | `src/crypto_trading_lab/indicators/library.py` | 31 |
| Backtesting engine | `src/crypto_trading_lab/backtesting/engine.py` | 37, 33 |

### Development environment

- Python 3.13.5, Debian 13 (trixie), PyQt6 (system), pyqtgraph 0.13.7
  (system, installed via `python3-pyqtgraph`), SQLAlchemy 2.0.40,
  platformdirs 4.3.7, pytest 8.3.5, Qt tools `pylupdate6`/`lrelease`/
  `linguist` — **all from Debian packages, no venv needed**



**Expected result:** 229 passed, 2 skipped. If anything else fails,
the migration lost a file — compare against this old repository.


## About Book Marcos López de Prado, *Advances in Financial Machine Learning*,
 Wiley, 2018.

Credit appears (and must be preserved) in:

- `docs/en/developers/reference-projects.md` — header and throughout
- `ROADMAP.md` — the "Vision and mission" section cites the book as
  the project's methodological reference
- `README.md` — "The method follows *Advances in Financial Machine
  Learning* (Marcos López de Prado)."

**Rule for the new repository:** the book is cited by bibliographic
reference only. Techniques from the book are implemented from the public
MIT-licensed exercise repository (`external/adv-financial-ml-marcos-
exercises`, already a submodule) and from the mathematical
definitions recorded in `reference-projects.md`, always with
attribution.

## 2. What to do if the Agent needs AFML material later

Part VIII of the ROADMAP (chapters 47-50) draws on the book. The new
repository's Agent must:

1. Use `docs/en/developers/reference-projects.md` — Part A maps every
   relevant technique to roadmap sections with adoption guidance
2. Use the MIT-licensed exercises submodule for reference code
3. Implement from the mathematical definitions, cite the book in
   docstrings/docs: *"Technique from López de Prado (2018),
   Advances in Financial Machine Learning, ch. N"*
   

## 3. Recommended: create AGENTS.md in the new repo

The new repository should carry an `AGENTS.md` at its root so any
AI Agent (opencode, Codex, etc.) automatically loads the ground
rules. Suggested content is provided in §7. Do this in the FIRST
commit of the new repository.

## 4. Working rules that must survive the migration

These rules are canonical. The new Agent inherits them verbatim:

1. **Read `ROADMAP.md` first**; treat it as the specification. Never
   silently simplify or omit its requirements.
2. **MANDATORY STOP RULE for dependencies** (chapter 4.0 and GENESIS.md
   rule 6): if a new dependency is needed, STOP, notify the developer
   with package name, source (Debian/PyPI), reason, and exact command.
   Debian package → developer runs `apt install`. PyPI-only → the
   developer creates a venv (`.venv`), the Agent never installs or
   creates environments itself. No package has required a venv so far.
3. **No real credentials**, no `eval()`/`exec()`, real trading stays
   disabled, strategies never bypass the risk manager.
4. **Vision and mission** (see ROADMAP.md intro): survive → validate
   → earn. Never risk money needed to live. Honest metrics only;
   never promise profits. The developer's economic situation makes
   capital protection a survival requirement, not ideology.
5. **Working method** (chapter 70): small changes, tests always run,
   results shown honestly, documentation evolves with code, English
   first (Spanish via Qt Linguist).
6. **Book rule** (§3-§4 of this file): cite López de Prado by
   reference; never redistribute his text.
7. **Windows/portability**: code is Qt/stdlib/Debian-packages pure —
   keep it platform-neutral by construction, but Debian is the only
   officially supported target for now.

## 5. Immediate next steps (where development left off)

Per `ROADMAP.md` and the last iteration report:

1. **Performance metrics** (chapter 40): win rate, profit factor,
   expectancy, max drawdown, volatility, Sharpe/Sortino — computed
   from `BacktestResult`, each with beginner documentation.
2. **Enable the Backtesting Lab button** in the main window (it is
   currently disabled by design), running backtests over imported
   candles, showing results with the mandatory beginner-oriented
   explanation (chapter 37.9).
3. Then: reports (41), paper trading (57), risk manager (58).

## 6. Quick-start for the new Agent

```bash
# Verify environment:
python3 --version            # ≥ 3.11 expected (3.13 on record)
python3 -c "import pyqtgraph, sqlalchemy, platformdirs; print('deps OK')"
QT_QPA_PLATFORM=offscreen python3 -m pytest tests/ -q   # 229 passed expected

# Read in this order:
# 1. AGENT-HANDOFF.md (this file)
# 2. GENESIS.md
# 3. ROADMAP.md (chapters 70, 71, then the next chapter to implement)
# 4. docs/en/developers/reference-projects.md (when AFML is needed)
```

---

*Handoff prepared 2026-09-13. All 229 tests passing at time of writing.*

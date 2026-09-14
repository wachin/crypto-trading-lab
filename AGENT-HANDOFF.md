# AGENT-HANDOFF.md — Continuation Guide

**Purpose:** everything a new AI Agent needs to continue this project from
its current state. The migration notes that follow (§3–§6) are preserved
for a fresh start.

A new AI Agent must read this file **before** doing anything else, then
`AGENTS.md`, then `ROADMAP.md`.

---

## 1. Project state (last updated 2026-09-13)

- **Repository:** `https://github.com/wachin/crypto-trading-lab`
  (branch `main`, pushed and in sync)
- **State verified at commit:** `1906732 docs: specify the AFML research-tier
  techniques` (an ancestor of the commit that carries this file)
- **Tests:** 229 passed, 2 skipped —
  `QT_QPA_PLATFORM=offscreen python3 -m pytest tests/ -q`
- **Source:** 39 Python files under `src/crypto_trading_lab/`
- **Tests:** 37 Python files under `tests/`
- **Documentation:** `docs/en/beginners/` (3 files) and
  `docs/en/developers/` (`reference-projects.md`, `afml-techniques.md`,
  `adr/0001-exchange-adapter-spike.md`)
- **Specification:** `ROADMAP.md` — 72 chapters; 241 requirements marked
  `[x]` after the 2026-09-13 reconciliation
- **Git submodules:** 8 reference projects under `external/`; a fresh clone
  needs `git submodule update --init --recursive`
- **Current phase:** Phase 3 (backtesting) in progress. The engine and the
  initial strategies are done; the next task is **Chapter 40 (performance
  metrics)**, followed by the Backtesting Lab UI (§37.9). See §5.

### Honest status of the earlier phases

Phase 0 (research) and Phase 2 (data & charts) are functionally done. Phase 1
(foundation) is done except for the items below — do not repeat "all phases
completed"; Chapter 69 and Chapter 71 track the real state.

Still missing from the foundation (required by Chapter 19.1 / Chapter 71 and
not yet written):

- `docs/en/developers/debian-dependencies.md`
- `docs/en/developers/architecture-proposal.md`
- `docs/en/developers/threat-model.md`
- the ADR set `ADR-0001`–`ADR-0007` (only an exchange-adapter spike ADR
  exists today, `docs/en/developers/adr/0001-exchange-adapter-spike.md`)
- the initial Debian package (Chapter 16)

These are ordinary pending work items, not blockers for Chapter 40.

### Implemented modules (all with passing tests)

| Module | Path | Roadmap chapter |
|---|---|---|
| Domain models (Decimal, UTC) | `src/crypto_trading_lab/domain/models.py` | 7 |
| Exchange adapters + Mock + CCXT | `src/crypto_trading_lab/exchanges/` | 26-27, 30 (partial) |
| Credential store (keyring/memory) | `src/crypto_trading_lab/security/credentials.py` | 9 |
| Logging + redaction + audit | `src/crypto_trading_lab/infrastructure/logging_setup.py` | 10 |
| SQLite persistence + candle repo | `src/crypto_trading_lab/persistence/` | 8 |
| XDG configuration | `src/crypto_trading_lab/configuration/xdg.py` | 71.1 |
| i18n (en default, es) | `src/crypto_trading_lab/i18n/` | 20 |
| Main window + Learning Center | `src/crypto_trading_lab/ui/` | 71.1, 23 |
| Charts (PyQtGraph backend) | `src/crypto_trading_lab/ui/charts/` | 32, 4.2 |
| CSV import + validation | `src/crypto_trading_lab/market_data/importer.py` | 28 |
| Indicators (SMA/EMA/RSI/BB/ATR/ROC) | `src/crypto_trading_lab/indicators/library.py` | 31 |
| Backtesting engine (fees, slippage, spread, next-open) | `src/crypto_trading_lab/backtesting/engine.py` | 37, 33 |
| AFML technique specifications | `docs/en/developers/afml-techniques.md` | 49, 47.4, 48 |

### Development environment

- Python 3.13.5, Debian 13 (trixie), PyQt6 (system), pyqtgraph 0.13.7
  (system, installed via `python3-pyqtgraph`), SQLAlchemy 2.0.40,
  platformdirs 4.3.7, pytest 8.3.5, Qt tools `pylupdate6`/`lrelease`/
  `linguist` — **all from Debian packages, no venv needed**

### One reference you will not have

The previous developer held the book's *exhibit compilation* as a local PDF.
It is git-ignored, was deliberately deleted and is **not part of the
repository**. This is not a blocker: every technique that depended on it is
already specified in `docs/en/developers/afml-techniques.md`, with the
exhibit numbers, the equations and the primary-paper citations in its §5.
Work from that specification; do not try to obtain the PDF.

## About the book — Marcos López de Prado, *Advances in Financial Machine Learning* (Wiley, 2018)

Credit appears (and must be preserved) in:

- `docs/en/developers/reference-projects.md` — header and throughout
- `ROADMAP.md` — the "Vision and mission" section cites the book as
  the project's methodological reference
- `README.md` — "The method follows *Advances in Financial Machine
  Learning* (Marcos López de Prado)."

**Rule for the new repository:** the book is cited by bibliographic
reference only. Techniques from the book are implemented from the public
MIT-licensed exercise repository (`external/adv-financial-ml-marcos-
exercises`, already a submodule), from the book's own exhibit
compilation (a local reference copy, inventoried in
`reference-projects.md` A.9), and from the mathematical definitions
recorded in `docs/en/developers/afml-techniques.md`, always with
attribution. Never copy book text or code, and never commit the book —
printed text or exhibit compilation.

## 2. What to do if the Agent needs AFML material later

Part VIII of the ROADMAP (chapters 47-50) draws on the book. The new
repository's Agent must:

1. Read `docs/en/developers/afml-techniques.md` first — it holds the
   project's own specification of every AFML technique: purpose,
   mandatory parameters, algorithm outline, required tests, exhibit
   pointers and open questions.
2. Use `docs/en/developers/reference-projects.md` — Part A maps every
   relevant technique to roadmap sections with adoption guidance; A.9
   inventories the book's exhibit compilation (a local reference copy).
3. Use the MIT-licensed exercises submodule for reference code. For the
   snippets and equations the submodule lacks (sample weights, fractional
   differentiation, bet sizing, structural breaks, entropy, the PSR/DSR
   formulas, CPCV), use the specification in `afml-techniques.md` — it
   carries the exhibit numbers and equations, and the compilation itself
   is not available to you (see §1).
4. Implement from the recorded definitions, cite the book in
   docstrings/docs: *"Technique from López de Prado (2018),
   Advances in Financial Machine Learning, ch. N"*
5. Resolve every *open question* in `afml-techniques.md` before coding
   the affected technique. The two that were open (PBO/CSCV, ch. 49.6;
   the Deflated Sharpe Ratio, ch. 49.5) are now specified from their
   public primary papers, as the roadmap allows ("additional research",
   Ch. 49); only the DSR paper's Appendix 3 (effective number of
   independent trials) remains, with a conservative fallback. Never
   guess.
6. Never copy book text or code into the repository and never commit the
   book (printed text or exhibit compilation).

## 3. AGENTS.md in the new repo

The new repository carries an `AGENTS.md` at its root so any
AI Agent (opencode, Codex, etc.) automatically loads the ground
rules. It was created in the first commit of this repository; keep it
in sync with §4 of this file (the working rules) and with the AFML book
rule (§1).

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
6. **Book rule** (§1 and §2 of this file): cite López de Prado by
   reference; never redistribute his text.
7. **Windows/portability**: code is Qt/stdlib/Debian-packages pure —
   keep it platform-neutral by construction, but Debian is the only
   officially supported target for now.

## 5. Immediate next steps (where development left off)

Per `ROADMAP.md` and the last iteration report:

1. **Performance metrics (Chapter 40)** — the canonical next task. Chapter 40
   owns the metric catalogue: return and profit metrics (40.1), trade
   statistics (40.2), risk metrics (40.3), trading activity (40.4), benchmark
   comparison (40.5), statistical validity (40.6), configuration (40.7) and
   documentation (40.8). Compute them from `BacktestResult`
   (`src/crypto_trading_lab/backtesting/engine.py`), each with its own tests
   (Chapter 14) and a beginner explanation (40.7 and Chapter 19.2).
2. **Backtesting Lab UI** — enable the Backtesting Lab button in the main
   window (it is currently disabled by design), run backtests over imported
   candles, and show the results with the mandatory beginner-oriented
   explanation (Chapter 37.9).
3. Then: reports (41), benchmarking (42), robustness (43-46), paper trading
   (57), risk manager (58).

Do not start a task before reading the chapter that owns it, and do not tick
a requirement until it is implemented **and tested**.

## 6. Quick-start for the new Agent

```bash
# 1. Clone with the reference submodules (or, if already cloned):
git submodule update --init --recursive

# 2. Verify the environment:
python3 --version            # ≥ 3.11 expected (3.13 on record)
python3 -c "import pyqtgraph, sqlalchemy, platformdirs; print('deps OK')"
QT_QPA_PLATFORM=offscreen python3 -m pytest tests/ -q   # 229 passed expected

# 3. Read in this order:
#    1. AGENT-HANDOFF.md (this file) — state and next steps
#    2. AGENTS.md — the non-negotiable rules
#    3. ROADMAP.md — the specification (start with Chapter 40, the next task)
#    4. docs/en/developers/afml-techniques.md (when AFML is needed)
#    5. docs/en/developers/reference-projects.md (reference-project studies)
```

If the test count differs, stop and report it before changing anything.

---

*Handoff updated 2026-09-13. All 229 tests passing at time of writing.*

# AGENT-HANDOFF.md — Continuation Guide

**Purpose:** everything a new AI Agent needs to continue this project from
its current state: what exists, what is verified, and where development
left off. The historical migration notes are kept in §3–§4 because they
still explain *why* the working rules exist.

A new AI Agent must read this file **before** doing anything else, then
`AGENTS.md`, then `ROADMAP.md`.

---

## 1. Project state (last updated 2026-10-01)

- **Repository:** `https://github.com/wachin/crypto-trading-lab`
  (branch `main`)
- **State verified at commit:** the commit that carries this file.
- **Tests:** 702 passed, 2 skipped, **exit code 0** —
  `QT_QPA_PLATFORM=offscreen python3 -m pytest tests/ -q`
  (The exit code matters: the suite used to segfault while the interpreter
  shut down, so it printed "passed" and still failed the build. See §5.)
- **Verified platforms:** Debian 13 (system packages, Python 3.13.5) and
  **Windows 10** (pip/PyPI, Python 3.14.7, 2026-10-01 — clean install, the
  window opens, identical numbers, `ccxt` reaches the network). **macOS is
  not verified.**
- **Source:** 115 Python files under `src/crypto_trading_lab/`
- **Tests:** 64 test modules under `tests/`
- **Documentation:** `docs/en/beginners/` and
  `docs/en/developers/` (virtualenv guide in `venv-setup.md`, audit in
  `unwired-modules-audit.md`)
- **Verification kit:** `Experiments/` runs twelve checks on a fresh machine
  and writes a report; `setup_windows.bat` is one-click.
- **Specification:** `ROADMAP.md` — 80 chapters in 16 parts
- **Git submodules:** 8 *optional* reference projects under `external/`;
  the application builds and tests without them. Clone them with
  `git submodule update --init --recursive` only when the task is about
  those references.
- **Current phase:** the scientific engine is mature. The 2026-09/10 review
  fixed the documentation-vs-code drift and cleared 15 of the 16 unwired
  modules found in the audit; the only one left is `strategy_registry`.
  The frontier after that is the live-data path (Binance WebSocket,
  chapters 26.2/27), testnet order placement (chapter 68) and packaging
  (chapters 15/16/18). **Real trading remains disabled by default.**

### What changed on 2026-09-19 (direction correction + Fase A/B)

The previous session had drifted: commits announced features that were
only unused imports or canned text. Those were fixed and backed by real,
tested code:

- `MainWindow._open_notebook` used to crash (`ExperimentManager` has no
  `list_experiments`); the manager now really has it, with persistence,
  statuses, tags, search and comparison.
- The research assistant no longer ignores the question and returns
  canned text: it is an honest, offline methodology assistant with an
  injectable model backend and persisted conversations.
- `run_optimization` passed arguments in the wrong order and swallowed
  the error, reporting “0 combinations tested”; fixed and tested.
- `RobustnessReport.summary()` raised `ValueError` (invalid f-string);
  fixed with a regression test.
- `strategy_builder.py` imported a non-existent `IndicatorFactory`, so
  the module could not be imported; fixed.
- New: historical-data download + validation + versioned datasets
  (`market_data/historical.py`, `persistence/datasets.py`), a research
  workflow service (`research.py`), the Research Wizard, validity
  dashboard, Research Notebook UI and strategy-builder UI, all i18n.
- Round 1 also found and fixed: the Learning Center crashed on lesson
  click (`Qt.AlignHCenter`) and on the quiz (`QHBoxBoxLayout`, always
  returned False, progress never loaded); and the strategy-builder
  module was unimportable while its launcher opened the dialog twice.
- New in round 1: a 48-lesson curriculum in three levels
  (`education/curriculum.py`), a rewritten Learning Center with a working
  quiz and persisted progress, executable rule strategies
  (`rule_strategy.py`) wired into the Backtesting Lab, and paper trading
  with a mandatory risk gate and a trading journal (`paper_session.py`,
  `ui/paper/paper_trading.py`).

### Contributor infrastructure

The repository is now prepared for outside contributors who work with AI
agents:

- `CONTRIBUTING.md` — setup, workflow, definition of done, the
  non-negotiable rules, a ready-to-paste agent prompt and a list of good
  first contributions.
- `.github/workflows/tests.yml` — runs the offline suite on Debian
  packages (no pip, no venv) for every push and pull request.
- `.github/PULL_REQUEST_TEMPLATE.md` and `.github/ISSUE_TEMPLATE/` —
  they require the real test output and the owning ROADMAP chapter.
- `Makefile` — `make test`, `make run`, `make banner`, `make translations`.
- `tools/make_banner_gif.py` — regenerates the README contributor banner
  (deterministic; needs Pillow/NumPy only to regenerate the asset).
- `assets/contributing-agents.gif` — the animated banner (76 KB).

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
| Performance metrics (returns, trades, risk, activity, benchmark, validity) | `src/crypto_trading_lab/backtesting/metrics.py` | 40 |
| Risk manager (position limits, loss limits, operational limits) | `src/crypto_trading_lab/risk_manager.py` | 58 |
| Emergency kill switch | `src/crypto_trading_lab/kill_switch.py` | 59 |
| Safety gates (pre-trade protection layer) | `src/crypto_trading_lab/safety_gates.py` | 67 |
| Strategy failure detection (early warning system) | `src/crypto_trading_lab/monitoring/failure_detection.py` | 64 |
| Risk of ruin and position sizing | `src/crypto_trading_lab/backtesting/robustness.py` | 60 |
| Strategy qualification (multi-criterion evaluation) | `src/crypto_trading_lab/qualification.py` | 66 |
| Robustness report (Monte Carlo, perturbation, cost sweep, OOS degradation) | `src/crypto_trading_lab/backtesting/robustness.py` | 44 |
| Statistical edge analysis (distributions, autocorrelation, bootstrap, PSR) | `src/crypto_trading_lab/backtesting/statistical_analysis.py` | 43 |
| Ensemble methods (voting, averaging, weighted combination) | `src/crypto_trading_lab/ensembles.py` | 50 |
| Portfolio construction (correlation, portfolio returns, portfolio metrics) | `src/crypto_trading_lab/portfolio.py` | 51 |
| AFML techniques (triple-barrier labeling, purged CV, sample uniqueness) | `src/crypto_trading_lab/machine_learning/` | 49 |
| Regime analysis (trending/ranging, volatility, concentration warning) | `src/crypto_trading_lab/market_data/regimes.py` | 46 |
| Feature engineering (returns, volatility, momentum, RSI, EMA, z-score) | `src/crypto_trading_lab/market_data/features.py` | 47 |
| Experiment manager (research tracking, reproducibility) | `src/crypto_trading_lab/machine_learning/experiment_manager.py` | 52 |
| Live vs backtest drift analysis | `src/crypto_trading_lab/monitoring/` | 63 |
| Real trading support (activation flow, safety protections) | `src/crypto_trading_lab/trading.py` | 68 |
| Robustness (seeded Monte Carlo, perturbation, cost sweeps) | `src/crypto_trading_lab/backtesting/robustness.py` | 44 (partial) |
| Chronological data splitting (train/validation/test) | `src/crypto_trading_lab/market_data/splitting.py` | 38 |
| Walk-forward analysis (rolling windows, per-window selection) | `src/crypto_trading_lab/backtesting/walk_forward.py` | 45 |
| AFML technique specifications | `docs/en/developers/afml-techniques.md` | 49, 47.4, 48 |
| Historical data download + validation + dataset identity | `src/crypto_trading_lab/market_data/historical.py` | 26.2, 28, 29, 53 |
| Dataset repository (versioned, checksummed) | `src/crypto_trading_lab/persistence/datasets.py` | 29, 53 |
| Download-and-store service | `src/crypto_trading_lab/market_data/dataset_service.py` | 28, 29 |
| End-to-end research workflow + validity checklist | `src/crypto_trading_lab/research.py` | 37-45, 53, 66 |
| Historical-data screen | `src/crypto_trading_lab/ui/data/historical_data.py` | 26.2, 28, 29 |
| Research Wizard | `src/crypto_trading_lab/ui/research/wizard.py` | 37-45, 66 |
| Research-validity dashboard | `src/crypto_trading_lab/ui/research/validity.py` | 43, 72 |
| Research Notebook / experiment manager UI | `src/crypto_trading_lab/ui/research/notebook.py` | 52-54 |
| Offline research assistant (injectable model backend) | `src/crypto_trading_lab/ui/research/assistant.py` | 55 |

### Domain-model naming and the chapter 7/26/30 reconciliation

- `Symbol` is the validated trading-pair type (`BASE/QUOTE`): where chapter 7
  lists "TradingPair", the implementation is `Symbol`.
- Domain models implemented: `Market`, `Ticker`, `Candle`, `Balance`,
  `OrderRequest`, `Fill`, `OrderResult` (`domain/models.py`), plus
  `BacktestConfig`, `CostModel`, `TradeRecord`, `BacktestResult`
  (`backtesting/engine.py`). All money, price, quantity, fee and balance
  fields are `Decimal`; timestamps are UTC and naive ones are rejected.
- Domain models still to add (chapter 7): Exchange, Asset, Trade, OrderBook,
  OrderBookLevel, Position, Portfolio, Order, Fee, StrategySignal,
  RiskDecision, Backtest, PaperAccount, PerformanceMetrics, DatasetVersion,
  Experiment, StrategyVersion, QualificationReport.
- Chapter 30 is only partly done: `Market` carries `min_quantity`,
  `min_notional`, `price_precision`, `quantity_precision` and maker/taker fees,
  and `ExchangeAdapter.validate_order_request` performs the shared pre-flight
  checks. Still pending: true tick-size/step-size rules, rate limits, time
  synchronisation, and the remaining pre-trade steps (risk limits, data
  freshness, duplicate prevention, idempotency identifiers, beginner-readable
  rejections).
- Chapters 26.2 and 26.3 are partial: only the Binance endpoint configuration
  exists (centralised, spot-only, tested). There is no WebSocket layer, no
  reconnection logic and no Coinbase support.

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

## 3. AGENTS.md at the repository root

The repository carries an `AGENTS.md` at its root so any
AI Agent (opencode, Codex, etc.) automatically loads the ground
rules. Keep it in sync with §4 of this file (the working rules) and with
the AFML book rule (§1).

## 4. Working rules (canonical)

These rules are canonical. Every Agent working here inherits them:

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

## 5. Where the project stands, and how to pick up work

### 5.1 The 2026-09/10 review (what changed, and why)

A repository review fixed one systematic problem: the documentation claimed
features the code did not ship. Concretely:

- **15 unwired modules were audited one by one.** The decisions and their
  evidence are in `docs/en/developers/unwired-modules-audit.md`: nine were
  deleted (dead, duplicated or non-functional), five were merged or wired,
  and **one remains — `strategy_registry.py`**.
- **The documented test baseline was wrong in twelve places** and had
  drifted between 229 and 698. It is `702 passed, 2 skipped`, and the suite
  **exits 0**.
- **The suite used to segfault while the interpreter shut down** (chapter 68
  imported Qt and re-initialised a `QObject`), so `make test` and CI failed
  while printing "passed". Fixed, with a regression test that forbids Qt in
  that module.
- **Chapter 56 execution realism is wired into paper trading**; chapter 63
  drift is shown in the Paper Trading screen; chapter 53 reproducibility now
  records the environment and the code hash; chapter 72 ethics guards report
  generation and the PDF export works; chapter 60 gained Kelly position
  sizing.
- **The CI was red for a real reason**: `ubuntu-24.04` ships SQLAlchemy 1.4
  and the code needs 2.0. `tests.yml` now installs with pip, and the manual
  `cross-platform` workflow runs Ubuntu, macOS and Windows.
- **Windows 10 is verified** (`Experiments/`); macOS is not.

### 5.2 The backlog, in the order that makes sense

1. **`strategy_registry.py`** — the last unwired module (audit item 16):
   wire its `list_strategies`/`search` into the Backtesting Lab combo, which
   today hard-codes its strategies, or delete it.
2. **Chapter 56.5** — feed the execution model into the **backtest engine**
   and robustness, not only paper trading.
3. **Chapter 63.2** — drift over time, likely causes, and marking a strategy
   as degraded.
4. **Chapters 26.2/27** — a continuous Binance WebSocket feed (paper trading
   still replays a dataset). `ccxt` is verified to reach **Binance and
   Coinbase**; chapter 26.3's native Coinbase adapter was deleted as dead.
5. **Chapters 15/16/18** — packaging. The Debian packaging is stale:
   `debian/rules` calls `setup.py install` and `debian/control` does not list
   pyqtgraph or platformdirs.
6. **Chapter 48** — machine learning is deliberately unbuilt; it needs a
   dependency decision first (chapter 4) before any code.
7. **Translations** — the Spanish `.ts` still has untranslated strings that
   fall back to English.

Anything in `ROADMAP.md` marked `[ ]` or `[~]` is fair game. The roadmap is
the specification; this list is only the recommended order.

### 5.3 How to work here

- Read the chapter that owns the task before writing code.
- Run `make test` (or `QT_QPA_PLATFORM=offscreen python3 -m pytest tests/ -q`)
  and check the **exit code**, not only the printed count.
- One requirement per change; tick a ROADMAP box only when it is implemented
  **and** tested; update the documentation in the same change.
- Never install a dependency: stop and report it (see `AGENTS.md` rule 2).
- Real trading stays disabled. That rule has no exceptions.

## 6. Quick-start for the new Agent

```bash
# 1. (Optional) the 8 reference projects under external/ — not needed to
#    build, run or test the application:
git submodule update --init --recursive

# 2. Verify the environment:
python3 --version            # ≥ 3.11 expected (3.13 on record)
python3 -c "import PyQt6, pyqtgraph, sqlalchemy, platformdirs; print('deps OK')"
QT_QPA_PLATFORM=offscreen python3 -m pytest tests/ -q   # 702 passed, 2 skipped expected

# 3. Read in this order:
#    1. AGENT-HANDOFF.md (this file) — state and next steps
#    2. AGENTS.md — the non-negotiable rules
#    3. ROADMAP.md — the specification (find the chapter that owns your task)
#    4. CONTRIBUTING.md — workflow and definition of done
#    5. docs/en/developers/afml-techniques.md (when AFML is needed)
```

If the test count differs, stop and report it before changing anything.

---

*Handoff updated 2026-09-27. Baseline: 702 passed, 2 skipped.*

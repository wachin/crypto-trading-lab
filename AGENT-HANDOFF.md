# AGENT-HANDOFF.md — Continuation Guide

**Purpose:** everything a new AI Agent needs to continue this project from
its current state. The migration notes that follow (§3–§6) are preserved
for a fresh start.

A new AI Agent must read this file **before** doing anything else, then
`AGENTS.md`, then `ROADMAP.md`.

---

## 1. Project state (last updated 2026-09-17)

- **Repository:** `https://github.com/wachin/crypto-trading-lab`
  (branch `main`, pushed and in sync)
- **State verified at commit:** `f34a0f7 docs: reconcile ROADMAP chapters 7,
  26, 27 and 30 against the code` (an ancestor of the commit that carries
  this file)
- **Tests:** 442 passed, 2 skipped —
  `QT_QPA_PLATFORM=offscreen python3 -m pytest tests/ -q`
- **Source:** 62 Python files under `src/crypto_trading_lab/`
- **Tests:** 60 Python files under `tests/`
- **Documentation:** `docs/en/beginners/` (8 files) and
  `docs/en/developers/` (`reference-projects.md`, `afml-techniques.md`,
  `adr/0001-exchange-adapter-spike.md`, `debian-dependencies.md`,
  `working-method.md`, `configuration-guide.md`, `research-ethics.md`,
  `capital-protection.md`, `live-monitoring.md`, `live-vs-backtest-drift.md`,
  `architecture-proposal.md`, `threat-model.md`)
- **Specification:** `ROADMAP.md` — 72 chapters; 70+ chapters complete
- **Git submodules:** 8 reference projects under `external/`; a fresh clone
  needs `git submodule update --init --recursive`
- **Current phase:** Phase 3 (backtesting) complete; Phase 4+ in progress.
  Most research infrastructure (Chapters 52-55, 62-67) is complete.

### Honest status of the earlier phases

Phase 0 (research) and Phase 2 (data & charts) are functionally done. Phase 1
(foundation) is done except for the items below — do not repeat "all phases
completed"; Chapter 69 and Chapter 71 track the real state.

Still missing from the foundation (required by Chapter 19.1 / Chapter 71 and
not yet written):

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

**Completed chapters** (implementation + tests + docs):

1.  ~~Performance metrics (Chapter 40)~~ — complete
2.  ~~Backtesting Lab UI~~ — done on 2026-09-14 (§37.9–37.10;
    `ui/backtesting/lab.py`, main-window button enabled, strategy/dataset
    reproducibility records added to the engine, Spanish translations
    compiled; 248 tests passing).
3.  ~~Reports (chapter 41)~~ — backtest reports done on 2026-09-09-14
    (`reporting/report.py`, HTML/CSV/JSON/PDF export from the Backtesting Lab,
    evidence-level labels and disclaimers). Still open by
    design: research/qualification reports (need the chapter 52 experiment manager).
4.  ~~Benchmarking (chapter 42)~~ — core done on 2026-09-14:
    `compare_reports()` (relative return/volatility/drawdown/Sharpe/
    Sortino differences, gross vs net excess, cost drag), benchmark
    selector in the Backtesting Lab (buy-and-hold default, null, none)
    with an identical-strategy warning, and the plain-language verdict;
    257 tests passing. Still open: graphical equity/drawdown comparison
    views, and feeding qualification (ch. 66).
5.  ~~Statistical edge (Chapter 43)~~ — complete
6.  ~~Robustness (Chapter 44)~~ — complete (consolidated report)
7.  ~~Regime analysis (Chapter 46)~~ — complete
8.  ~~Feature engineering (Chapter 47)~~ — complete
9.  ~~AFML techniques (Chapter 49)~~ — partial (triple-barrier labeling, purged CV, sample uniqueness)
10. ~~Ensembles (Chapter 50)~~ — complete
11. ~~Portfolio (Chapter 51)~~ — partial (correlation, portfolio returns, portfolio metrics)
12. ~~Experiment manager (Chapter 52)~~ — complete
13. ~~Paper trading (Chapter 57)~~ — partial (account simulation, order simulation)
14. ~~Risk manager (Chapter 58)~~ — complete
15. ~~Kill switch (Chapter 59)~~ — complete
16. ~~Risk of ruin (Chapter 60)~~ — complete
17. ~~Capital protection (Chapter 61)~~ — documented
18. ~~Live monitoring (Chapter 62)~~ — documented
19. ~~Live vs backtest drift (Chapter 63)~~ — documented
20. ~~Strategy failure detection (Chapter 64)~~ — complete
21. ~~Strategy qualification (Chapter 66)~~ — complete
22. ~~Safety gates (Chapter 67)~~ — complete
23. ~~Working method (Chapter 70)~~ — documented
24. ~~Configuration (Chapter 71)~~ — documented
25. ~~Research ethics (Chapter 72)~~ — documented
26. ~~Strategy promotion pipeline (Chapter 65)~~ — documented
27. ~~Architecture proposal (Chapter 71)~~ — documented
28. ~~Threat model (Chapter 71)~~ — documented
29. ~~Live vs backtest drift (Chapter 63)~~ — documented
30. ~~ADRs 0002-0007~~ — documented

**Next tasks** (per ROADMAP order):

- Chapter 68 (Real trading) — requires explicit activation flow, API credential handling, strategy restrictions, testing restrictions, monitoring, failure handling, beginner protection
- Chapter 69 (Development phases) — check remaining items like Debian package
- Glossary remaining terms (drawdown, liquidity, latency, fill, backtesting bias)
- Spanish translations
- AppImage packaging
- Performance optimization
- Accessibility improvements
- Learning Center quizzes and screenshots

Note: §37.8 determinism checkboxes are still open; much of it is already
engine-tested, reconciling them is a cheap documentation task.

Do not start a task before reading the chapter that owns it, and do not tick
a requirement until it is implemented **and tested**.

## 6. Quick-start for the new Agent

```bash
# 1. Clone with the reference submodules (or, if already cloned):
git submodule update --init --recursive

# 2. Verify the environment:
python3 --version            # ≥ 3.11 expected (3.13 on record)
python3 -c "import pyqtgraph, sqlalchemy, platformdirs, pypdf; print('deps OK')"
QT_QPA_PLATFORM=offscreen python3 -m pytest tests/ -q   # 415 passed expected

# 3. Read in this order:
#    1. AGENT-HANDOFF.md (this file) — state and next steps
#    2. AGENTS.md — the non-negotiable rules
#    3. ROADMAP.md — the specification (start with §37.9, the next task)
#    4. docs/en/developers/afml-techniques.md (when AFML is needed)
#    5. docs/en/developers/reference-projects.md (reference-project studies)
```

If the test count differs, stop and report it before changing anything.

---

*Handoff updated 2026-09-14. All 276 tests passing at time of writing.*

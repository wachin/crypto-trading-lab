# Unwired modules — audit and disposition

**Date:** 2026-09-27
**Method:** static import graph (AST over `src/` and `tests/`), symbol
grep, git history, and six independent read-only audits. Every claim
marked *(verified)* was re-checked by executing the code, not by reading
it.

## Why this document exists

The repository review of 2026-09-27 found that several chapters are
"implemented" in the sense that a Python module exists, but the module is
imported by no product path and by no test. The README and
`AGENT-HANDOFF.md` describe some of them as complete, which makes the
documentation untrustworthy. This audit records, module by module, which
one survives and which one is deleted, so the decision is not repeated.

Git history explains how it happened: on 2026-09-18/19 a burst of
one-commit-per-chapter work added these modules
(`feat: add <x> module (chapter N)`) and, in several cases, immediately
followed with `docs: mark chapter N as complete`. None of them was ever
wired afterwards.

## Execution status

- **Batch A — delete (9 modules): executed 2026-09-27.** Suite unchanged
  at 630 passed, 2 skipped. `ROADMAP.md` §4.4 item 3 corrected.
- **Batch C, item 13 — `execution_realism` wired: executed 2026-09-27.**
  `paper_session` now calls `simulate_market_order` for entries and exits,
  in both the replay and the live path, with a seeded `random.Random`
  (`PaperSessionConfig.seed`). The model also had two defects fixed on the
  way: slippage could be *favourable* and `simulate_execution` discarded
  its own slippage calculation. 15 tests added; suite 645 passed,
  2 skipped. Backtest/robustness wiring (56.5) remains open, so chapter 56
  is `[~]`, not `[x]`.
- **Batch C, item 14 — `reproducibility` wired: executed 2026-09-27.**
  `ExperimentManager.create()` now produces `code_hash` and `environment`
  for every record. Fixed on the way: the code hash returned the empty
  SHA-256 outside the repo root, `capture_environment()` wrote
  `CRYPTO_*`/`TRADING_*` values (possible API keys) in clear text, and the
  dependency scan used the deprecated `pkg_resources`. 12 tests added;
  suite 657 passed, 2 skipped.
- **Batch C, item 15 — `live_vs_backtest` wired: executed 2026-09-27.**
  Four defects fixed (regime bucket, non-deterministic metric order, float
  fill rates, zero-baseline mislabelling) and the Paper Trading screen now
  shows the drift against the same strategy's backtest. `BacktestConfig`
  gained `position_fraction` so the comparison cannot mistake sizing for
  drift. 15 tests added; suite 672 passed, 2 skipped.
- **Batch B, item 11 — `research_ethics` merged into reports: executed
  2026-09-27.** The checker now guards every generated report (it raises on
  a missing disclaimer or profit-guarantee language), the mandatory
  disclaimers, assumptions and limitations ship in all formats, and two
  latent bugs were fixed: "out-of-sample" was not recognised, and
  `render_pdf()` had been broken since pypdf 5. 11 tests added; suite 683
  passed, 2 skipped.
- **Batch B, item 10 — `risk_of_ruin` merged into `robustness`: executed
  2026-09-27.** Kelly sizing is ported and reachable
  (`ResearchRun.recommended_risk_per_trade` + warnings); the unsound
  closed-form ruin formulas were deliberately not ported. 15 tests added;
  suite 698 passed, 2 skipped.
- **Batch B, item 12 — `exchanges/coinbase/` deleted: executed
  2026-09-27.** Dead, unreachable and non-functional; `ROADMAP.md` §26.3 and
  the live-trading roadmap now say Coinbase is **not implemented** instead
  of claiming otherwise. No test count change (nothing imported it): 698
  passed, 2 skipped.
- **Still open:** `strategy_registry` (item 16). It keeps its module until
  the wiring lands.

## Summary

| # | Module | Chapter | ROADMAP | Disposition |
|---|---|---|---|---|
| 1 | `benchmarking.py` | 42 | `[~]` | **Delete** — superseded by `metrics.compare_reports` |
| 2 | `live_monitoring.py` | 62 | `[~]` | **Delete** — non-functional *(verified)*, superseded |
| 3 | `research_notebooks.py` | 54 | `[ ]` | **Delete** — contradicts the chapter-76 design |
| 4 | `capital_protection.py` | 61 | `[~]` | **Delete** — duplicate of `risk_manager`/`safety_gates` |
| 5 | `working_method.py` | 70 | `[~]` | **Delete** — docs-as-code duplicate of the markdown |
| 6 | `development_phases.py` | 69 | `[~]` | **Delete** — broken *(verified)* and contradicts ROADMAP |
| 7 | `infrastructure/performance.py` | 13 | `[~]` | **Delete** — caller-less; cache already exists elsewhere |
| 8 | `ui/charts/qt_websocket_client.py` | 4.2 | `[x]` | **Delete** — duplicate of the tested WS client |
| 9 | `machine_learning/strategies.py` | 48 | `[ ]` | **Delete** — unwired draft; ensembles duplicated |
| 10 | `risk_of_ruin.py` | 60 | `[ ]` | **Merge** the sizing formulas, then delete |
| 11 | `research_ethics.py` | 72 | `[~]` | **Merge** `EthicsChecker` into reports, then delete |
| 12 | `exchanges/coinbase/` | 26.3 | `[ ]` | **Delete** — dead, non-functional; ROADMAP corrected |
| 13 | `execution_realism.py` | 56 | `[x]` | **Wire** into `paper_session` |
| 14 | `reproducibility.py` | 53 | `[~]` | **Wire** into `ExperimentManager` |
| 15 | `live_vs_backtest.py` | 63 | `[~]` | **Wire** (sole implementation), fix bug first |
| 16 | `strategy_registry.py` | 36 | `[~]` | **Wire** (sole implementation) into the Lab |

## Batch A — delete (zero importers, zero tests)

None of these is imported by any file in `src/` or `tests/`, so removing
them cannot change the suite. All are recoverable from git history.

### 1. `benchmarking.py` (chapter 42)

- Live owner: `backtesting/metrics.py` — `BenchmarkComparison`,
  `BenchmarkView`, `compare_reports` (`metrics.py:153,163,186`), wired
  into the Backtesting Lab (`ui/backtesting/lab.py:49,788`) and tested
  (`tests/backtesting/test_metrics.py`).
- Overlap: subset. `compare_against_benchmarks` returns three raw
  differences; `compare_reports` adds gross-vs-net excess, cost drag and
  Sortino. `buy_and_hold_benchmark` duplicates the live buy-and-hold
  path.
- Unique: `risk_free_benchmark`, `market_index_benchmark` — outside the
  benchmark set chapter 42 states (buy-and-hold and simple/null).

### 2. `live_monitoring.py` (chapter 62)

- **Non-functional (verified).** `register_component` stores
  `ComponentHealth(name=name)` and discards the `checker`
  (`live_monitoring.py:101-103`); `check_all` then calls that object
  (`:113-129`), always raising and always reporting `CRITICAL`.
  `ComponentStatus.CRITICAL` does not exist (`:294`).
- Live owners: `exchanges/feed_health.py`,
  `exchanges/connection_manager.py` (`StaleDataDetector`),
  `exchanges/connection_state_descriptors.py`,
  `monitoring/failure_detection.py` and `ui/connection_health_widget.py`
  (UI-wired at `ui/main_window/window.py:276`).
- The chapter-62 narrative already lives in
  `docs/en/developers/live-monitoring.md`. Its portfolio/positions/orders
  display is genuinely unimplemented and needs a new home when chapter 62
  is really built.

### 3. `research_notebooks.py` (chapter 54)

- A second notebook model (cells, `execute_cell`) that contradicts the
  design fixed in chapter 76: `ui/research/notebook.py:1-8` states every
  entry *is* an experiment record, backed by
  `machine_learning/experiment_manager.py` (notes, search, compare,
  export) and wired into the main window.
- No requirement in `ROADMAP.md:3680-3696` asks for markdown/code cells.

### 4. `capital_protection.py` (chapter 61)

- Duplicate of `risk_manager.py` (daily/weekly loss, position, exposure
  and frequency limits; `risk_manager.py:141-236`), which is the one
  wired into Paper Trading (`paper_session.py:332,381`).
- Logic defects *(read)*: unused `daily_loss` (`:123`),
  `_get_current_level` returns the last action ever appended (`:291-295`),
  hard-coded 10000 initial capital (`:93-97`).
- `docs/en/developers/capital-protection.md` already carries the concept.

### 5. `working_method.py` (chapter 70)

- Docs-as-code duplicate of `docs/en/developers/working-method.md:7-79`
  and `AGENTS.md` rule 8. No product path calls the scoring machinery.

### 6. `development_phases.py` (chapter 69)

- **Broken (verified):**
  `get_current_phase(set(range(1, 69)))` and `get_next_milestone(...)`
  raise `KeyError: DevelopmentPhase.PHASE_6` because `PHASE_6` has no
  entry in `PHASE_DEFINITIONS`.
- **Contradicts the roadmap:** its `PHASE_4` is "Research Infrastructure"
  while `ROADMAP.md:4640-4650` defines Phase 4 as "Paper trading"; it
  stops at `PHASE_7` while the roadmap defines Phase 8/8+.
- `ROADMAP.md` chapter 69 already is the phase checklist.

### 7. `infrastructure/performance.py` (chapter 13)

- `memoize_candles` keys on `str(args)` (`:22`), so equal `Candle` objects
  miss and the cache is unbounded; `DataBatcher` is a caller-less loop.
  A correct indicator cache already exists in `rule_strategy.py:211-237`.

### 8. `ui/charts/qt_websocket_client.py` (chapter 4.2)

- Duplicates the tested `exchanges/binance/websocket_client.py`
  (`BinanceWebSocketClient`, `MessageTracker`) and
  `exchanges/connection_manager.py` (`ReconnectionPolicy`,
  `CircuitBreaker`, `StaleDataDetector`); only the transport differs
  (Qt vs asyncio).
- No UI screen references any WebSocket client, so the Qt signal surface
  has no consumer. Defect: the kline interval is hard-coded to `1m`
  (`:266`).
- The ROADMAP chapter-4.2 credit at `ROADMAP.md:366` must be re-pointed.

### 9. `machine_learning/strategies.py` (chapter 48)

- Unwired, untested; its `EnsembleStrategy` / `EqualWeightEnsemble`
  duplicate the tested `ensembles.py`. Chapter 48 is `[ ]`.
- Maintainer's call: chapter 48 needs a dependency decision
  (`numpy` arrives only transitively through pyqtgraph) before it can be
  built honestly. Recommend deleting and rebuilding against that
  decision.

## Batch B — merge the unique part, then delete

### 10. `risk_of_ruin.py` (chapter 60) → `backtesting/robustness.py` — DONE

- **Was:** unwired. The live path already owned the Monte-Carlo half of
  chapter 60 (`RiskOfRuinReport`, `PositionSizingConfig`,
  `compute_risk_of_ruin`, tested in `tests/backtesting/test_risk_of_ruin.py`).
- **Ported:** `kelly_fraction()` and `optimal_bet_size()` (Kelly, scaled to
  half by default and capped by `PositionSizingConfig.max_risk_per_trade`),
  plus a new `position_size_from_trades()` that derives the win rate and
  payoff ratio from the backtest's own closed trades. It returns 0 **with a
  warning** when the sample is too small, has only wins or only losses, or
  shows no edge, and warns when the estimated edge is suspiciously large.
  `RiskOfRuinReport` gained `recommended_risk_per_trade`, and
  `ResearchRun.recommended_risk_per_trade` carries it to the research
  output, where `ui/research/validity.py` already renders `run.warnings`.
- **Not ported, on purpose:** `risk_of_ruin_binomial()`,
  `risk_of_ruin_diffusion()`, `capital_depletion_path()` and
  `sequential_risk_of_ruin()`. The first two mix units and multiply a
  per-trade expectancy by 100/50 and call it "expected drawdown" and
  "median drawdown" — numbers that look precise and are not; the last
  returns 0/1 while claiming to be a probability. Importing them into the
  tested path would have damaged it. The Monte-Carlo estimate that already
  exists is more defensible.
- **Follow-up:** `compute_risk_of_ruin()`/`RiskOfRuinReport` are still only
  reached by tests: `research.py` reads `monte_carlo.risk_of_ruin` and calls
  `position_size_from_trades()` directly. Either fold the wrapper into
  `compute_robustness_report()` or drop it — do not leave two ruin numbers
  that disagree. Chapter 60 stays `[~]` for the size-versus-ruin curve.

### 11. `research_ethics.py` (chapter 72) → report generation — DONE

- **Was:** unwired. `EvidenceLevel`/`format_evidence_label` duplicated
  `ui/research/validity.py` and `reporting/report.py`; the disclaimer
  catalog existed but no report ever carried it.
- **Now (2026-09-27):** the used part moved to `reporting/ethics.py`
  (`EthicsChecker`, `STANDARD_DISCLAIMERS`, `EthicalCheckResult`,
  `EthicsError`, `ETHICS_WARNING`); the unused `EvidenceLevel`,
  `EvidenceLabel`, `generate_evidence_label`, `format_evidence_label` and
  `WarningType`/`EthicalWarning` were dropped rather than carried over as
  dead weight. `reporting/report.py` now:
  - embeds the five mandatory disclaimers (performance, risk, statistical,
    overfitting, general) in HTML, CSV, JSON and PDF;
  - adds explicit **Assumptions** and **Limitations** sections;
  - runs `audit_report_ethics()` over every rendered format and **raises
    `EthicsError`** on a violation (missing disclaimer, profit-guarantee
    language), while attaching warnings instead of raising for omissions.
- Two bugs were fixed while merging: the out-of-sample check only matched
  the underscore spelling, so the normal English "out-of-sample" was
  reported as missing; and `render_pdf()` called
  `PdfWriter._addObject`/`_writeObject`/`.stream`, private names that pypdf
  5 removed, so **PDF export raised `AttributeError`**. `render_pdf()` now
  builds the document with the current API and returns bytes; a test reads
  the result back with `PdfReader`.
- `research_ethics.py` was deleted. Still open: 72.1's remaining items,
  and all of 72.3/72.4. Chapter 72 stays `[~]`.

### 12. `exchanges/coinbase/` (chapter 26.3) — DONE

- **Was:** a native read-only adapter, capability-identical to
  `CcxtExchangeAdapter` and structurally twin to `BinanceRestAdapter`, with
  `CcxtWebSocketClient.subscribe` already generalising the Coinbase one.
  Nothing in `src/` or `tests/` imported it, and `exchanges/__init__.py`'s
  own layout note never listed it.
- **Defects (verified):** `record_success()` ran **before** the request
  (`adapter.py:302`), so the circuit breaker could never open; `stop()` was
  declared twice, with the synchronous definition at `:454` silently
  overriding the async one at `:447`; `start()` was a placeholder that set
  `CONNECTED` without connecting; the `StaleDataDetector` was built and
  never used.
- **Action taken (2026-09-27):** the whole `exchanges/coinbase/` package
  was deleted, including `config.py`. The audit had suggested keeping
  `config.py`, but after removing the adapter nothing imported it either,
  and the substitute path (CCXT) manages its own endpoints — keeping it
  would have recreated exactly the dead-code problem this audit exists to
  fix. The Coinbase sandbox warning it carried was preserved in
  `ROADMAP.md` §26.3.
- **Not routed through CCXT at the time:** `CcxtExchangeAdapter` takes an
  injected ccxt **client instance**, not an `exchange_id`, and `ccxt` is an
  optional PyPI-only dependency that was not installed. Adding a caller
  would have been unverifiable then, so `ROADMAP.md` §26.3 and
  `docs/en/developers/live-trading-roadmap.md` were corrected: Coinbase is
  **not implemented**, not "Implemented".
- **Update (2026-09-27, after the maintainer created the venv):** the CCXT
  path was verified live. ccxt 4.5.84 covers 104 exchanges, both Binance and
  Coinbase expose the surface the adapter calls, and
  `CcxtExchangeAdapter.fetch_candles()` returned normalised (Decimal + UTC)
  candles from **both** exchanges. The measured evidence, including the fact
  that Coinbase's liquid pair is BTC/USD while Binance's is BTC/USDT, is
  recorded in `docs/en/developers/venv-setup.md` §7. Chapter 26.3's
  *native* adapter stays deleted; the second exchange is now reachable
  through the optional CCXT path (not exposed in the UI yet).
- Rebuilding it later means a native adapter over the existing
  `ExchangeAdapter` port, or a documented CCXT path with the dependency
  decision of chapter 4.

## Batch C — wire (unique value, spec-relevant)

### 13. `execution_realism.py` (chapter 56) → `paper_session.py` — DONE

- **Was:** `paper_session.py` imported `ExecutionConfig` and
  `simulate_execution`, but never called `simulate_execution`; it read only
  `impact_factor` and faked a partial fill with an **unseeded**
  `random.random() < 0.1`, which made paper-trading results
  non-reproducible.
- **Now (2026-09-27):** `run_paper_session` and `run_paper_session_live`
  call `simulate_market_order` for entries and exits. A synthetic,
  documented order book (`synthetic_order_book`) provides depth, so an
  order larger than the modelled liquidity is partially filled or
  rejected instead of being assumed away. `PaperSessionConfig` and
  `LivePaperConfig` gained a `seed`, and every draw now comes from one
  seeded `random.Random`, so a session is reproducible.
- Two defects in the model were fixed on the way: slippage could come out
  **favourable** (a buy below mid) because the random term could push the
  total negative, and `simulate_execution` computed its slippage price and
  then discarded it, returning the raw book-ladder average and reporting
  market impact as if it were slippage.
- Still open: item **56.5** also requires the backtest engine (chapter 37)
  and robustness (chapter 44) to use the model. They still use the simple
  `CostModel`. Chapter 56 is therefore `[~]`.

### 14. `reproducibility.py` (chapter 53) → `ExperimentManager` — DONE

- **Was:** `ExperimentRecord.code_hash` existed but was only ever copied
  from another record; nothing produced it, and no record carried the
  environment. `ROADMAP.md` had "every experiment must record the
  environment" unchecked.
- **Now (2026-09-27):** `ExperimentManager.create()` fills a blank
  `code_hash` with `compute_code_hash()` and attaches a compact
  `environment` (Python, platform, git revision, dependency versions) from
  `capture_environment()` → `environment_summary()`, captured once per
  manager. `ExperimentRecord.environment` is serialised and preserved by
  `update_status`, `add_note`, `add_tag` and `save`/`load`.
- Three defects were fixed first:
  - `compute_code_hash()` walked the **relative** path `"src"`, so from any
    other working directory it hashed nothing and returned the SHA-256 of
    the empty string (`e3b0c442…`). It now hashes the package directory,
    includes relative paths, and is cwd-independent *(verified from
    `/tmp`)*.
  - `capture_environment()` recorded the **values** of every `CRYPTO_*` /
    `TRADING_*` variable, so an API key in the environment would have been
    written in clear text into `experiments.json`. Names that look like
    credentials are now stored as `***`; other relevant variables keep
    their values.
  - The dependency scan used the deprecated `pkg_resources` and took
    ~520 ms per call; it now uses `importlib.metadata` and is cached per
    process.
- Still open: 53.1's remaining items (commission/slippage/execution model,
  time range, schema version, application version) and 53.3 (re-run
  verification). Chapter 53 stays `[~]`.

### 15. `live_vs_backtest.py` (chapter 63) — DONE

- **Was:** unwired, and `calculate_regime_drift` appended the *live*
  return into the `"bt"` bucket, so every regime reported a drift of
  exactly zero. `calculate_drift_metrics` iterated a `set`, so the metric
  order (and therefore the report) was non-deterministic; fill rates were
  computed with float division; a zero backtest baseline was reported as
  "no drift".
- **Now (2026-09-27):** all four defects fixed, plus
  `drift_report_from_results()` (a `BacktestResult` vs a
  `PaperSessionResult`) and `render_drift_report()`. The Paper Trading
  screen runs the same strategy as a backtest after each session and shows
  the drift table, so chapter 63 is visible to the user.
- **A subtler trap found while wiring:** the backtest engine invested
  100 % of available cash while the paper session uses
  `position_fraction` (0.5 by default). Comparing their returns would have
  reported a **sizing artefact as drift** — the exact kind of misleading
  metric this project forbids. Fixed at the root: `BacktestConfig` gained
  `position_fraction` (default `1`, so existing behaviour is unchanged),
  the Paper screen backtests with the session's fraction, and
  `drift_report_from_results()` emits a `SIZING MISMATCH` warning if the
  two ever disagree.
- The bridge also sums the engine's separate `slippage` + `spread` before
  comparing them with the paper session's single `total_slippage`, which
  already includes both.
- Still open: 63.1 latency/volatility/regime-change drift, and all of 63.2
  (drift over time, causes, degradation marking) and 63.3. Chapter 63
  stays `[~]`.

### 16. `strategy_registry.py` (chapter 36)

- Sole implementation of a strategy catalog. Today the Backtesting Lab
  hard-codes its three strategies (`ui/backtesting/lab.py:84-94`) and the
  Paper screen hard-codes its own list.
- Caveats: it covers only id/name/version/parameters of the ~15 chapter-36
  requirements; `import_registry` drops factories (`:271-276`) and
  `_load` (`:288`) is never called.
- Action: wire `list_strategies`/`search` into the Lab combo and add
  tests; complete the missing chapter-36 items separately.

## Findings beyond this audit

These are not duplications, but the same credibility problem surfaced
while auditing and they belong in the same conversation:

- **`kill_switch.py` and `safety_gates.py` are imported only by their
  own tests.** README's safety table presents them as guards; no product
  path reaches them today.
- **`ui/trading/testnet.py` *is* wired** (`ui/main_window/window.py:43,743`)
  while the README lists Testnet as "⬜ not built". The screen exists;
  whether it can place a real testnet order is a separate question.
- **ROADMAP chapter 56 is `[x]`** while the README admits execution
  realism is not wired. One of the two is wrong; batch C fixes the code
  rather than the checkbox.
- Every module in this audit was added in the 2026-09-18/19 burst and
  never touched again. The pattern — module first, integration never — is
  the root cause, not any single file.

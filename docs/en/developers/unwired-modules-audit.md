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
- **Batch B — merge, and Batch C — wire: open.** No code has been removed
  for these; each keeps its module until the port/wiring lands.

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
| 12 | `exchanges/coinbase/adapter.py` | 26.3 | `[~]` | **Merge** via CCXT, then delete |
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

### 10. `risk_of_ruin.py` (chapter 60) → `backtesting/robustness.py`

- The live path already owns chapter 60: `RiskOfRuinReport`,
  `PositionSizingConfig`, `compute_risk_of_ruin`
  (`robustness.py:483,491,502`), Monte-Carlo based, seeded, with explicit
  assumptions and warnings, tested in
  `tests/backtesting/test_risk_of_ruin.py` and surfaced by
  `research.py:239,357`.
- Unique in the dead module: the closed-form sizing math
  `kelly_fraction` (`:36`) and `optimal_bet_size` (`:257`); also
  `risk_of_ruin_binomial`/`_diffusion` and `capital_depletion_path`.
- Action: port `kelly_fraction` + `optimal_bet_size` into
  `robustness.py` as advisory sizing helpers with tests, then delete the
  module and its duplicated `RiskOfRuinConfig`/`Result`/`WARNING`
  scaffolding. Keep chapter 60 `[ ]` until the ported functions are
  tested.

### 11. `research_ethics.py` (chapter 72) → report generation

- Duplicate part: `EvidenceLevel`/`format_evidence_label` duplicate
  `ui/research/validity.py:70` and `reporting/report.py:36`; the
  six-category disclaimer catalog overlaps `metrics.DISCLAIMER`
  (`metrics.py:36`).
- Unique part: `EthicsChecker.check_report()` — an automated scan for
  missing disclaimers, profit-guarantee language, cherry-picking and
  missing out-of-sample discussion. Nothing in the product does this.
- The prose already lives in `docs/en/developers/research-ethics.md`.
- Action: call `EthicsChecker.check_report()` from report generation as a
  chapter-72 assertion (report must fail or warn loudly), then delete the
  module.

### 12. `exchanges/coinbase/adapter.py` (chapter 26.3) → CCXT

- Capability-identical to `CcxtExchangeAdapter`
  (`exchanges/ccxt/adapter.py`) and structurally twin to
  `BinanceRestAdapter`; `CcxtWebSocketClient.subscribe`
  (`ccxt/adapter.py:725`) already generalises the Coinbase one.
- Defects *(read)*: `record_success()` called before the request
  (`:302`), `start()` is a placeholder (`:443-445`), `stop()` is declared
  twice (sync at `:454` silently overrides async at `:447`), the
  `StaleDataDetector` is built and never used (`:98`).
- Action: keep `exchanges/coinbase/config.py`, route Coinbase through
  `CcxtExchangeAdapter(exchange_id="coinbase")`, delete `adapter.py`, and
  re-mark `ROADMAP.md:1848-1850` as unmet instead of implying a native
  adapter exists.

## Batch C — wire (unique value, spec-relevant)

### 13. `execution_realism.py` (chapter 56) → `paper_session.py`

- **The import is decorative (verified):** `paper_session.py:27` imports
  `ExecutionConfig` and `simulate_execution`, but `simulate_execution` is
  never called anywhere in the repo. `paper_session` reads only
  `impact_factor` (`:452`) and fakes a partial fill with an **unseeded**
  `random.random() < 0.1` (`:464-465`), which makes paper-trading results
  non-reproducible.
- Chapter 56 is marked `[x]`, and item 56.5 requires execution realism to
  feed backtest and paper trading. Today it does not.
- Action: in `run_paper_session` replace the inline blocks
  (`:458-475` entry, `:494-502` exit) with one `simulate_execution(...)`
  call each using a synthetic `OrderBookSnapshot` and the configured
  `adv`; mirror it in `run_paper_session_live` (`:696-751`); seed
  determinism from the session seed. Add tests. Then chapter 56's `[x]`
  becomes true instead of aspirational.

### 14. `reproducibility.py` (chapter 53) → `ExperimentManager`

- Unique: `capture_environment()`/`EnvironmentSnapshot` (no environment
  capture exists anywhere), `compute_code_hash()`, `RunManifest`,
  `save_manifest`/`load_manifest`, `set_deterministic_seeds`.
- `ExperimentRecord.code_hash` exists (`experiment_manager.py:68`) but is
  only ever copied from another record
  (`ui/research/notebook.py:370`); nothing produces it.
  `ROADMAP.md` still has "every experiment must record the environment"
  unchecked — this module is the missing producer.
- Fix before wiring *(verified)*: `compute_code_hash` walks the relative
  path `"src"` (`reproducibility.py:105`), so it silently hashes nothing
  when the cwd is not the repo root; it also uses the deprecated
  `pkg_resources` (`:59`).
- Action: fix those two, feed `capture_environment()` +
  `compute_code_hash()` into `ExperimentManager.create()`, add tests.

### 15. `live_vs_backtest.py` (chapter 63)

- Sole implementation of backtest-vs-live drift (no counterpart:
  `robustness.out_of_sample_degradation` compares train vs out-of-sample
  inside one backtest, not live data).
- **Bug (verified):** `calculate_regime_drift` appends `live_r` into the
  `"bt"` bucket (`:256`), so per-regime drift is identically zero.
- Action: fix the bucket bug, add tests, then feed it from the Paper
  Trading session (which today only reports aggregate slippage) so drift
  becomes visible to the user. Align its default thresholds with
  `docs/en/developers/live-vs-backtest-drift.md`.

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

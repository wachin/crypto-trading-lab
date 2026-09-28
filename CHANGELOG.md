# Changelog

All notable changes to Crypto Trading Lab are documented in this file.
The format is based on [Keep a Changelog](https://keepachangelog.com/),
and the project intends to follow
[Semantic Versioning](https://semver.org/) once it reaches 1.0
(current version: `0.0.0.dev0`).

Entries before this file existed live only in `git log --oneline`; the
list below starts at the repository review that created it. For the
per-chapter state of the specification, see [`ROADMAP.md`](ROADMAP.md).

## [Unreleased]

### Added

- `tests/market_data/test_quality.py`: the Chapter 29 data-quality
  framework (`market_data/quality.py`) now has an offline test suite —
  validation, stale/frozen rules, volume anomalies, configuration and
  report serialization.
- `tests/ui/test_accessibility.py` now verifies that the tab order is
  actually applied, and that a cross-window call fails loudly.
- `CODE_OF_CONDUCT.md`, `CHANGELOG.md` and `.gitattributes` so a fork
  inherits community rules, a change history and consistent line
  endings.
- `invalid_count` is accepted by `create_quality_report()` and
  `validate_dataset_quality()`, so rejected raw rows are reported as an
  `INVALID_OHLCV` error instead of being dropped silently.
- Missing `__init__.py` files for `crypto_trading_lab.machine_learning`,
  `crypto_trading_lab.testing` and `crypto_trading_lab.monitoring`.
  Without them `setuptools.find_packages()` omitted those packages from
  a built distribution (27 → 30 packages discovered).
- The `integration` pytest marker is declared in `pyproject.toml`.
- `docs/en/developers/unwired-modules-audit.md`: a per-module audit of the
  16 modules that no product path imports, with an explicit
  delete / merge / wire disposition for each.
- The chapter-56 execution model is now wired into paper trading:
  `paper_session.run_paper_session` and `run_paper_session_live` call
  `simulate_market_order` for entries and exits. `PaperSessionConfig` and
  `LivePaperConfig` gained a `seed`, `execution_realism` gained
  `synthetic_order_book()` / `simulate_market_order()` and an injectable
  `random.Random`, and `tests/test_execution_realism.py` adds 15 tests.
- Chapter 53 reproducibility is now wired into research records:
  `ExperimentManager.create()` fills `code_hash` from the source and
  attaches a compact `environment` (Python, platform, git revision,
  dependency versions) to every `ExperimentRecord`, which round-trips
  through `update_status`, notes, tags and `save`/`load`.
  `reproducibility` gained `environment_summary()`,
  `capture_environment(include_packages=...)` and a cached dependency scan;
  `tests/test_reproducibility.py` adds 12 tests.
- Chapter 63 drift is now wired to the Paper Trading screen:
  `live_vs_backtest` gained `drift_report_from_results()` and
  `render_drift_report()`, and every paper session is compared with the
  same strategy's backtest at the same sizing. `BacktestConfig` gained
  `position_fraction` (default `1`, so existing backtests are unchanged);
  it is recorded in `metadata()` and `tests/test_live_vs_backtest.py` adds
  10 tests.
- Chapter 72 ethics now guards report generation: `reporting/ethics.py`
  holds `EthicsChecker` + `STANDARD_DISCLAIMERS`, and every HTML/CSV/JSON
  report carries the five mandatory disclaimers plus explicit
  **Assumptions** and **Limitations** sections. `audit_report_ethics()`
  raises `EthicsError` on a violation (missing disclaimer, profit-guarantee
  language) and attaches warnings for omissions;
  `tests/reporting/test_report_ethics.py` adds 11 tests.
- Chapter 60 position sizing is implemented and reachable:
  `robustness.kelly_fraction()`, `optimal_bet_size()` (half-Kelly by
  default, capped by `PositionSizingConfig`) and
  `position_size_from_trades()`, which derives the edge from the backtest's
  own trades and returns 0 **with a warning** when the sample is too small,
  degenerate or edgeless. `RiskOfRuinReport` gained
  `recommended_risk_per_trade` and `ResearchRun` carries it to the research
  output. `tests/backtesting/test_risk_of_ruin.py` adds 15 tests.
- `docs/en/developers/venv-setup.md`: the complete virtualenv guide —
  every dependency under its Debian **and** PyPI name, both venv routes
  (`--system-site-packages` over the Debian Qt stack, or fully isolated),
  run/test commands, troubleshooting, and how to decide whether `ccxt` is
  worth adopting. `pyproject.toml` gained the `pdf` extra, and
  `tools/evaluate_ccxt.py` is a read-only script that
  reports ccxt's coverage and whether the project's adapter accepts a real
  client. Section 7 of that guide records the **measured** evaluation: ccxt
  4.5.84, 104 exchanges, Binance and Coinbase both exposing the required
  surface, `fetch_candles()` returning normalised Decimal+UTC candles from
  **both** exchanges over the network, and the suite passing inside the venv
  (698 passed, 2 skipped). Verdict: ccxt is worth adopting for chapter 26.3
  because it is the only path to a second exchange.
- Cross-platform pip installation: the four runtime packages are now
  declared in `[project.dependencies]`, so a plain `pip install .` works on
  Linux, macOS and Windows instead of installing nothing; `keyring` moved to
  a `credentials` extra. The README gained per-platform tutorials (Linux,
  macOS, Windows) covering the PowerShell execution-policy error and its
  safe per-session fix, and clearly marking Windows/macOS as **not yet
  verified**. `.github/workflows/cross-platform.yml` runs the suite on
  Ubuntu, macOS and Windows — `workflow_dispatch` only, so it can never
  redden the default CI.
- `Experiments/`: a self-contained verification kit for machines without
  Debian packages. `requirements-all.txt` lists every dependency (including
  `ccxt`), `setup_windows.bat` and `run_verify.cmd` do the setup in `cmd.exe`
  so PowerShell's execution policy is never involved, `verify.py` runs twelve
  checks (imports, CSV import, backtest, paper trading, the offscreen Qt
  window, the ccxt adapter) with optional `--tests`, `--gui` and `--network`
  stages and writes `verify-report.md`, and `CHECKLIST.md` is a tick-box
  manual to fill in and return. A 400-candle sample dataset lets the whole
  pipeline be exercised with no network. The generated report is
  git-ignored.

### Fixed

- `venv-setup.md` now explains the two messages a `pip install` prints
  inside a `--system-site-packages` venv: `Not uninstalling X … outside
  environment` (pip correctly refusing to modify the Debian packages) and
  `ERROR: pip's dependency resolver … weasyprint … html5lib` (a conflict in
  a *system* package this project does not use; the install still succeeds
  and pip exits 0).
- The documented test baseline had been left at **683 passed, 2 skipped**
  in ten places (the README badge and body, `AGENTS.md`,
  `AGENT-HANDOFF.md`, `CONTRIBUTING.md`, `Makefile`, the pull-request
  template and the developer docs) after the chapter-60 turn: a previous
  update used the wrong search value and silently changed nothing. It is
  **698 passed, 2 skipped**.
- `README.md` no longer states the blanket "No virtualenv, no `pip install`,
  no network"; the Debian-first default is unchanged, and the PyPI-only
  path is documented separately in `venv-setup.md`. `CONTRIBUTING.md` and
  `debian-dependencies.md` say the same thing instead of "no virtualenv".
- `render_pdf()` was broken: it called `PdfWriter._addObject` /
  `_writeObject` / `.stream`, private names that pypdf 5 removed, so every
  PDF export raised `AttributeError`. It now builds the document with the
  current API, escapes PDF string delimiters that a strategy name could
  inject, and returns bytes.
- The ethics checker only matched the underscore spelling of
  "out_of_sample", so the normal English "out-of-sample" was reported as
  missing.
- `live_vs_backtest.calculate_regime_drift()` put the **live** return into
  the backtest bucket, so per-regime drift was always exactly zero. It also
  silently truncated mismatched inputs; it now raises.
- `calculate_drift_metrics()` iterated a `set`, so metric order and the
  report were non-deterministic, and a zero backtest baseline was reported
  as "no drift" instead of material.
- `analyze_execution_drift()` computed fill rates with float division,
  leaking binary floating point into a money-adjacent report.
- The drift bridge cannot mistake position sizing for drift: the backtest
  engine invested 100 % of cash while the paper session uses
  `position_fraction`, so returns now require matched sizing and a mismatch
  is reported as a `SIZING MISMATCH` warning rather than a fake drift.
- `reproducibility.compute_code_hash()` walked the **relative** path
  `"src"`, so running the app or the tests from any other directory hashed
  nothing and returned the SHA-256 of the empty string (`e3b0c442…`). It is
  now cwd-independent.
- `capture_environment()` stored the **values** of every `CRYPTO_*` /
  `TRADING_*` environment variable, so an API key present in the
  environment would have been written in clear text into
  `experiments.json`. Variables whose name looks like a credential are now
  recorded as `***` (chapter 9 / threat model).
- `reproducibility` no longer uses the deprecated `pkg_resources`; the
  dependency scan uses `importlib.metadata` and is cached per process
  (~520 ms per call before).
- Chapter 56's model was inert: `paper_session` imported
  `simulate_execution` and never called it, so an `execution_config` only
  changed one `impact_factor` term and partial fills came from an
  **unseeded** `random.random()`, making paper-trading runs
  non-reproducible. Seeds now make a session reproducible, and an order
  larger than the modelled liquidity is partially filled or rejected
  instead of being assumed away.
- `simulate_execution` computed its slippage price and then discarded it,
  returning the raw book-ladder average and reporting market impact in the
  `slippage_bps` field. The slippage model now sets the price and the
  reported slippage.
- `calculate_slippage` could return **favourable** slippage — the random
  term could push the total negative, so a buy filled below mid. Slippage
  is now clamped to be adverse, as slippage is by definition.
- `run_paper_session_live` divided the P/L of a partial exit incorrectly
  and always recorded `entry.slippage = 0` because it read `position`
  after zeroing it.

- `create_quality_report()` raised `TypeError` because it indexed the
  `DataQualityReport` returned by `validate_dataset_quality()`
  (`report[0]`).
- `DataQualityValidator` no longer mislabels missing, duplicate or
  invalid-row counts as `GRID_ALIGNMENT` warnings; only genuinely
  off-grid timestamps get that code.
- Keyboard tab order set by `MainWindow` had no effect: it was applied
  before the buttons shared a top-level window, which Qt silently
  ignores. The call now runs after `setCentralWidget()`, and
  `AccessibilityHelper.set_tab_order()` raises `ValueError` instead of
  pretending when widgets live in different windows.
- `machine_learning/strategies.py` was deleted (see Removed); earlier in
  this batch it had an unused `scipy` import, a `NameError` in
  `evaluate_ensemble()` (`report` → `performance`) and duplicate `__all__`.
- `features.py` no longer declares `compute_asset_correlations()` with a
  bare `except:` next to an `import scipy.stats` the project does not
  ship (see Removed).
- `setup.py` duplicated metadata from `pyproject.toml` and disagreed
  with it (different dependencies, missing packages). It is now a
  metadata-free shim, and the license is declared with the SPDX
  expression `GPL-3.0-only` instead of the deprecated TOML table.
- `pyproject.toml` package data now includes the Learning Center
  tutorial figures, so an installed copy can display them.
- `media-generation/README.md` and `generate_tutorial_images.py` no
  longer hard-code the maintainer's `/home/wachin/...` path.
- Documented test baseline corrected to **698 passed, 2 skipped**
  across `README.md`, `AGENTS.md`, `AGENT-HANDOFF.md`,
  `CONTRIBUTING.md`, `Makefile`, the pull-request template and the
  developer docs. It had drifted between 229, 415, 522, 599 and 611.
- `AGENTS.md` "Current position" no longer claims the project is at
  chapter 40; that chapter is implemented.
- `ROADMAP.md` header rewritten as an English specification preamble
  instead of an audit report about a file that is not in the repository.

### Removed

- Obsolete root-level scratch files (translation scripts, an orphan
  JSON Schema and internal audit/plan notes). They are preserved
  locally under `.scratch/`, which is git-ignored.
- The archived `numba-vs-decimal` benchmark script, which imported the
  deleted `performance/numba_accel` module. The decision record it
  supported is kept in `docs/en/developers/benchmarks/README.md`.
- Dead chapter-51 portfolio code that had been pasted into
  `market_data/features.py` (`portfolio_backtest`,
  `compute_asset_correlations`, `compute_portfolio_metrics` and three
  unused warning constants). It duplicated the tested `portfolio.py`,
  was imported nowhere, and its correlation function needed `scipy` plus
  a bare `except:`.
- Nine unwired modules that no product path and no test imported
  (2,317 lines). Each was either a duplicate of a tested module, a
  re-statement of a markdown document, or non-functional; every decision
  and its evidence is recorded in
  `docs/en/developers/unwired-modules-audit.md`:
  `benchmarking.py` (42), `live_monitoring.py` (62, non-functional),
  `research_notebooks.py` (54), `capital_protection.py` (61),
  `working_method.py` (70), `development_phases.py` (69, raised
  `KeyError`), `infrastructure/performance.py` (13),
  `ui/charts/qt_websocket_client.py` (4.2) and
  `machine_learning/strategies.py` (48).
  `ROADMAP.md` §4.4 item 3 was corrected accordingly.
- `research_ethics.py` (chapter 72), after merging its checker into
  `reporting/ethics.py`. The unused `EvidenceLevel`, `EvidenceLabel`,
  `generate_evidence_label`, `format_evidence_label`,
  `WarningType` and `EthicalWarning` were dropped instead of carried over
  as dead weight; the evidence ladder already lives in
  `reporting/report.py` and `ui/research/validity.py`.
- `risk_of_ruin.py` (chapter 60), after merging its Kelly sizing into
  `backtesting/robustness.py`. Its closed-form ruin formulas
  (`risk_of_ruin_binomial`, `risk_of_ruin_diffusion`),
  `capital_depletion_path` and `sequential_risk_of_ruin` were **not**
  ported: they mix units, multiply a per-trade expectancy by 100/50 and
  present it as an "expected/median drawdown", or return 0/1 while claiming
  to be a probability. The Monte-Carlo estimate that already exists is more
  defensible.
- The whole `exchanges/coinbase/` package (chapter 26.3): the native
  adapter and its endpoint config. Nothing imported either; the WebSocket
  client was a placeholder, `stop()` was declared twice so the synchronous
  definition silently overrode the async one, and the REST path recorded
  circuit-breaker *successes before the request*, so the breaker could never
  open. `ROADMAP.md` §26.3 and `docs/en/developers/live-trading-roadmap.md`
  were corrected to state that Coinbase is **not implemented**; the sandbox
  warning the config carried is preserved in the roadmap text.


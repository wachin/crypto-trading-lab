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

### Fixed

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
- `machine_learning/strategies.py`: removed an unused `scipy` import
  (`scipy` is not a declared dependency), fixed a `NameError` in
  `evaluate_ensemble()` (`report` → `performance`) and merged the two
  `__all__` definitions that silently hid half the public names.
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
- Documented test baseline corrected to **630 passed, 2 skipped**
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


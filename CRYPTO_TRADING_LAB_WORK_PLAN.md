# CONTINUATION PLAN — Crypto Trading Lab

This file accompanies the corrected `ROADMAP.md`. The goal is to provide the development agent with a clear workflow and prevent the misconception that the only remaining task is packaging.

## 0. Working Rule

For each task:

1. Read the corresponding chapter in `ROADMAP.md`.
2. Inspect the existing code and tests.
3. Implement only what is necessary to meet the requirement.
4. Add or update tests.
5. Run the relevant tests.
6. Run the full suite when appropriate.
7. Update `ROADMAP.md` only with actual evidence.
8. If something is partially implemented, use `[~]`; do not mark `[x]` prematurely.

## 1. Immediate Block: Establishing the Baseline

- [ ] Run the full suite and record the actual result.
- [ ] Confirm the actual number of passed/failed/skipped tests.
- [ ] Confirm that the README does not state a test count that is no longer accurate.
- [ ] Verify that the project starts up from a clean environment according to the repository instructions.
- [ ] Identify any import, dependency, or startup failures before proceeding with development.

## 2. Pending Functional Block

Prioritize the chapters that the ROADMAP itself leaves partially open and that affect the validity of the lab:

- [ ] Chapter 29 — Data quality.
- [ ] Chapter 33 — Strategies.
- [ ] Chapter 34 — Visual strategy builder.
- [ ] Chapter 35 — Strategy complexity control.
- [ ] Chapter 37 — Backtesting: finalize quality controls and ensure no look-ahead bias.
- [ ] Chapter 39 — Parameter optimization.
- [ ] Chapter 48 — Machine learning as an optional and reproducible capability. - [ ] Chapter 49 — AFML, maintaining its research-tier capabilities.
- [ ] Chapter 52 — Research experiment manager.
- [ ] Chapter 54 — Research notebooks.
- [ ] Chapter 55 — AI research assistant.
- [ ] Chapter 57 — Paper trading, especially the capabilities that remain pending.
- [ ] Chapter 58 — Risk manager.
- [ ] Chapter 59 — Emergency kill switch.
- [ ] Chapter 60 — Risk of ruin.
- [ ] Chapter 62 — Live monitoring.
- [ ] Chapter 64 — Strategy failure detection.
- [ ] Chapter 66 — Strategy qualification.
- [ ] Chapter 67 — Safety gates.

**Important dependency:** do not implement an advanced layer merely to make it appear that a chapter is finished. When another chapter is a dependency that is still incomplete, retain the partial state and document the dependency.

## 3. Data and reproducibility

- [ ] Complete the pending parts of Chapter 73.
- [ ] Resolve historical data acquisition from a second source where applicable.
- [ ] Complete dataset identity/version/checksum details where Chapter 29 requires them.
- [ ] Verify that each experiment can be reconstructed using its metadata.
- [ ] Run determinism and reproducibility tests.

## 4. Scientific validation

- [ ] Jointly review Chapters 38, 39, 43, 44, 45, and 49.
- [ ] Verify that no descriptive results are presented as validated evidence.
- [ ] Verify that warnings regarding small sample sizes, multiple testing, overfitting, and OOS performance appear where appropriate.
- [ ] Verify that liquidity/market impact remains marked as unaddressed as long as no actual model exists.
- [ ] Verify that research conclusions are linked to an identifiable experiment. ## 5. Operational safety

Before considering any trading flow complete:

- [ ] Complete chapter 58.
- [ ] Complete chapter 59.
- [ ] Complete chapter 62.
- [ ] Complete chapter 64.
- [ ] Complete chapter 66.
- [ ] Complete chapter 67.
- [ ] Confirm that live mode remains disabled until ROADMAP conditions are met.
- [ ] Verify that no alternative path can bypass the RiskManager or Safety Gates.

## 6. Learning Center

- [ ] Review pending tasks for chapter 23.
- [ ] Confirm that existing lessons match the README description.
- [ ] Complete examples, quizzes, progress tracking, screen links, and the initial path as required by chapter 23.
- [ ] Keep education, research, and actual trading operations separate.

## 7. English documentation

Documentation is a distinct phase; it should not be considered complete simply because a Learning Center exists.

### 7.1 Developer documentation

- [ ] `docs/en/developers/debian-packaging.md`
- [ ] `docs/en/developers/debian-dependencies.md` — exists; review against requirements.
- [ ] `docs/en/developers/exchange-adapters.md`
- [ ] `docs/en/developers/backtesting-methodology.md`
- [ ] `docs/en/developers/risk-management.md`
- [ ] `docs/en/developers/data-formats.md`
- [ ] `docs/en/developers/i18n.md`
- [ ] `docs/en/developers/threat-model.md` — exists; review against requirements.
- [ ] `docs/en/developers/reference-projects.md` — exists; review against requirements. - [ ] `docs/en/developers/translation-workflow.m
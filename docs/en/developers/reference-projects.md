# Reference projects — study conclusions

This document records the conclusions of studying the repositories under `external/`, as required by `ROADMAP.md` Chapter 25 (Reference projects) and Chapter 49.9 (Research code references).

Notation: `Ch. N` refers to a roadmap chapter, `N.x` to a roadmap section. "Book" refers to *Advances in Financial Machine Learning* (Marcos López de Prado, Wiley, 2018). The book is the conceptual authority in any dispute between implementations; it must be cited in documentation.

Status legend: **done** (study concluded, conclusions below) · **pending** (study not yet concluded).

| Reference | Path | Roadmap pointers | Status |
|---|---|---|---|
| AFML exercises | `external/adv-financial-ml-marcos-exercises` | Ch. 29, 38, 43–50 | **done** (Part A) |
| Backtrader | `external/backtrader` | Ch. 37 | **done** (Part B) |
| CCXT | `external/ccxt` | Ch. 26 | **done** (Part D) |
| Freqtrade | `external/freqtrade` | Ch. 33, 39, 57 | pending |
| Hummingbot | `external/hummingbot` | Ch. 56, 26 | pending |
| Jesse | `external/jesse` | Ch. 43–50 | pending |
| TA-Lib | `external/ta-lib` | Ch. 31 | pending |
| VectorBT | `external/vectorbt` | Ch. 37, 45 | **done** (Part C) |
| AFML book exhibit compilation | local reference copy (not in this repository) | Ch. 43–50, 47.4 | **inventoried** (A.9) |

---

# Part A — AFML(Advances in Financial Machine Learning) exercise repository (`external/adv-financial-ml-marcos-exercises`)

## A.1 The reference at a glance

| Property | Value |
|---|---|
| Upstream | https://github.com/fernandodelacalle/adv-financial-ml-marcos-exercises |
| License | MIT (© 2021 Fernando) — code may be adapted with attribution, after review and testing |
| Content | Author's solutions to the book's exercises + the book's own code snippets (`src/snippets/`) |
| Language stack | Python 3.6-era: pandas 0.23.4, numpy 1.15.0, scikit-learn 0.19.2, scipy 1.1.0, pyarrow 0.9.0 |
| Tests / type hints | none — research-notebook quality throughout |

**Key structural fact:** the *snippet files* cover considerably more of the book than the *notebooks* do. Several techniques (notably purged cross-validation and the whole labeling suite) have complete, verbatim book code in `src/snippets/` while their exercise notebooks are empty stubs. Conversely, some roadmap-relevant techniques are absent from the repository entirely (fractional differentiation, PBO, DSR/PSR, CPCV) and must be implemented from the book.

**Second reference — the book's own exhibits.** The developer also holds the book's exhibit compilation as a local reference copy, outside this repository (see A.9). It contains **all 97 book snippets** — including the ones this repository lacks — plus the book's equations, figures and tables, though it is *not* the full book text. A.9 inventories it; the per-technique specifications that turn its exhibits into implementable requirements live in `docs/en/developers/afml-techniques.md`.

## A.2 Coverage status by book chapter

| Book chapter / topic | Notebook | Snippet code | Coverage |
|---|---|---|---|
| 2. Financial data structures (bars, CUSUM) | `ch2.ipynb` — rich (64 cells) | `src/snippets/ch2.py`, `features/bars.py` | **strong** |
| 3. Labeling (triple-barrier, meta-labeling) | `ch3.ipynb` — partial (20 cells; 3.1 started, 3.2–3.5 headers only) | `src/snippets/ch3.py` — complete suite (3.1–3.8) | **strong (code), weak (worked examples)** |
| 4. Sample weights by uniqueness | `ch4.ipynb` — empty stub (1 cell, mislabeled title) | none | **absent** |
| 5. Fractionally differentiated features | `ch5.ipynb` — empty stub | none | **absent** |
| 6. Ensemble methods | `ch6.ipynb` — partial (9 cells; Snippet 6.1 only) | none | **weak** |
| 7. Cross-validation in finance (purging, embargo) | `ch7.ipynb` — mostly empty (imports only) | `src/snippets/ch7.py` — complete suite (7.1–7.4) | **strong (code), no worked examples** |
| 8. Feature importance (MDI, MDA, SFI, PCA) | `ch8.ipynb` — rich (14 cells, MDI/MDA/SFI runs + plots) | `src/snippets/ch8.py` — complete suite (8.2–8.8) | **strong** |
| 9. Hyper-parameter tuning | `ch9.ipynb` — empty stub | none | **absent** |
| 10. Bet sizing | — | none | **absent** |
| 11–12. Backtest statistics, PBO/CSCV, CPCV | — | none | **absent** |
| 14. Backtest statistics (PSR, DSR) | — | none | **absent** |
| 17–18. Structural breaks, entropy features | — | only CUSUM (Snippet 2.4) | **mostly absent** |
| 20. Multiprocessing | — | `src/snippets/ch20.py` — complete suite (20.5–20.10) | **strong** |
| Data preparation (Kibot tick data, MAD outliers) | `data_load_and_clean.ipynb` (18 cells) | `data/clean_data.py` | **didactic** |

> This table covers the *exercise repository only*. Rows marked **absent** are absent from that repository — not from the project. For each of them the book's own exhibit compilation supplies the snippet or equation (see A.9), and `afml-techniques.md` records the resulting specification.

## A.3 Technique-to-exercise mapping (roadmap → reference)

This is the operative table for implementers. "Adoption" follows the roadmap rule that adapted code must be reviewed against the book's definitions and tested before merging (Ch. 49.9). Status values: **usable reference** = code exists in the exercise repository; **absent in repo, exhibits available** = the book's snippet or equation is available in the local exhibit compilation (A.9) and the technique is specified in `afml-techniques.md`; **absent** = neither code nor formula is available locally.

| Roadmap section | Technique | Where in the reference | Status | Adoption guidance |
|---|---|---|---|---|
| 29.1, 49.1 | Tick / volume / dollar bars | `features/bars.py` (`tick_bar`, `volume_bar`, `dollar_bar`, `volume_bar_cum`, `dollar_bar_cum`); `ch2.ipynb` exercise 2.1(a)–(e): bar counts, serial correlation, monthly variance, Jarque-Bera | usable reference | Reimplement with vectorized cumulative thresholds; the notebook's statistical comparisons (2.1b–e) are a ready-made acceptance-test template |
| 29.1, 49.1 | Dollar *imbalance* bars | `ch2.ipynb` cell "implement dollar imbalance bars" (exercise 2.2) | attempt only, incomplete | Implement from the book's chapter 2; do not treat the notebook cell as a correct reference |
| 49.2 | Triple-barrier labeling | `src/snippets/ch3.py`: `applyPtSlOnT1` (Sn. 3.2), `addVerticalBarrier` (Sn. 3.4), `getEvents` (Sn. 3.3); `ch3.ipynb` 3.1 | usable reference | Verify intrabar-ambiguity handling against Ch. 37.5 (the book's snippet evaluates barrier touches on the close path; document that choice explicitly) |
| 49.2 | Dropping rare labels | `src/snippets/ch3.py`: `dropLabels` (Sn. 3.8) | usable reference | Wire into the labeling pipeline as an explicit, recorded step |
| 49.3 | Sample weights by uniqueness | no repo code; book ch. 4 exhibits: Sn. 4.1–4.11 (the compilation, pp. 35–44), Eq. 32 | **absent in repo**, exhibits available | Specified in `afml-techniques.md` §3.1; port with vectorized interval counting |
| 49.4 | Purging of overlapping training observations | `src/snippets/ch7.py`: `getTrainTimes` (Sn. 7.1) | usable reference | Port with unit tests on interval-overlap edge cases |
| 49.4 | Embargo | `src/snippets/ch7.py`: `getEmbargoTimes` (Sn. 7.2) | usable reference | Same; embargo length must become an explicit parameter (Ch. 49.4) |
| 49.4 | Purged K-Fold CV class | `src/snippets/ch7.py`: `PurgedKFold` (Sn. 7.3), `cvScore` (Sn. 7.4) | usable reference | The central CV component for Ch. 49.4/38.8; verify against the book's definition before merging |
| 45.3 | Combinatorial purged CV (CPCV) | no repo code; book ch. 12 exhibits: Eq. 39–44 (the compilation, pp. 96–99), Figs. 12.1–12.2 | **absent in repo**, equations available | Specified in `afml-techniques.md` §3.4; build on `PurgedKFold`; count paths and disclose data re-use (Ch. 45.3) |
| 49.5 | Probabilistic Sharpe ratio (PSR) | no repo code; book ch. 14 exhibit: Eq. 52 (the compilation, p. 126) | **absent in repo**, formula available | Specified in `afml-techniques.md` §3.5; requires recorded skewness/kurtosis/sample length |
| 49.5 | Deflated Sharpe ratio (DSR) | no repo code; compilation Eq. 53 (p. 127) + primary paper Eqs. 1–2 | **absent in repo**, specified | Specified in `afml-techniques.md` §3.6 from Bailey & López de Prado (2014); requires the trial count (Ch. 49.5: no trial count → no deflated estimate) |
| 49.6 | PBO via CSCV | no repo code; compilation Figs. 11.1–11.2 (p. 94) + primary paper Algorithm 2.3 | **absent in repo**, specified | Specified in `afml-techniques.md` §3.7 from Bailey, Borwein, López de Prado & Zhu (Algorithm 2.3); combine with the optimization trial records of Ch. 39 |
| 48.1, 48.3 | Hyper-parameter tuning with purged CV | no repo code; book ch. 9 exhibits: Sn. 9.1–9.4 (the compilation, pp. 79–82) | **absent in repo**, exhibits available | Specified in `afml-techniques.md` §3.8; requires scikit-learn (Ch. 4.0 STOP procedure) |
| 49.8, 58 | Bet sizing from probabilities (+ limit price) | no repo code; book ch. 10 exhibits: Sn. 10.1–10.4 (the compilation, pp. 87–91) | **absent in repo**, exhibits available | Specified in `afml-techniques.md` §3.9; research-tier only, must pass the risk manager (Ch. 58) |
| 49.7 | MDI feature importance | `src/snippets/ch8.py`: `featImpMDI` (Sn. 8.2); `ch8.ipynb` | usable reference | Tree-ensemble only; run within purged CV, never plain K-Fold |
| 49.7 | MDA feature importance | `src/snippets/ch8.py`: `featImpMDA` (Sn. 8.3); `ch8.ipynb` | usable reference | Score on purged/embargoed splits; report uncertainty |
| 49.7 | Single-feature importance (SFI) | `src/snippets/ch8.py`: `auxFeatImpSFI` (Sn. 8.4); `ch8.ipynb` | usable reference | — |
| 49.7 | Clustered / orthogonalized importance | `src/snippets/ch8.py`: `get_eVec` + `orthoFeats` (Sn. 8.5), `kendal_weighted` (Sn. 8.6) | usable reference | Supports the roadmap rule that correlated feature clusters distort single-feature importance (Ch. 49.7) |
| 49.8 | Meta-labeling events/bins | `src/snippets/ch3.py`: `getEvents` (Sn. 3.6), `getBins` (Sn. 3.7) | usable reference | Meta-label output remains a research signal candidate; never bypasses 33.6 |
| 47.4 | Symmetric CUSUM filter (structural breaks/events) | `src/snippets/ch2.py`: `getTEvents` (Sn. 2.4) | usable reference | Threshold `h` must be a recorded parameter |
| 47.4 | Structural-break tests (SADF/GSADF, CUSUM on residuals) | no repo code; book ch. 17 exhibits: Sn. 17.1–17.4 (the compilation, pp. 164–165), §17.3 (p. 156) | **absent in repo**, exhibits available | Specified in `afml-techniques.md` §3.10; minimum sample length, deterministic terms and lag order are recorded parameters |
| 47.4 | Fractional differentiation | no repo code; book ch. 5 exhibits: Sn. 5.1–5.4 (the compilation, pp. 48–53), Table 5.1 | **absent in repo**, exhibits available | Specified in `afml-techniques.md` §3.2; differentiation order `d` must be recorded (Ch. 47.4) |
| 47.4 | Entropy features | no repo code; book ch. 18 exhibits: Sn. 18.1–18.4 (the compilation, pp. 168–172) | **absent in repo**, exhibits available | Specified in `afml-techniques.md` §3.11; document the quantization scheme |
| 50 | Ensembles (bagging theory) | `ch6.ipynb` (Snippet 6.1 bagging accuracy, exercise 6.1 discussion) | weak reference | Ensemble design follows Ch. 50; this reference only illustrates bagging variance reduction |
| 10 | Multiprocessing framework | `src/snippets/ch20.py`: `mpPandasObj` (Sn. 20.7) and helpers (20.5–20.10) | usable reference | Concept/design reference for parallel research jobs; the app's own background processing follows Ch. 12 |
| 29 | Data cleaning (MAD outliers, tick-data preparation) | `data_load_and_clean.ipynb`, `data/clean_data.py`: `mad_outlier` | didactic reference | Informs Ch. 29 policies; the notebook works on Kibot E-mini/IVE and WDC tick files, not crypto data |

## A.4 Notebook inventory (what each actually contains)

- `ch2.ipynb` — 64 cells. Loads cleaned IVE tick data; builds minute/tick/volume/dollar bars; the full exercise 2.1 battery: weekly bar counts, return autocorrelation per bar type, monthly variance-of-variance, Jarque-Bera normality; dollar imbalance bar attempt (2.2); Bollinger-band crossings on dollar bars (2.4); 2.5 stub.
- `ch3.ipynb` — 20 cells. Daily volatility (`getDailyVol`), dollar bars, triple-barrier events on one day of data; exercises 3.2–3.5 are header-only.
- `ch4.ipynb`, `ch5.ipynb`, `ch9.ipynb` — title cells only. **No content.**
- `ch6.ipynb` — 9 cells. Exercise 6.1 discussion placeholder; Snippet 6.1 (bagging classifier accuracy) via `scipy.special.comb`.
- `ch7.ipynb` — 10 cells. Imports `getTrainTimes`; no worked exercises.
- `ch8.ipynb` — 14 cells. Synthetic dataset (Sn. 8.7); MDI, MDA, and SFI runs with the author's own Snippets 8.8–8.10 helper and plots.
- `data_load_and_clean.ipynb` — 18 cells. Kibot tick-data ingestion, MAD outlier filtering, parquet output; used to produce the `clean_IVE_tickbidask.parq` the other notebooks load.

## A.5 Snippet-file inventory (verbatim book code)

| File | Functions / classes | Book snippets |
|---|---|---|
| `src/snippets/ch2.py` | `getTEvents` | 2.4 (symmetric CUSUM filter) |
| `src/snippets/ch3.py` | `getDailyVol`, `applyPtSlOnT1`, `getEvents`, `addVerticalBarrier`, `getBinsOld`, `getBins`, `dropLabels` | 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 3.8 |
| `src/snippets/ch7.py` | `getTrainTimes`, `getEmbargoTimes`, `PurgedKFold`, `cvScore` | 7.1, 7.2, 7.3, 7.4 |
| `src/snippets/ch8.py` | `featImpMDI`, `featImpMDA`, `auxFeatImpSFI`, `get_eVec`, `orthoFeats`, `kendal_weighted`, `getTestData`, `featImportance` | 8.2–8.8 |
| `src/snippets/ch20.py` | `linParts`, `nestedParts`, `mpPandasObj`, `processJobs_`, `reportProgress`, `processJobs`, `expandCall` | 20.5–20.10 |
| `src/data/clean_data.py` | `mad_outlier` | chapter 3 exercise material |
| `src/features/bars.py` | `tick_bar`, `volume_bar`, `dollar_bar`, `volume_bar_cum`, `dollar_bar_cum` | author's own implementation (not verbatim book code) |
| `src/visualization/candle.py` | `plot_candlestick_ohlc` | plotting helper |

## A.6 Code-quality review (blocking issues for direct reuse)

- **pandas 0.23 idioms.** `bars.py` mutates slices (`volume_bar.loc[idx, 'cum_vol'] = ...` on a filtered frame) — under modern pandas this raises `SettingWithCopyWarning` and can silently misbehave. Any port must operate on explicit copies.
- **Python-loop bar construction.** `volume_bar`/`dollar_bar` accumulate in O(n) Python loops. Fine didactically; must be vectorized (cumsum + searchsorted) for production datasets.
- **No tests, no type hints, no package metadata.** The repo is a notebook companion, not a library. Adapted code must enter this project's test suite (Ch. 14) with provenance comments.
- **Close-path barrier evaluation.** The book's `applyPtSlOnT1` evaluates barriers on close prices. That is a legitimate but consequential simplification; Ch. 49.2 requires documenting whether high/low paths or close-only paths are used, and Ch. 37.5 intrabar-ambiguity rules apply.
- **Stack vintage.** Python 3.6 / pandas 0.23 / sklearn 0.19 APIs differ from the project's target stack; assume API migration work in every port.

## A.7 Gaps that require original implementation

The exercise repository does **not** cover: sample weights by uniqueness (book ch. 4), fractional differentiation (ch. 5), hyper-parameter tuning with purged CV (ch. 9), bet sizing (ch. 10), PBO/CSCV (ch. 11–12), CPCV (ch. 12), PSR/DSR (ch. 14), structural-break tests (ch. 17), and entropy features (ch. 18). Each is mapped to a roadmap section in A.3.

The book's own exhibit compilation (A.9) narrows the gap: it supplies the code snippets for chs. 4, 5, 9, 10, 17 and 18, and the equations for chs. 12 and 14. It does **not** supply the book's prose definitions; where those were missing, the technique was specified from its **primary paper** instead — DSR and PBO/CSCV are now unblocked this way (see `afml-techniques.md` §3.6–§3.7 and its §5 references list); PBO/CSCV in particular is built on the published CSCV algorithm rather than on the book's chapter, whose prose is not in the compilation.

For every technique in this list the implementation must be written from the specification in `docs/en/developers/afml-techniques.md` (our own definitions, exhibit pointers, mandatory parameters and open questions) and reviewed against the printed book (Ch. 49.9), which is cited as authority and never redistributed.

## A.8 Verification checklist before adopting any code from this repository

- [ ] The adapted function reproduces the book's snippet definition (line-level review, not just behavioral similarity).
- [ ] Unit tests cover the edge cases relevant to the roadmap section (interval overlap and embargo boundaries for Ch. 49.4; intrabar ambiguity for Ch. 49.2; NaN handling everywhere).
- [ ] The port passes the project's lint and test suite on the target stack.
- [ ] Provenance is recorded: source file and snippet number in the docstring, and the technique-to-reference mapping in A.3 updated if needed.
- [ ] MIT license attribution is preserved where code, not just ideas, is taken.
- [ ] The roadmap checklist item that required the study (Ch. 25) is checked for this repository.

## A.9 The book's exhibit compilation (local reference)

One-off inventory taken 2026-09-13; the method and the per-technique
consequences are recorded in `afml-techniques.md` §1.

The compilation is a local reference copy held by the developer, **outside this
repository**; it is not tracked and never will be. Only its structure is
recorded here, not the file itself.

| Property | Value |
|---|---|
| Source | the book's exhibit compilation (local reference copy, not in this repository) |
| Pages | 218 |
| Structure | pp. 1–10 = *List of Exhibits* (tables, figures, equations, snippets + page); pp. 11–218 = the exhibits grouped by chapter (`c01`–`c22`) |
| Content | **all 97 book snippets**, plus the book's equations, figures and tables |
| Narrative | fragments only (≈20,600 words in the body, median 69 words/page, 75 of 209 body pages under 50 words) — **this is not the full book** |

Page pointers for the roadmap-relevant chapters:

| PDF chapter | Topic | Key exhibits |
|---|---|---|
| c02 | Financial data structures, CUSUM filter | Table 2.1; Figs. 2.1–2.3; Sn. 2.1–2.4 (pp. 21–23) |
| c03 | Labeling, meta-labeling | Sn. 3.1–3.8 (pp. 26–34); Figs. 3.1–3.2 |
| c04 | Sample weights / uniqueness | Sn. 4.1–4.11 (pp. 35–44); Eq. 32; Figs. 4.1–4.3 |
| c05 | Fractional differentiation | Sn. 5.1–5.4 (pp. 48–53); Table 5.1; Figs. 5.1–5.5 |
| c07 | Cross-validation in finance | Sn. 7.1–7.4 (pp. 63–67); Figs. 7.1–7.3 |
| c08 | Feature importance | Sn. 8.2–8.10 (pp. 68–76); Figs. 8.1–8.4 |
| c09 | Hyper-parameter tuning | Sn. 9.1–9.4 (pp. 79–82) |
| c10 | Bet sizing | Sn. 10.1–10.4 (pp. 87–91); Figs. 10.1–10.3 |
| c11 | Dangers of backtesting (PBO) | Figs. 11.1–11.2 only (p. 94) — **no formula, no code** |
| c12 | Backtesting through CV (CSCV/CPCV) | Eq. 39–44 (pp. 96–99); Figs. 12.1–12.2 |
| c13–c14 | Backtest statistics | Sn. 13.1–13.2 (p. 103); Sn. 14.1–14.4 (pp. 120–124); Eq. 45–53; Table 14.1 |
| c17 | Structural breaks | Sn. 17.1–17.4 (pp. 164–165); §17.3 (p. 156); Eq. 59–66 |
| c18 | Entropy features | Sn. 18.1–18.4 (pp. 168–172); Eq. 67–89 |
| c20 | Multiprocessing and vectorization | Sn. 20.1–20.14 (pp. 187–199) |

Rules: the compilation is a local reference only — **never commit or
redistribute it**; page pointers refer to that copy and to the book's own
exhibit numbering; the per-technique requirements derived from these exhibits
live in `afml-techniques.md`.

---

# Part B — Backtrader (`external/backtrader`)

## B.1 The reference at a glance

| Property | Value |
|---|---|
| Path / upstream | `external/backtrader` · https://github.com/mementum/backtrader |
| License | **GPLv3** — the strictest of all references. Design inspiration only; **no code adaptation** (contrast: the AFML exercises are MIT) |
| Version | 1.9.78.123; last upstream commit 2023-04-19 — stable but effectively in maintenance mode |
| Architecture | Event-driven engine: `Cerebro` orchestrator + strategies + simulated broker + feeds + analyzers/observers + metaclass/lines machinery |
| Tests | Extensive per-indicator and comparison tests under `tests/` — a useful model for Ch. 14 |

## B.2 What maps to which roadmap chapter

### Backtesting engine (Ch. 37) — the core value of this study

- **Broker simulation** (`backtrader/brokers/bbroker.py`, ~1,240 lines): cash/value accounting, order acceptance checks (cash/margin before submission), order states including `Margin` and `Rejected` (`backtrader/order.py`), short-cash policy (`shortcash`). Direct conceptual input for 37.1 (capital and trading costs) and the order/trade domain models of Ch. 7.
- **Order types** (`order.py`): `Market, Close, Limit, Stop, StopLimit, StopTrail, StopTrailLimit, Historical` — covers 37.3 and adds trailing orders beyond the MVP set.
- **Slippage model**: `slip_perc`, `slip_fixed`, `slip_match` (cap at bar extremes), `slip_out` (allow fills outside the high–low range); configured via `set_slippage_perc` / `set_slippage_fixed`. This is a clean, parameterized cost model — exactly the shape 37.1 and 44.3 (cost sweeps) need.
- **Volume-constrained fills** (`backtrader/fillers.py`): `FixedSize`, `FixedBarPerc`, `BarPointPerc` fill only a fraction of the bar's volume. The seed for the liquidity/liquidity-slice model of 56.4.
- **Commission schemes** (`comminfo.py`, `commissions/`): `CommInfoBase` with fixed/percentage commission, stocklike/futures attributes, margin, interest, leverage. See B.4 for what crypto still needs on top.
- **Intrabar execution policy**: fills are evaluated against bar OHLC with fixed matching rules. Our Ch. 37.5 intrabar-ambiguity requirements must go further: Backtrader's policy is implicit, ours must be explicit and documented.
- **Caution — look-ahead shortcuts**: Cerebro supports *cheat-on-close/cheat-on-open* execution and strategies expose `next_open`. These deliberately break the decide-on-bar-close realism. The app must never enable such modes in evidence-producing runs (Ch. 43.5); at most, didactic comparisons with explicit labeling.

### Performance metrics and reporting (Ch. 40–42)

- **Analyzer pattern** (`analyzer.py`): hooks `next`, `notify_order`, `notify_trade`, `notify_cashvalue`/`notify_fund` + `get_analysis`. Analyzers observe the same event stream as strategies — a clean separation the roadmap's metrics chapter can adopt (metrics as observers of the backtest, not post-hoc report hacks).
- **Analyzer suite** (`analyzers/`): `annualreturn`, `calmar`, `drawdown`, `leverage`, `logreturnsrolling`, `periodstats`, `positions`, `pyfolio`, `returns`, `sharpe`, `sqn`, `timereturn`, `tradeanalyzer`, `transactions`, `vwr`. Direct menu for Ch. 40.1–40.4.
- **Observers** (`observers/`): live chart overlays — `broker` (cash/value), `buysell`, `drawdown`, `trades`, `timereturn`, `logreturns`, and **`benchmark` (buy-and-hold comparison)** — the last one is the conceptual seed for Ch. 42 inside the engine, not just in reports.
- **Sizers** (`sizers/`): `fixedsize`, `percents_sizer` — position-sizing hooks. Only two trivial stock-world sizers; crypto sizing per Ch. 58 is our own work.

### Data feeds, resampling, replay (Ch. 26, 28–29)

- **Feed abstraction** (`feed.py`, `feeds/`): `csvgeneric`, `btcsv`, `pandafeed`, `influxfeed`, `quandl`, `yahoo`, IB/Oanda/VirtualChart stores; a filter pipeline (`filters/`, `resamplerfilter.py`) between raw input and engine.
- **Resampling and replay** (`cerebro.resampledata` / `replaydata`; `Resampler`, `Replayer`, `DTFaker`): replay progressively refines the current bar intrabar — conceptually valuable for simulating lower-timeframe execution on higher-timeframe backtests (37.6), with the same intrabar-ambiguity caveats.
- **Multi-timeframe chaining** (`feeds/chainer.py`) and a trading calendar (`tradingcal.py`) + timers (`timer.py`). Caution: calendar/session concepts assume trading sessions; crypto trades 24/7 — the app must not inherit session assumptions (Ch. 29/31 documentation point).

### Parameter optimization (Ch. 39)

- `Cerebro.optstrategy` + `multiprocessing.Pool(maxcpus)` + `optreturn` (stripped result objects to survive large sweeps) + `exactbars` (memory control over long histories). A workable execution pattern — but Backtrader has **no** trial-record, objective-function, or overfitting-discipline concepts; those come from Ch. 39, 43, 44, 49.

## B.3 What Backtrader does **not** provide (verified by search)

- No walk-forward, Monte Carlo, purged CV, or robustness tooling (repo-wide search negative) — Chapters 43–49 are fully our own work.
- No crypto-specific execution: no maker/taker fee distinction, no minimum-order quantity/value rules, no exchange-rule model (Ch. 30, 37.2, 55).
- No paper-trading persistence, no risk manager, no kill-switch concept (Ch. 57–59).
- No regime analysis, no feature/ML infrastructure (Ch. 46–49).

## B.4 Adoption guidance

- [ ] **GPLv3 constraint**: design inspiration and terminology only — zero code adaptation; do not vendor or link any Backtrader code into the application.
- [ ] Where the analyzer/observer pattern is adopted, implement it from the roadmap's own specification (original code, own tests).
- [ ] Design the liquidity model (56.4) from the *concept* of the fillers; extend with partial fills, maker/taker fees, and exchange rules Backtrader lacks.
- [ ] Treat cheat-on-close/cheat-on-open as forbidden in evidence-producing runs; if ever implemented for teaching, mark outputs as non-evidence (43.5).
- [ ] Maintenance mode ⇒ pin exact reference commit in this document when concepts are adopted; re-verify on any submodule update.
- [ ] Record every adopted *idea* (not code) in this document and in the relevant roadmap chapter.

---

# Part C — VectorBT (`external/vectorbt`)

## C.1 The reference at a glance

| Property | Value |
|---|---|
| Path / upstream | `external/vectorbt` · https://github.com/polakowo/vectorbt |
| License | **Apache 2.0 with Commons Clause** ("Fair Code"). Use and modification are permitted with attribution and notice preservation, but the license does **not** grant the right to *Sell* — to charge for a product or service whose value derives substantially from VectorBT. Read `LICENSE.md` before any distribution decision. More permissive than Backtrader's GPLv3, but not unrestricted. |
| Version | 1.1.0; **actively maintained** (last commit 2026-08-02, commit `34b6d59`) |
| Architecture | Vectorized engine over numpy/pandas with numba JIT compilation: entire parameter grids are simulated in one call. The opposite paradigm to Backtrader's event loop — both are informative exactly because they differ |
| Stack requirements | pandas ≥ 3.0, numpy ≥ 2.4, numba ≥ 0.66 (llvmlite), plotly, scikit-learn; optional extras pull TA-Lib, ccxt, python-binance, alpaca-py, yfinance. Bleeding-edge requirements — Debian/PyPI availability must be verified per Chapter 4 |

## C.2 What maps to which roadmap chapter

### Backtesting and execution simulation (Ch. 37, 55)

- **`Portfolio.from_signals`** (`vectorbt/portfolio/base.py`): signal-driven simulation with broadcastable per-column parameters: `size`, `size_type`, `fees`, `fixed_fees`, `slippage`, `allow_partial`, `raise_reject`, `upon_opposite_entry`, `direction`, `val_price`, `init_cash`, `call_seq`, `group_by`. The parameter surface matches the cost/constraint model of 37.1–37.3 well.
- **Native stop engine**: `sl_stop` (including trailing), `tp_stop`, `use_stops`, `stop_entry_price`, `stop_exit_price`. Useful complement to 49.2 barrier logic and stop-order handling; note that stop resolution paths are configurable and the intrabar-ambiguity rules of 37.5 remain our own to document.
- **`Portfolio.from_orders` / `from_order_func`**: order-level and low-level order-loop constructors — a bridge toward the execution realism of Ch. 55 without abandoning vectorization.
- **Trade and drawdown records**: `Records` (`vectorbt/records/base.py`), `EntryTrades`/`ExitTrades`/`Positions` (`portfolio/trades.py`), and `Drawdowns` (`generic/drawdowns.py`, per-event depth/timing records). First-class trade records are exactly what 40.2 needs; drawdown *events* are richer than a single max-drawdown number (40.3).

### Performance metrics and statistical evaluation (Ch. 40, 43, 49.5)

- **Metrics registry pattern** (`vectorbt/returns/metrics.py` + `generic/stats_builder.py`): named, documented metric functions surfaced through a `.stats()` builder. This is the pattern to mirror for Ch. 40's metric catalog.
- **Native `deflated_sharpe_ratio` and `approx_exp_max_sharpe`**: directly relevant to 49.5. Caveats: it is a normal-approximation implementation requiring `nb_trials` explicitly — good, because 49.5 demands recorded trial counts — but it must be validated against the book's definition before use (49.9). No probabilistic Sharpe ratio found; PSR stays an original implementation.

### Data splitting and walk-forward (Ch. 38, 45)

- **`vectorbt/generic/splitters.py`**: `RangeSplitter`, **`RollingSplitter` ("rolling walk-forward splitter")**, **`ExpandingSplitter` ("expanding walk-forward splitter")** — native walk-forward range generation matches Ch. 45's window mechanics.
- **No purging or embargo anywhere in the repository** (verified by search). The splitters are not leakage-safe for overlapping labels; 38.8/49.4 remain our own work (AFML's `PurgedKFold` is the reference). Any leakage-sensitive use requires a purge+embargo wrapper around these splitters.

### Feature engineering, labeling, signals, data (Ch. 31, 33, 47, 49)

- **`vectorbt/labels/generators.py`**: `FIXLB`, `MEANLB`, `LEXLB`, `TRENDLB`, `BOLB` label generators — useful baseline labels. No triple-barrier generator (no `PROLB`); 49.2 stays AFML-based.
- **`vectorbt/signals/generators.py`**: random entry/exit generators (`RAND`, `RANDX`, `RANDNX`, `RPROB`, `RPROBX`, `RPROBCX`, `RPROBNX`) and stop/exit generators (`STX`, `STCX`, `OHLCSTX`, `OHLCSTCX`). The random generators are ideal for the null-baseline comparisons Ch. 43 encourages.
- **`IndicatorFactory`** (`indicators/factory.py`) and `basic.py`: parameterized indicator classes with built-in grids, plotting, and stats — a strong pattern reference for the Ch. 31 indicator catalog and Ch. 47 feature catalog.
- **`vectorbt/data/custom.py`**: `YFData`, `BinanceData`, `CCXTData`, `AlpacaData`, plus `SyntheticData`/`GBMData` (synthetic GBM paths — useful for method validation and Monte Carlo-style studies under explicit assumptions).

### Parameter optimization (Ch. 39)

- The core paradigm *is* the optimization story: broadcasting parameter grids through the engine simulates thousands of configurations cheaply. Excellent for controlled grid experiments (39.1, 39.3) — but mass backtesting at near-zero cost amplifies exactly the multiple-testing risks that Ch. 43.2, 49.5, and 49.6 exist to control. Discipline must scale with capability.

## C.3 What VectorBT does **not** provide (verified by search)

- No purged/embargoed CV, no PBO/CSCV, no CPCV (repo-wide search negative).
- No Monte Carlo scenario framework (random signal generators exist, but no trade-reshuffling/scenario engine for 44.4).
- No meta-labeling, no sample-weight/uniqueness tooling (Ch. 49.3, 49.8).
- No GUI, no persistence, no paper-trading loop, no risk manager, no kill switch (Ch. 57–59) — notebook-centric by design.

## C.4 Adoption guidance

- [ ] **License discipline**: Apache 2.0 + Commons Clause permits using, studying, and adapting VectorBT inside the application, but forbids selling a product/service whose value derives substantially from it. Re-read `LICENSE.md` before any commercialization or paid-hosting decision; keep the Commons Clause notice in any attribution file.
- [ ] **Dependency reality check (Ch. 4)**: numba/llvmlite JIT toolchain and pandas ≥ 3.0 / numpy ≥ 2.4 are demanding. Verify Debian/PyPI availability before making VectorBT a runtime dependency; treat it as an optional research-tier dependency until proven.
- [ ] **Vectorized ≠ event-realistic**: use `from_orders`/`from_order_func` and the stop engine as inspiration, but the evidence rules (37.5, 37.7, 43.5) remain ours; document every close-path assumption.
- [ ] **Wrap splitters with purge+embargo (49.4) before leakage-sensitive use**; never use the raw walk-forward splitters with overlapping labels.
- [ ] **DSR**: adapting the metric is license-permitted, but validate against the book and keep trial records per 49.5.
- [ ] **Actively maintained**: pin the studied commit (`34b6d59`, 2026-08-02) here; re-verify conclusions on submodule updates.

---

# Part D — CCXT (`external/ccxt`)

## D.1 The reference at a glance

| Property | Value |
|---|---|
| Path / upstream | `external/ccxt` · https://github.com/ccxt/ccxt |
| License | **MIT** (© 2024 Igor Kroitor) — the most permissive of all references; study, use, and adapt with attribution preserved |
| Version | 4.5.77; **hyperactive maintenance** (last commit 2026-09-06 — the day of this study); multi-language monorepo (JS/PHP/Python/C#/Go generated from one metadata set) |
| Scale | 105 synchronous exchange classes, 77 `pro/` WebSocket classes, plus `async_support/` asyncio mirrors (`class binance(Exchange, ImplicitAPI)`) |
| Structure note (v4) | The unified abstract API lives in `python/ccxt/base/exchange.py` (142 unified `fetch_*`/`create_order`/`cancel_order` definitions); `python/ccxt/abstract/` now holds per-exchange description files. APIs move between releases — pin the studied commit and isolate CCXT behind our adapter |

## D.2 What maps to which roadmap chapter

### Exchange adapters and market data (Ch. 26) — the core value of this study

- **Unified API**: `fetch_markets`, `fetch_ohlcv` (+ `*_ws` variants), `fetch_balance`, `fetch_ticker`, `fetch_trades`, `fetch_order_book(s)`, `fetch_my_trades`, `create_order`, `cancel_order` — one interface across ~100 exchanges. This is the same shape as our `ExchangeAdapter` interface (26): CCXT is the leading candidate to become the *implementation behind* that interface rather than a parallel abstraction.
- **WebSocket layer** (`python/ccxt/pro/`): `watch_ticker(s)`, `watch_ohlcv(_for_symbols)`, `watch_order_book`, `watch_trades(_for_symbols)` verified on `pro/binance.py` — maps onto Ch. 26's subscription requirements (tickers, candles, trades, order book).
- **Binance Spot Testnet**: explicit `testnet.binance.vision` REST URLs built into `binance.py` — matches Ch. 26.2 exactly. Binance *futures* testnet URLs also exist and must remain unused (Ch. 26 forbids futures).
- **Coinbase**: `coinbase.py` (Advanced Trade-era class; `sandbox: False` observed — sandbox support is limited), `coinbaseexchange.py` (with `'test'` URL set), `coinbaseinternational.py`. Ch. 26.3's sandbox warning (static/predefined data) remains applicable; public market data first.
- **Error taxonomy** (`python/ccxt/base/errors.py`, 23 classes): `ExchangeError` → `AuthenticationError`, `InsufficientFunds`, `InvalidOrder`; `NetworkError` → `RateLimitExceeded`, `ExchangeNotAvailable`. Direct input for Ch. 27's state machine (map onto `AUTHENTICATING`, `RATE_LIMITED`, `ERROR`, `RECONNECTING`) and for Ch. 26 adapter error translation.
- **Rate limiting**: `enableRateLimit` (default `True`) with `throttle()` in `base/exchange.py`. Our adapters must keep this enabled and still surface `RATE_LIMITED` state explicitly (Ch. 27) rather than silently waiting.

### Market precision and exchange rules (Ch. 30) and costs (37.1, 55)

- **Precision machinery** (`base/exchange.py`, `decimal_to_precision`): `DECIMAL_PLACES`, `TICK_SIZE`, `SIGNIFICANT_DIGITS` modes; `price_to_precision`, `amount_to_precision`, `cost_to_precision`; per-market `precisionMode` (some exchanges use tick size, others decimal places). This is exactly the normalization problem Ch. 30 must own — adopt the *model* (three precision modes + per-market declaration), implementing in our domain or wrapping CCXT's.
- **Market structure**: per-market `limits` (amount/cost minima) and per-market `maker`/`taker` fees incl. tiered structures (verified in `binance.py`) — feeds 37.1, 37.2, and 55 (maker/taker distinction that Backtrader lacks).

### Where CCXT ends (verified by search)

- **No data-quality framework**: no dataset identity/versioning/checksums (Ch. 29 stays ours); fetched data must enter our dataset pipeline immediately.
- **No backtesting, paper-trading, risk, or qualification tooling** (Ch. 37, 57–59 ours); CCXT is a live-exchange integration library, not a research platform.
- **Historical-candle depth is exchange-dependent**: what `fetch_ohlcv` can retrieve varies per exchange and plan; bulk historical data needs our own import pipeline (Ch. 28).
- **Async model**: `async_support/` and `pro/` are asyncio-based; bridging into the Qt/background-processing architecture (Ch. 12) is a deliberate design task, not a drop-in.

## D.3 Adoption guidance

- [ ] **Adapter isolation**: never let CCXT types leak into the central domain (Ch. 26 rule); the `ExchangeAdapter` interface owns the boundary so CCXT can be upgraded or replaced.
- [ ] **Pin the studied commit** in this document; CCXT ships breaking structural changes between minor versions (v4 moved the abstract API) — re-verify on submodule updates.
- [ ] **Debian/PyPI check (Ch. 4)**: pure-Python package (no compiled extensions); packaging metadata lives under `python/`. Verified during this study: **no `python3-ccxt` package exists in Debian's apt sources** — the PyPI route (preferably in the app's isolated environment) is the only one; confirm the current CCXT version's Python requirement during the Chapter 4 evaluation. Until then treat as the reference implementation behind `MockExchange`-parallel adapters.
- [ ] **Feature-verification rule (Ch. 25)**: CCXT normalizes ~100 exchanges, but per-exchange quirks remain; verify each claimed capability (testnet endpoints, fee structure, precision mode) per exchange before relying on it.
- [ ] **Never enable the futures testnet**; spot-only scope is a roadmap rule (Ch. 26.2).
- [ ] **Credentials**: CCXT instances take API keys directly — instances may only be constructed inside the credential store boundary (Ch. 9), never from UI code.

---

# Part E — Remaining reference repositories (study pending)

These sections will be filled as each study concludes, per Chapter 25. Until then, the pointers in the status table above define what to inspect in each repository.

- [ ] **Freqtrade** — conclude the study of strategy/execution separation, dry-run mode, and hyperopt (Ch. 33, 39, 57 pointers).
- [ ] **Hummingbot** — conclude the study of execution and order-management design (Ch. 56, 26 pointers).
- [ ] **Jesse** — conclude the study of the research loop: backtest, optimization, Monte Carlo, significance testing, ML pipeline (Ch. 43–50 pointers); verify each claimed feature before recording it.
- [ ] **TA-Lib** — conclude the study of the indicator catalog and Debian packaging status of the Python wrapper (Ch. 31 pointers).

## Maintenance rules for this document

- [ ] Update A.3 whenever an implementation of a technique lands, noting the project module that fulfills it, and mirror the status change in `afml-techniques.md`.
- [ ] Keep the coverage table (A.2) in sync with the submodule commit recorded in the repository; re-verify on submodule updates.
- [ ] Keep A.9 in sync with `afml-techniques.md`; if the local compilation is replaced, re-verify the page pointers.
- [ ] Resolve the open questions recorded in `afml-techniques.md` before implementing the affected technique (Ch. 49.9).
- [ ] Never commit or redistribute the book — printed text or exhibit compilation (book rule: cite by bibliographic reference only).
- [ ] Every conclusion must be backed by the referenced files, not by the book's table of contents.

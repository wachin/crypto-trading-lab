# AFML technique specifications

This document is the project's own specification of the research-tier
techniques from *Advances in Financial Machine Learning* (Marcos López de
Prado, Wiley, 2018) that `ROADMAP.md` Chapter 49 and its cross-references
(38.8, 44.8, 45.3, 47.4, 48) require.

It exists because the MIT-licensed exercise repository
(`external/adv-financial-ml-marcos-exercises`) does **not** cover all of those
techniques (see `reference-projects.md` §A.7), and because the roadmap rule is
explicit: *never implement from memory of the book alone* — each technique must
be verified against a recorded definition before it is coded (Ch. 49.9).

## 0. Scope, authority, and legal rules

- **Scope.** Research-tier capabilities only. None of these techniques is
  required by the MVP, none may generate an order by itself, and all of them
  obey the evidence rules of Chapter 43 and the leakage rules of Chapters 38
  and 48 (Ch. 49.10).
- **Authority.** The printed book is the conceptual authority in any dispute
  between implementations (Ch. 49.9). This document records *our* working
  definitions and the pointers needed to verify them; it does not replace the
  book. Where the exhibit compilation lacks the book's prose, the technique is
  specified from its **primary paper** instead — the "additional research" the
  roadmap permits (Ch. 49) — and the paper is listed in §5.
- **Never redistribute the book.** No book prose, figure, table, or code
  listing is copied into this repository; the same applies to the papers cited
  in §5. Sources are cited by bibliographic reference:
  > López de Prado, M. (2018). *Advances in Financial Machine Learning*.
  > Wiley. ISBN 978-1-119-48208-6.
- **Exhibit pointers** below refer to the project's own copy of the book's
  exhibit compilation (see §1)
  by *snippet / equation / figure / table number* plus *page*. Those numbers
  are the book's own numbering, so they remain valid against the printed book.
- **Status legend.** `not implemented` · `specified` (this document defines it
  well enough to write tests) · `implemented` (code merged and tested).
- **Verification duty.** Each technique entry carries an *Open questions*
  block. Any question marked *blocking* must be resolved — against the printed
  book or the cited primary paper, never from memory — before the algorithm is
  written (Ch. 49.9). Non-blocking residuals are documented with a conservative
  fallback.

## 1. What the book's exhibit compilation is

The developer holds a local companion PDF: the book's *exhibit compilation*
(its List of Exhibits followed by the exhibits themselves). It is **not** part
of this repository and is never committed. Verified on 2026-09-13 with
`pdfinfo`, `pdftotext -layout` and `pdftoppm`:

| Property | Value |
|---|---|
| Source | the book's exhibit compilation (local reference copy, not in this repository) |
| Pages | 218 |
| Structure | pp. 1–10 = *List of Exhibits* (tables, figures, equations, snippets with page numbers); pp. 11–218 = the exhibits themselves, grouped by chapter (`c01`–`c22` running heads) |
| Content | **all 97 code snippets** of the book, plus its equations, figures and tables |
| Narrative prose | **fragments only**: ≈20,600 words in the body, median 69 words/page, 75 of 209 body pages carry fewer than 50 words |

This is an **exhibit compilation, not the full book**. Confirmed by rendering
pages to images: p. 42 contains only Figure 4.2 and p. 45 only Figure 4.3, with
the rest of the page blank; the chapter 11 body (p. 94) contains only Figures
11.1–11.2; the phrase "deflated Sharpe ratio" occurs once in the whole
compilation, in the List of Exhibits (p. 12), never in the body.

Practical consequence: the compilation is an excellent source for **code,
formulas, tables and figure references**, and an unreliable source for
**definitions in prose**. Sections marked *Open questions* below are exactly
where the prose is missing.

The compilation must **never be committed or redistributed** (book rule: cite
by bibliographic reference only). It is a local reference only.

## 2. Coverage map (roadmap section → technique → evidence)

| Roadmap | Technique | Code in exercise repo | Exhibits in the compilation | Status |
|---|---|---|---|---|
| 49.1 / 29.1 | Event-based bars, CUSUM filter | `getTEvents` (Sn. 2.4), `features/bars.py` | Table 2.1 (p. 13); Figs. 2.1–2.3; Sn. 2.1–2.4 (pp. 21–23) | not implemented here |
| 49.2 | Triple-barrier labeling | `ch3.py` Sn. 3.1–3.8 | Sn. 3.1–3.8 (pp. 26–34); Figs. 3.1–3.2 | not implemented here |
| **49.3** | **Sample uniqueness and weights** | **none** | **Sn. 4.1–4.11 (pp. 35–44); Eq. 32; Figs. 4.1–4.3** | specified (§3.1) |
| **47.4** | **Fractional differentiation** | **none** | **Sn. 5.1–5.4 (pp. 48–53); Table 5.1; Figs. 5.1–5.5** | specified (§3.2) |
| 49.4 / 38.8 | Purged K-Fold + embargo | `ch7.py` Sn. 7.1–7.4 | Sn. 7.1–7.4 (pp. 63–67); Figs. 7.1–7.3 | not implemented here |
| **49.4 / 45.3** | **Combinatorial purged CV (CPCV)** | **none** | **Eq. 39–44 (pp. 96–99); Figs. 12.1–12.2; §12.4.1/§12.5 (pp. 96–98)** | specified (§3.4) |
| **49.5** | **Probabilistic Sharpe ratio (PSR)** | **none** | **Eq. 52 (p. 126); Fig. 14.2 (p. 127)** | specified (§3.5) |
| **49.5** | **Deflated Sharpe ratio (DSR)** | **none** | **Eq. 53 (p. 127); Fig. 14.3 (p. 128) + primary paper Eqs. 1–2 (§6)** | specified (§3.6) |
| **49.6 / 44.8** | **PBO via CSCV** | **none** | **Figs. 11.1–11.2 (p. 94) + primary paper Algorithm 2.3 (§6)** | specified (§3.7) |
| 49.7 | MDI / MDA / SFI / clustered importance | `ch8.py` Sn. 8.2–8.8 | Sn. 8.2–8.10 (pp. 68–76); Figs. 8.1–8.4 | not implemented here |
| 48.1 / 48.3 | Hyper-parameter tuning with purged CV | **none** | Sn. 9.1–9.4 (pp. 79–82) | specified (§3.8) |
| 49.8 / 58 | Bet sizing (+ limit price) | **none** | Sn. 10.1–10.4 (pp. 87–91); Figs. 10.1–10.3 | specified (§3.9) |
| 49.8 | Meta-labeling | `ch3.py` Sn. 3.6–3.7 | Sn. 3.6–3.7 (pp. 31–32) | not implemented here |
| **47.4** | **Structural-break features (SADF/CUSUM)** | **none** | **Sn. 17.1–17.4 (pp. 164–165); §17.3 (p. 156); Eq. 59–66** | specified (§3.10) |
| **47.4** | **Entropy features** | **none** | **Sn. 18.1–18.4 (pp. 168–172); Eq. 67–89 (pp. 168–179)** | specified (§3.11) |
| 40 / 41 | Bet timing, holding period, HHI, DD/TuW series | **none** | Sn. 14.1–14.4 (pp. 120–124); Sn. 13.1–13.2 (pp. 103) | specified (§3.12) |
| 12 | Parallel research jobs (`mpPandasObj` design) | `ch20.py` Sn. 20.5–20.10 | Sn. 20.1–20.14 (pp. 187–199) | not implemented here |

## 3. Technique specifications

Each entry states: purpose, inputs, **mandatory recorded parameters** (Ch. 49,
Ch. 52–53), algorithm outline, evidence pointers, implementation notes, tests
required by Chapter 14, and open questions.

### 3.1 Sample uniqueness and weights (Ch. 49.3)

**Purpose.** Overlapping labels make observations dependent; equal weighting
then overstates the effective sample size. Weight each label by how much of its
holding interval is not shared with other labels.

**Inputs.** Per-event start/end times `t0, t1` (from triple-barrier labeling),
the bar index, close prices.

**Mandatory recorded parameters.** The weighting scheme (uniqueness only, or
uniqueness × return attribution, plus optional time decay); the time-decay
parameter `c` when used; the number of bootstrap draws for the sequential
bootstrap; the random seed.

**Outline.**
1. *Concurrency* (Sn. 4.1, p. 35): an indicator matrix `1[t,i] = 1` iff bar `t`
   lies inside the holding interval of label `i`; concurrency `c[t] = Σ_i 1[t,i]`.
   Events still open at the end of the sample keep counting (fill the last
   `t1` with the last bar timestamp).
2. *Average uniqueness* (Sn. 4.2, p. 37): `u[t,i] = 1[t,i] / c[t]`; the weight
   of label `i` is the mean of `u[t,i]` over the bars it spans.
3. *Return attribution* (Sn. 4.10, p. 43): `w[i] = |Σ_{t∈[t0,t1]} r[t] / c[t]|`
   with log-returns so they are additive; rescale so `Σ w[i] = I`.
4. *Sequential bootstrap* (Sn. 4.3–4.9, pp. 38–41): draw observations one at a
   time, each draw's probability proportional to the average uniqueness it
   would add to the sample already drawn (recomputed after every draw).
5. *Time decay* (Sn. 4.11, pp. 43–44): multiply weights by a piecewise-linear
   factor on **cumulative uniqueness** (not on calendar time): newest
   observation weight 1, oldest `c`; for `c < 0` the factor is zero before
   `|c|` of the cumulative uniqueness. `c ∈ (-1, 1]`.

**Evidence.** Sn. 4.1–4.11 (pp. 35–44); Eq. 32 (p. 36); Figs. 4.1–4.3;
§4.7 "Time decay" prose retained at p. 44.

**Implementation notes.** The book's code is Python-2-era (`.iteritems()`,
`xrange`), uses an O(bars × events) loop, and depends on the book's own
`mpPandasObj` engine (Sn. 20.7). A production port must vectorize the interval
counting and must not depend on the exercise repository's multiprocessing
module. Warn the user when the mean uniqueness is far below 1 (effective sample
size much smaller than the nominal count — Ch. 49.3).

**Tests required.** Interval-overlap edge cases (nested, touching, disjoint,
open-ended); uniqueness of a single non-overlapping label equals 1; weights sum
to `I`; decay endpoints; determinism given a fixed seed.

**Open questions.** None for the core algorithm.

### 3.2 Fractional differentiation (Ch. 47.4)

**Purpose.** Make a price series stationary while retaining as much memory
(serial dependence) as possible; integer differencing destroys memory.

**Inputs.** A price series (normally log-prices), a differentiation order `d`,
and a weight-loss / weight cut-off threshold.

**Mandatory recorded parameters.** `d` (the order actually used), the search
grid for `d`, the weight threshold, whether the expanding-window or
fixed-width-window variant was used, and the stationarity test plus its
critical value.

**Outline.**
1. *Binomial weights* (Sn. 5.1, p. 48): `ω[0] = 1`,
   `ω[k] = -ω[k-1] · (d - k + 1) / k`; `ω[k] → 0` only for integer `d`.
2. *Expanding window* (Sn. 5.2, p. 50): normalize the cumulative absolute
   weights; skip the initial points until the retained cumulative weight exceeds
   the threshold `thres`; then, for each point, dot the available weight vector
   with the series so far (note: the window grows, so early weights are unstable).
3. *Fixed-width window (FFD)* (Sn. 5.3, p. 51): truncate the weights where
   `|ω[k]| < thres`, fix the resulting width, and apply a constant-width dot
   product. This is the variant the book recommends ("new solution") and the
   one this project should implement first.
4. *Choice of `d`* (Sn. 5.4, p. 53; Fig. 5.5; Table 5.1): sweep
   `d ∈ [0, 1]`, run an ADF test on the differentiated series, and choose the
   **smallest** `d` whose ADF statistic passes the 95% critical value, checking
   that the correlation with the original series (the retained memory) stays
   high.

**Evidence.** Sn. 5.1–5.4 (pp. 48–53); Figs. 5.1–5.5 (pp. 47–52);
Table 5.1 (p. 54); §5.4 prose retained at pp. 46–47.

**Implementation notes.** The book uses `statsmodels` `adfuller` (a
**dependency decision**: verify Debian availability per Chapter 4 before
coding) and the fixed-width weights use a threshold of `1e-5` by default and
`1e-4`–`1e-2` for the `d` search. Vectorize the convolution
(`numpy.convolve`/`lfilter`); the book's per-row loop is O(n·width).

**Tests required.** Integer `d` equals ordinary differencing; `d = 0` returns
the input (after warm-up); weight recurrence values for known `d`; NaN handling;
reproducibility; stationarity of the output on a synthetic random-walk series
for a sufficiently large `d`.

**Open questions.** None.

### 3.3 Purged K-Fold and embargo (Ch. 49.4, 38.8)

**Purpose.** Purge training observations whose label interval overlaps the
test block, and embargo a buffer after each test block, so leakage cannot
inflate cross-validation scores.

**Inputs.** Label end times `t1`, number of folds, embargo fraction.

**Mandatory recorded parameters.** Number of folds, embargo length
(`pctEmbargo` or an absolute duration), and the fact that purging and embargo
were applied.

**Outline.** `getTrainTimes` (Sn. 7.1, p. 63) removes training observations
whose `[t0, t1]` overlaps any test interval; `getEmbargoTimes` (Sn. 7.2, p. 65)
computes the embargoed times after each test block; `PurgedKFold` (Sn. 7.3,
p. 66) yields purged/embargoed splits; `cvScore` (Sn. 7.4, p. 67) scores a
classifier on those splits.

**Evidence.** Sn. 7.1–7.4 (pp. 63–67); Figs. 7.1–7.3 (pp. 62–65). Reference
code exists in the exercise repository (`src/snippets/ch7.py`) — the only
already-available implementation for this technique.

**Implementation notes.** This is the canonical CV used by 38.8, 45.3, 48.3 and
49.7. Never present a purged-CV score as a substitute for a true untouched
out-of-sample test (Ch. 49.4). The portable behaviour is already specified in
the roadmap; this document only records the exhibit pointers.

**Tests required.** Overlapping/non-overlapping boundary cases; embargo
boundaries; no test observation ever appears in the training set; deterministic
splits given a fixed input.

**Open questions.** None.

### 3.4 Combinatorial purged cross-validation (Ch. 49.4, 45.3)

**Purpose.** Derive many train/test paths from the same history instead of a
single walk-forward path, so the *distribution* of results can be reported and
data re-use disclosed.

**Inputs.** Number of groups `N` (contiguous, no shuffling), test-set size `k`
groups, plus purging and embargo at every boundary.

**Mandatory recorded parameters.** `N`, `k`, the purge/embargo settings, the
number of splits and paths, and the path-to-result mapping.

**Outline.**
1. Partition the observations into `N` contiguous groups; groups
   `1…N-1` of size `⌊T/N⌋`, the `N`-th taking the remainder (Eq. 39, p. 96).
2. All test sets are the `C(N, N-k)` combinations of `k` groups (Eq. 39);
   every group is tested the same number of times.
3. Number of backtest paths `φ[N,k] = (k/N)·C(N,N-k) = C(N-1, k-1)` (Eq. 40);
   the book's example `φ[6,2] = 5` (Fig. 12.1, p. 96; Fig. 12.2, p. 96).
4. Variance of the mean Sharpe across paths falls when the average
   off-diagonal correlation `ρ̄ < 1` (Eq. 43a–43b, p. 98), which is why CPCV
   produces fewer false discoveries than walk-forward or plain CV
   (§12.5, p. 97).

**Evidence.** Eq. 38–44 (pp. 95–99); Figs. 12.1–12.2 (p. 96); definitions and
prose at §12.4.1 (p. 96) and §12.5 (pp. 97–98). **No code listing exists** for
CPCV in the book or in the exercise repository: it must be implemented on top
of `PurgedKFold`.

**Implementation notes.** Use the combinatorial split count and path formula
above as the acceptance criterion for the generator. Purging/embargo apply at
every train/test boundary of every combination. CPCV complements, never
replaces, walk-forward and a final untouched out-of-sample period (Ch. 45.3).

**Tests required.** Split count equals `C(N, N-k)`; path count equals
`C(N-1, k-1)`; each group appears in the same number of test sets; no train
observation overlaps a test interval; reproducible enumeration order.

**Open questions.** None for split generation.

### 3.5 Probabilistic Sharpe ratio (Ch. 49.5)

**Purpose.** Probability that the true Sharpe ratio exceeds a stated benchmark,
given the observed Sharpe ratio, skewness, kurtosis and sample length.

**Inputs.** Return series or its first four moments; the benchmark Sharpe `SR*`
and the sample length `T` (the book's Eq. 52 calls it `n`).

**Mandatory recorded parameters.** The benchmark used, the sample length, and
the observed skewness and kurtosis.

**Outline.** Eq. 52 (p. 126):

```
PSR[SR*] = Z[ (SR_hat - SR*) · sqrt(T - 1)
              / sqrt( 1 - g3·SR_hat + ((g4 - 1)/4)·SR_hat² ) ]
```

where `SR_hat` is the non-annualized Sharpe estimate, `g3` skewness, `g4`
kurtosis, and `Z[·]` the standard normal CDF. The estimate assumes
non-normality is captured by the first four moments and that returns are
independent. This is the same expression as Eq. 2 of Bailey & López de Prado
(2014) with the benchmark replaced by `SR*`.

**Evidence.** Eq. 52 (p. 126); Fig. 14.2 (p. 127, PSR vs skewness and sample
length). The estimator was introduced in Bailey & López de Prado (2012) and is
restated in the 2014 DSR paper (§6).

**Tests required.** `PSR → 0.5` when `SR_hat = SR*`; monotonicity in `T` and in
`SR_hat - SR*`; reduction to the normal case when `g3 = 0, g4 = 3`; explicit
labeling of model assumptions in reports.

**Open questions.** None.

### 3.6 Deflated Sharpe ratio (Ch. 49.5)

**Purpose.** Correct a best-of-`N` Sharpe ratio for selection bias under
multiple trials: use as the PSR benchmark the Sharpe ratio expected from the
maximum of `N` independent trials when the true Sharpe ratio is zero.

**Inputs.** The selected strategy's return series (giving `SR_hat`, `T`,
skewness `g3`, kurtosis `g4`), the number of independent trials `N`, and the
variance of the trials' Sharpe estimates `V[{SR_n}]`.

**Mandatory recorded parameters.** `SR_hat` (state the return frequency — the
formula uses the same frequency as `T`), `T`, `g3`, `g4`, `N` (the number of
configurations actually attempted — "an experiment that cannot count its trials
cannot claim a deflated estimate", Ch. 49.5), `V[{SR_n}]`, and how `N` and `V`
were obtained.

**Outline.** Let `γ ≈ 0.5772156649` be the Euler–Mascheroni constant, `e`
Euler's number and `Z[·]` the standard normal CDF.

1. Expected maximum Sharpe under the null (Bailey & López de Prado (2014),
   Eq. 1; book Eq. 53, p. 127). Under the null of zero true Sharpe the mean
   term of the paper's Eq. 1 vanishes, leaving

   ```
   SR_0 = sqrt(V[{SR_n}]) · [ (1 - γ)·Z⁻¹(1 - 1/N)
                             + γ·Z⁻¹(1 - 1/(N·e)) ]
   ```

2. Deflated statistic (paper Eq. 2), i.e. a PSR (§3.5) evaluated at `SR_0`:

   ```
   DSR = PSR[SR_0] = Z[ (SR_hat - SR_0)·sqrt(T - 1)
                       / sqrt( 1 - g3·SR_hat + ((g4 - 1)/4)·SR_hat² ) ]
   ```

**Sources.** Bailey & López de Prado (2014), *The Deflated Sharpe Ratio:
Correcting for Selection Bias, Backtest Overfitting and Non-Normality*,
Journal of Portfolio Management 40(5):94–107, Eqs. 1–2 (§6). Both equations
were verified against the published paper, not recalled: Eq. 1 and Eq. 2 were
read from the rendered pages of the public PDF. The book restates them as
Eq. 52–53 (pp. 126–127); Figs. 14.2–14.3 (pp. 127–128).

**Implementation notes.**
- Report DSR as a **probability in [0, 1]**, never as a Sharpe ratio, and label
  it as model-based with its assumptions visible (Ch. 49.5).
- Implement PSR once (§3.5) and evaluate it at `SR_0`; do not duplicate the
  formula.
- **Annualization trap (verified against the paper's example).** The paper
  states `V[{SR_n}]` and the reported `SR` on an **annualized** basis, while
  the PSR core of Eq. 2 takes the observed `SR_hat` and `T` in the returns'
  own frequency. `SR_0` and `SR_hat` must therefore be expressed in the *same*
  frequency before subtracting: convert the annualized threshold with
  `SR_0 / sqrt(periods_per_year)`. Skipping this conversion produces an
  absurd result (DSR → 0 or → 1 instead of ≈ 0.90) and is the single easiest
  way to implement the formula wrongly.
- **Correlation caveat.** `N` is the number of *independent* trials. The
  paper's Appendix 3 covers determining `N` when trials are not independent;
  that appendix is not in the locally obtained copy of the paper. Until it is
  consulted, pass the raw trial count and say so: because the threshold rises
  with `N`, a raw count larger than the effective number of independent trials
  yields a **conservative (lower) DSR** — it can understate significance but
  never inflate it. Record this choice in the experiment metadata.
- The paper's worked example is instructive for the UI: an annualized Sharpe of
  2.5 over a 5-year daily sample with strongly non-normal returns, after 100
  trials, leaves only ~90% confidence that the true Sharpe exceeds zero; the
  same strategy would have cleared the 95% bar had only 46 independent trials
  been run. Deflation is not a cosmetic correction; explain it in beginner
  terms (Ch. 49.5).
- Trial records come from the optimization/experiment manager (Ch. 39, 52).

**Tests required.**
- **Reproduce the paper's example exactly** (this is the canonical vector; the
  values below were computed from Eqs. 1–2 and match the paper's reported
  0.9004 and 0.9505):
  `SR_hat = 2.5` annualized, `periods_per_year = 250`, `V[{SR_n}] = 0.5`,
  `T = 1250`, `g3 = -3`, `g4 = 10`;
  `N = 100 → DSR ≈ 0.9004` (< 0.95, not significant);
  `N = 46 → DSR ≈ 0.9505` (≥ 0.95, significant).
- `DSR` decreases monotonically as `N` grows and as `V[{SR_n}]` grows.
- `DSR ≤ PSR[0]` whenever `SR_0 ≥ 0`.
- `g3 = 0, g4 = 3` reduces the denominator to the normal case.
- Boundary behaviour: `SR_hat = SR_0` gives `DSR = 0.5`.
- `N = 1` is a documented special case: `Z⁻¹(1 - 1/N)` is undefined there, so
  the implementation must define `SR_0 = 0` (no deflation, `DSR = PSR[0]`)
  explicitly instead of returning `-inf`.

**Open questions.** One residual, non-blocking: the paper's Appendix 3
(effective number of independent trials when trials are correlated). Until it
is obtained, use the conservative raw-count fallback documented above.

### 3.7 Probability of backtest overfitting / CSCV (Ch. 49.6, 44.8)

**Purpose.** Estimate the probability that the configuration selected as best
in-sample will *underperform the median* of the `N` configurations out-of-sample,
using combinatorially symmetric cross-validation (CSCV). This is the measure
the roadmap requires next to any multi-trial selection result.

**Inputs.** A matrix `M` of order `T × N`: one column per configuration tried
(`N` trials), rows on a common synchronous time index, with values from which
the performance metric can be computed on sub-samples (e.g. per-period P&L or
returns).

**Mandatory recorded parameters.** `N` (number of configurations), `T`, `S`
(the **even** number of row partitions), the performance metric, and the
selection method. `PBO` must always be reported together with the trial count
and the metric (Ch. 44.8, 49.6).

**Outline** (CSCV, Bailey, Borwein, López de Prado & Zhu, Algorithm 2.3):
1. Assemble `M` (`T × N`); observations must be synchronous across columns
   (aggregate to a common index if configurations trade at different
   frequencies).
2. Partition `M` across rows into `S` disjoint, equal sub-matrices of order
   `T/S × N` (`S` even).
3. Form all `C(S, S/2)` combinations of `S/2` sub-matrices (e.g. `S = 16` gives
   12,780 combinations).
4. For each combination `c`:
   a. In-sample set `J` = the chosen `S/2` blocks concatenated (`T/2 × N`).
   b. Out-of-sample set `J̄` = the complement (`T/2 × N`).
   c. Compute the `N` performance statistics on `J` and rank them; rank `N` is
      the best.
   d. Same on `J̄`, giving ranks `r̄`.
   e. `n*` = the configuration with the best in-sample performance.
   f. Relative out-of-sample rank `ω̄_c = r̄_{n*} / (N + 1) ∈ (0, 1)`.
   g. Logit `λ_c = ln( ω̄_c / (1 - ω̄_c) )`.
5. `PBO = ∫_{-∞}^{0} f(λ) dλ`, estimated as the **relative frequency of
   combinations with `λ_c < 0`** — i.e. the rate at which the in-sample best
   ranks below the out-of-sample median.

**Complementary statistics from the same run** (report alongside `PBO`):
- *Performance degradation*: regress the selected configurations' OOS
  performance on their IS performance; the slope is typically negative, showing
  that a higher IS Sharpe does not imply a higher OOS Sharpe. This is the
  book's Fig. 11.1.
- *Probability of loss*: the proportion of combinations where the IS-best
  configuration's OOS performance is negative.
- *Stochastic dominance*: whether selecting the IS best beats choosing a
  configuration at random.
- The **logit distribution** itself (the book's Fig. 11.2).

**Sources.** Bailey, Borwein, López de Prado & Zhu, *The Probability of
Backtest Overfitting*, Journal of Computational Finance (2017); preprint
(Feb 2015) at SSRN 2326253 and davidhbailey.com (§6). Algorithm 2.3,
Eqs. 2.1–2.4 and Section 3 were read from the public preprint. The book's
Figs. 11.1–11.2 (p. 94) are that paper's Figure 2; Definition 2 "Overfit
Trading Rule" (p. 99) matches its Definition 2.1.

**Implementation notes.**
- CSCV is model-free and non-parametric: the metric may be the Sharpe ratio,
  Sortino, PSR, etc.; record which one was used.
- The published procedure does **not** purge overlapping labels — it addresses
  selection bias on a synchronous performance matrix. Each column's performance
  series must therefore come from a leakage-safe evaluation; when labels
  overlap, apply purging/embargo (§3.3) while building the trial series and
  document it.
- Guard the combinatorics: choose `S` deliberately, record it, and cap it so the
  number of combinations stays computable.
- Degenerate input breaks the `r̄/(N+1)` scaling: identical configurations
  (duplicate columns), constant columns or `N = 1` must be detected and
  reported instead of silently producing a meaningless PBO.
- The paper suggests treating `PBO > 0.05` as grounds for scepticism; Ch. 49.6
  governs our behaviour: a high PBO must visibly lower the evidence level of
  the result, and PBO must never be presented as an exact prediction.

**Tests required.**
- Combination count equals `C(S, S/2)`; `J` and `J̄` are disjoint complements of
  `T/2` rows each.
- Synthetic null: for `N` independent random configurations with no edge,
  `PBO ≈ 0.5`; for a genuinely dominant configuration, `PBO ≈ 0`.
- Rank convention is consistent (rank `N` = best) and `n*` maximizes IS
  performance.
- `PBO ∈ [0, 1]` and `λ_c` is finite for every combination
  (`ω̄_c ∈ (0, 1)`).
- Reproducibility for a fixed `M` and `S`; deterministic combination
  enumeration.
- Degenerate inputs (duplicate/constant columns) raise a reported warning.

**Open questions.** None blocking. The book's PBO/CSCV chapter text is still
absent from the compilation, so the primary paper remains the authority to cite; if the
printed book is later consulted, record any divergence.

### 3.8 Hyper-parameter tuning with purged CV (Ch. 48.1, 48.3)

**Purpose.** Search a parameter grid (or a random distribution) using purged
K-fold **inside** the training data, and optionally bag the chosen estimator.

**Inputs.** Features, labels, label end times `t1`, a scikit-learn pipeline, a
parameter grid, folds, embargo fraction, optional bagging settings.

**Mandatory recorded parameters.** The grid/distribution searched, number of
folds, embargo fraction, scoring rule, number of random-search iterations,
bagging settings, and the random seed.

**Outline** (Sn. 9.1/9.3, pp. 79–80). Scoring is `f1` when the labels are
binary (meta-labeling) and `neg_log_loss` otherwise (log loss takes predicted
probabilities into account, §9.3); the inner CV is a `PurgedKFold` with embargo;
`GridSearchCV` or `RandomizedSearchCV` selects the pipeline; optional
`BaggingClassifier` on top, fitted with sample weights. Sn. 9.2 (p. 80) is a
pipeline subclass that forwards `sample_weight`. Sn. 9.4 (p. 82) provides a
log-uniform distribution (`logUniform`) for parameters such as the learning
rate.

**Evidence.** Sn. 9.1–9.4 (pp. 79–82); Figs. 9.1–9.2 (pp. 82–84); Eq. 36.

**Implementation notes.** scikit-learn is not currently a project dependency;
adding it requires the Chapter 4.0 STOP procedure. The scoring rule and the
purged inner CV are the parts that must not be dropped.

**Tests required.** Hyper-parameters are never selected on the test period;
the same seed reproduces the same choice; binary vs non-binary scoring switch;
sample weights reach the final estimator.

**Open questions.** None.

### 3.9 Bet sizing and limit prices (Ch. 49.8, 58)

**Purpose.** Convert classifier probabilities (and, under meta-labeling, the
primary signal's side) into a target position size, and derive the limit price
that realizes it without taking a loss.

**Inputs.** Predicted probabilities, number of classes, event end times,
optional meta-label `side`, discretization step, maximum position `Q`, the
sigmoid width `ω`, current position, current and forecast prices.

**Mandatory recorded parameters.** Averaging rule for concurrent signals,
discretization step, `ω` calibration (divergence and target bet size), and `Q`.

**Outline.**
1. *Signal from probabilities* (Sn. 10.1, p. 87): one-vs-rest t-value
   `(p - 1/K) / sqrt(p(1-p))`, mapped through `2·Φ(x) - 1` and signed by the
   prediction; multiplied by the meta-label `side` when present.
2. *Average active signals* (Sn. 10.2, p. 88): at each time point average the
   signals whose holding interval is still open.
3. *Discretization* (Sn. 10.3, p. 89): round the averaged signal to multiples
   of `stepSize` and cap it in `[-1, 1]`.
4. *Dynamic size and limit price* (§10.6, pp. 89–91; Sn. 10.4, pp. 90–91):
   bet size `m[ω,x] = x / sqrt(ω + x²)` with `x = f - p` the price divergence;
   target position `q̂ = int(m·Q)`; the breakeven limit price averages the
   inverse function `L[f, ω, m] = f - m·sqrt(ω/(1 - m²))` over the increments
   of the order size.

**Evidence.** Sn. 10.1–10.4 (pp. 87–91); Figs. 10.1–10.3; §10.3 (p. 86),
§10.6 (pp. 89–91); Eq. 37.

**Guardrail.** Any bet size derived here is a **research output**. It must pass
through the risk manager (Ch. 58) before it can inform anything operational and
must never bypass the signal → order separation of 33.6.

**Tests required.** `m ∈ (-1, 1)`; discretization idempotence after one pass;
size monotonic in the divergence; inverse function round-trips; limit price
lies between current and forecast price; caps at `±Q`.

**Open questions.** None for the sigmoid variant (the power-function variant is
left as an exercise by the book and is out of scope).

### 3.10 Structural-break features (Ch. 47.4)

**Purpose.** Features that detect explosive behaviour and regime changes:
recursive right-tailed ADF tests (SADF/GSADF/CADF) and CUSUM tests on recursive
residuals.

**Inputs.** Log-price series, minimum sample length, deterministic terms
(`nc`, `c`, `ct`, `ctt`), lag order, and (for CADF) a rolling window.

**Mandatory recorded parameters.** Minimum sample length, deterministic
specification, lag order and/or lag-selection rule, window length, and the
critical values used.

**Outline.** Sn. 17.1 (p. 164) computes the backward SADF/GSADF statistic as the
supremum over recursive start points of the ADF t-statistic, using the OLS
helpers `getYX` (Sn. 17.2, p. 164), `lagDF` (Sn. 17.3, p. 165) and `getBetas`
(Sn. 17.4, p. 165). The CUSUM tests on recursive residuals (§17.3, p. 156) are
the second family; the CUSUM *filter* for event sampling is Sn. 2.4 (p. 23).

**Evidence.** Sn. 17.1–17.4 (pp. 164–165); §17.3 (p. 156); Eq. 59–66
(pp. 158–166); Figs. 17.1–17.3; Table 17.1.

**Tests required.** Reproduce the SADF on a synthetic explosive series; lag
matrix construction; deterministic-term variants; no look-ahead in the
recursive estimation; NaN/warm-up handling.

**Open questions.** The chapter prose around the snippets is fragmentary in the
exhibit compilation; confirm the SMT/CADF definitions and the critical-value
tables against the book before implementing the CADF variant.

### 3.11 Entropy features (Ch. 47.4)

**Purpose.** Information-content features: Shannon entropy and entropy-rate
estimators of quantized returns, used as a measure of how predictable a series
is.

**Inputs.** A symbol sequence (quantized returns or price changes) and a
quantization/encoding scheme.

**Mandatory recorded parameters.** The quantization scheme (number of letters,
binning rule), the block/window length `w`, and the estimator used.

**Outline.**
1. *Plug-in (maximum-likelihood) entropy rate* (Sn. 18.1, p. 168): build the
   empirical distribution of all length-`w` substrings, then
   `H = -Σ p_i·log2(p_i) / w`.
2. *Lempel-Ziv* (Sn. 18.2–18.3, pp. 169–170; Sn. 18.4, p. 172): build the
   dictionary of non-redundant substrings; `matchLength` returns the length of
   the longest match plus one; the Kontoyiannis estimator averages
   `log2(window + 1) / L_i` over the sequence (expanding-window variant when
   `window = None`), and reports redundancy `r = 1 - h/log2(len(msg))`.
3. §18.2 (p. 167) reviews Shannon's entropy; Eq. 67–89 (pp. 168–179) carry the
   estimators and their asymptotic behaviour; Fig. 18.1 (pp. 174–175) shows
   how sensitive the estimates are to the encoding (10, 7, 5 and 2 letters).

**Evidence.** Sn. 18.1–18.4 (pp. 168–172); Eq. 67–89 (pp. 168–179);
Figs. 18.1–18.2; §18.2 (p. 167).

**Implementation notes.** The quantization scheme is the dominant modelling
choice; it must be documented with the feature (Ch. 47.4) and compared across
encodings in validation, since the estimates are encoding-dependent. The
book's `konto` is O(n·w²) and must be vectorized or bounded in production.

**Tests required.** Constant sequence → zero entropy; alternating sequence
`"101010"` → known values as in the book's example; redundancy bounds
`0 ≤ r ≤ 1`; determinism; sensitivity test across encodings.

**Open questions.** None.

### 3.12 Backtest statistics exhibits for Chapters 40–41 (Ch. 13–14)

**Purpose.** Reusable statistics that the performance-metrics chapter (40) and
the reports chapter (41) can adopt: bet boundaries, holding period,
concentration, and the drawdown / time-under-water *series* (not just the
maximum).

**Exhibits.**
- *Bet timing* (Sn. 14.1, p. 120): a bet starts/ends at flat positions and at
  position flips.
- *Holding period* (Sn. 14.2, p. 120): average holding period in days computed
  by entry-time pairing weighted by position change.
- *Concentration* (Sn. 14.3, p. 124): normalized Herfindahl-Hirschman index of
  positive returns, negative returns, and bets per month.
- *Drawdowns and time under water* (Sn. 14.4, p. 124, Fig. 14.1, p. 125):
  sequence of drawdowns from each high-water mark and the time under water
  between them.
- *Optimal trading rule simulation* (Sn. 13.1–13.2, p. 103; Table 13.1,
  Fig. 13.1–13.25, pp. 104–119): Monte Carlo of profit-target/stop-loss pairs
  for a mean-reverting forecast, used to illustrate strategy-risk heat-maps.

**Notes.** These are the only chapter-13/14 exhibits relevant to Chapter 40
(the next development step) rather than to Part VIII. The drawdown *event
series* is richer than a single maximum-drawdown number and should shape the
metrics API accordingly. This section does not authorize copying book code;
it records which statistics exist and where they are defined.

**Open questions.** The narrative around Sn. 13.1–13.2 and the "strategy risk"
heat-maps is absent from the exhibit compilation; consult the book if the
simulation design is to be reproduced.

## 4. Gap register — what the exhibit compilation cannot supply

**Resolved on 2026-09-13** by consulting the primary papers (§6): the **DSR**
definition (formerly G1) and the **PBO/CSCV** algorithm (formerly G2). Both are
now specified in §3.6 and §3.7 from the published papers, which the roadmap
permits as "additional research" (Ch. 49) when the book's prose is unavailable.

Remaining gaps:

| # | Gap | Affects | Resolution path |
|---|---|---|---|
| G1 | The DSR paper's **Appendix 3** (effective number of independent trials when trials are correlated) is not in the locally obtained copy | 49.5 | Obtain the appendix or the book's ch. 14 text; until then use the conservative raw-count fallback documented in §3.6 |
| G2 | **CSCV does not purge** overlapping labels; it assumes a synchronous performance matrix | 49.6, 44.8 | Build each trial's performance series with purging/embargo (§3.3) and document it |
| G3 | Chapter narrative in the compilation is fragmentary throughout (median 69 words/page) | All | Any *Open questions* block above is a blocker until resolved |
| G4 | Book code is Python 2-era and depends on the book's own multiprocessing engine | 49.3, 47.4, 48.1 | Port with vectorization and this project's own background processing (Ch. 12); record provenance |
| G5 | No local full text of the book; the compilation is not the book | All | The book stays a bibliographic reference (never redistributed); consult it when a technique is implemented |

## 5. References

Cited by bibliographic reference only; no text, code, figure or table is
reproduced.

1. López de Prado, M. (2018). *Advances in Financial Machine Learning*. Wiley.
   ISBN 978-1-119-48208-6. Conceptual authority for Chapter 49; cited, never
   redistributed.
2. Bailey, D. H., & López de Prado, M. (2014). "The Deflated Sharpe Ratio:
   Correcting for Selection Bias, Backtest Overfitting and Non-Normality."
   *The Journal of Portfolio Management* 40(5), 94–107.
   [PDF](https://www.davidhbailey.com/dhbpapers/deflated-sharpe.pdf) ·
   [SSRN 2460551](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2460551).
   Equations 1–2 read from the published PDF and used in §3.5–§3.6.
3. Bailey, D. H., Borwein, J. M., López de Prado, M., & Zhu, Q. J. (2017).
   "The Probability of Backtest Overfitting." *The Journal of Computational
   Finance*. Preprint (rev. February 2015):
   [PDF](https://www.davidhbailey.com/dhbpapers/backtest-prob.pdf) ·
   [SSRN 2326253](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2326253).
   Algorithm 2.3, Equations 2.1–2.4 and Section 3 read from the preprint and
   used in §3.7.
4. Bailey, D. H., Borwein, J. M., López de Prado, M., & Zhu, Q. J. (2014).
   "Pseudo-Mathematics and Financial Charlatanism: The Effects of Backtest
   Overfitting on Out-Of-Sample Performance." *Notices of the American
   Mathematical Society* 61(5), 458–464.
   [PDF](https://www.davidhbailey.com/dhbpapers/backtest-pseudo.pdf).
   Accessible companion to reference 3.
5. Bailey, D. H., & López de Prado, M. (2012). "The Sharpe Ratio Efficient
   Frontier." *Journal of Risk* 15(2). Origin of the Probabilistic Sharpe Ratio
   restated in reference 2.

## 6. Maintenance rules

- Update the status of a technique here **in the same change** that implements
  it (Ch. 19.5), and mirror the mapping in `reference-projects.md` §A.3.
- Keep the exhibit page pointers in sync with the local compilation described
  in §1; if that reference copy is replaced, re-verify the pointers.
- Resolve every *Open questions* block before writing the algorithm; if an
  answer changes the specification, change it here first, then code (Ch. 49.9).
- When a technique is specified from a paper rather than from the book, add the
  paper to §5 and record in the technique entry that the equation was read from
  the source, not recalled.
- Never paste book or paper text into this repository. Adapted code must record
  its provenance (source file and snippet number, or equation number) in the
  docstring and preserve the applicable license attribution.
- The book (printed text or exhibit compilation) must never be committed or
  redistributed.

---

*Created 2026-09-13. Basis: `ROADMAP.md` Ch. 25, 38.8, 40, 43–50, 58 and
`docs/en/developers/reference-projects.md` Part A.*

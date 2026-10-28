# Live vs Backtest Drift (Chapter 63)

## The problem

Backtests are idealized simulations. Real trading (paper or live) will produce different results due to:

1.  **Execution reality** - Slippage, latency, partial fills
2.  **Market conditions** - Liquidity changes, volatility shifts
3.  **Data quality** - Missing candles, incorrect timestamps

This chapter quantifies and explains those differences.

## Drift dimensions

### Return drift

```
Backtest return:  15%
Paper trading:    12%
Drift:            -3% (20% of backtest return)
```

### Drawdown drift

```
Backtest max DD:  12%
Paper trading DD: 18%
Drift:            +6% (worst case worse than expected)
```

### Slippage drift

```
Backtest assumed:  5bps per trade
Actual observed:   12bps per trade
Drift:             +7bps (execution worse than model)
```

### Fill-rate drift

```
Backtest expected: 100% of signals
Actual observed:   75% of signals
Drift:             -25% (liquidity or latency issues)
```

## Root causes

### Backtest assumptions

* Assumes immediate execution at close price
* Assumes full fill at quoted price
* Assumes no exchange rejection
* Assumes no network latency

### Real-world factors

* Market moves during order transmission
* Partial fills due to low liquidity
* Order rejections due to risk limits
* Exchange maintenance or connection loss

## Monitoring

### Automated alerts

* Drift exceeds threshold (e.g., 20% of backtest metrics)
* Fill rate below minimum (e.g., 80%)
* Slippage exceeds model (e.g., 2x backtest estimate)

### Manual review

Compare:
* Strategy signals vs actual orders
* Expected vs actual fills
* Backtest fees vs actual fees

## Interpretation

### Acceptable drift

* Return drift: ±10% of backtest return
* Fill rate: > 90%
* Slippage: within backtest model

### Concerning drift

* Return drift: > 20% of backtest return
* Fill rate: < 80%
* Slippage: > 2x backtest estimate

## Reporting drift (chapter 63.2)

A single drift number hides two things: whether the difference is *normal*
variability or *degradation*, and *where in the run* it appeared.
`assess_drift()` answers both and returns a verdict.

### Expected ranges

`expected_ranges(backtest)` builds the band a live run is expected to stay
inside, and every band carries a `basis` string so the reader can judge it:

| Metric | How the band is built |
| --- | --- |
| `return` | The backtest's own trades are resampled with replacement to measure how much the total varies; that spread is then centred on the return the run actually realised. |
| `max_drawdown` | Anchored on the drawdown the equity curve showed, widened by a 1.5x tolerance. |

Two honest limitations, both stated in the code and in the report:

* The bootstrap knows **closed trades only**. A run that ends holding a
  position marks it to market in `final_equity`, so the raw resampled
  centre sits away from the observed return. That is why the band is
  anchored instead of used directly.
* A trade-level bootstrap **cannot see intra-trade drawdown** — the
  decline between an entry and its exit. Resampling trades therefore
  reports a band of zero for any profitable run, which would have called
  every real drawdown a failure. The drawdown band is anchored on the
  observed drawdown for that reason.

A backtest with fewer than two trades returns no band at all: one trade is
not a distribution.

### Drift over time

`drift_over_time(backtest_curve, paper_curve, buckets=5)` cuts both equity
curves into equal slices and reports the return of each. Two runs can end at
the same value while drifting apart in opposite directions in the middle,
and only the time series shows it. When the paper run is shorter than the
backtest, the common prefix is compared.

### The verdict

Each metric lands in one of four buckets:

| Verdict | Meaning | Effect on status |
| --- | --- | --- |
| `within_expected` | Inside the band. | none |
| `expected_tail` | Outside the band, but within one half-width of it. | none — a tail of the same variability |
| `outside_expected` | Beyond a half-width, on the *good* side. | suspicious: a result better than the model predicted usually means the model, the data or the assumptions are wrong |
| `degraded` | Beyond a half-width, on the *bad* side. | degraded |

The overall status is `degraded` if any metric is degraded, `suspicious` if
any is outside on the good side or the chapter-63 drift classification is
`high`/`severe`, and `healthy` otherwise. A run whose backtest produced
fewer than two trades is reported as `suspicious` with the reason
"unvalidated", never as healthy. If every time slice drifts negatively, the
status is at least `suspicious` and the report says the drift is persistent
rather than one bad window.

### Likely causes

Every metric has a short list of mechanisms to check (`LIKELY_CAUSES`): a
regime the strategy was not built for, a volatility change, sizing that
differs from the backtest, thinner liquidity, latency between decision and
fill, risk-manager rejections, an indicator warm-up the replay did not
have. They are shown only for `degraded` and `outside_expected` metrics —
listing causes for a normal tail would invite the reader to fix something
that is not broken.

### Where it runs

The Paper Trading screen renders the full analysis after each session
(`render_drift_analysis`), including the slices, the bands, the verdict and
the causes. The assessment never touches the risk manager and never places
an order: it is evidence for chapter 64, not an action.

## Checklist

* [x] Track backtest expectations
* [x] Monitor paper trading results
* [x] Compare metrics side-by-side
* [x] Alert on significant drift
* [x] Document root causes
* [x] Compare realized metrics against expected ranges (63.2)
* [x] Show drift over time (63.2)
* [x] Explain likely causes per dimension (63.2)
* [x] Separate expected variability from degradation (63.2)
* [x] Mark a strategy healthy, suspicious or degraded (63.2)

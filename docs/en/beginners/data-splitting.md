# Splitting Historical Data — Plain-Language Guide

ROADMAP chapter 38. The application divides market history into three
chronological blocks:

```text
Historical Data
      ↓
Training (strategy development)
      ↓
Validation
      ↓
Out-of-Sample Test
```

**Never shuffled.** Markets have a direction in time: yesterday causes
today, not the other way round. Splitting randomly would sneak the
future into the past and make every result look better than it is.

## Why divide the data at all?

If you design a strategy on some data and then "test" it on the same
data, you have only proven the strategy can *describe the past* — the
same way reading the answers while taking an exam proves nothing
about your knowledge. The test must happen on data the strategy never
saw while it was being built.

**"The strategy worked on historical data used to design it"**
is a much weaker claim than
**"The strategy continued to work on data that was not used to design it."**

The second statement is the only one worth money.

## The three periods

- **Training** — for experiments: ideas, indicator choices, first
  parameter guesses. Results here are working notes, not evidence.
- **Validation** — for choosing between a few candidates and spotting
  obvious overfitting. Use it sparingly: checking it too often slowly
  turns it into training data.
- **Out-of-sample test** — the final exam. Run it **once**, at the end.
  Every run is recorded, and the application warns when the test
  period is evaluated more than once.

## Why warm-up candles are separate

An SMA-30 needs 30 candles before it produces its first value. So a
validation or test block can borrow a few candles *from the end of the
previous block* purely to warm the indicators up. Those borrowed
candles never count as part of the period itself — the recorded
boundaries always point at the period's true first and last candle.

## Why good out-of-sample results are stronger evidence

Overfitting means the strategy memorized quirks of the past instead of
finding something real. A result that survives on unseen data has at
least passed that filter. It is still only an *observed result* — but
an honest one.

## What about cross-validation?

Standard K-Fold cross-validation breaks financial time series (trades
overlap block boundaries and leak information). The laboratory may
later add *purged and embargoed* cross-validation as a research
capability; plain K-Fold will never be offered for time series.

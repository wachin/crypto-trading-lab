# Statistical Edge and Evidence (Chapter 43)

## What is "statistical edge"?

A **statistical edge** means a strategy's performance is unlikely to be due to random chance. This is different from just seeing profitable results in one backtest.

**Key insight**: A profitable backtest does NOT guarantee future profits. It only shows what happened in the past.

## What this module provides

### Distribution analysis

**What it does**: Summarizes how returns are distributed - their average, spread, and shape.

**Why it matters**: 
- Normal (bell-curve) distributions are easier to analyze
- Heavy-tailed distributions have extreme outliers that can surprise you
- Skewed distributions have asymmetric risk/reward

**Plain language**: If your returns look like a bell curve centered around zero, you're taking risk without compensation. If they're skewed positively (more big winners than big losers), you may have an edge.

### Autocorrelation

**What it does**: Checks if today's return predicts tomorrow's return.

**Why it matters**: Most statistical tests assume returns are independent. If they're not (autocorrelation exists), those tests may give wrong conclusions.

**Plain language**: If winning trades tend to cluster together, your strategy may be riding a trend. If losses cluster, you may face periods of sustained drawdown.

### Bootstrap confidence intervals

**What it does**: Uses resampling to estimate uncertainty in metrics without assuming a specific distribution.

**Why it matters**: Traditional tests assume normality. Bootstrap makes fewer assumptions and works with any return distribution.

**Plain language**: Instead of giving you a single number for Sharpe ratio, bootstrap gives you a range where the "true" value likely falls.

### Deflated Sharpe Ratio (PSR)

**What it does**: Corrects the Sharpe ratio for:
1. Number of trials (how many strategy variations you tested)
2. Non-normal returns
3. Sample size

**Why it matters**: Testing 100 strategy variations and picking the best one creates a "multiple testing" problem - the winner may just be lucky. PSR penalizes for this.

**Plain language**: If you tested 100 parameter combinations and one looks great, it may be a false winner. PSR tells you how likely that is.

## Evidence levels

This module distinguishes between:

1. **Observed result**: What happened in one backtest (descriptive only)
2. **Statistical evidence**: Results supported by documented methods and sufficient samples
3. **Research hypothesis**: An idea being tested, not yet proven
4. **Validated evidence**: Results that survived out-of-sample, robustness, and qualification checks

## Warnings you may see

- **Small sample**: Fewer than 30 observations means low statistical power
- **Multiple testing**: Many strategy variations tested increase chance of false winners
- **Autocorrelation detected**: Returns are not independent; standard tests may be invalid
- **Heavy tails**: Extreme returns happen more often than normal distribution predicts

## How to use this information

1. **Don't trust single backtests** - they are just observations, not evidence
2. **Look for consistency** - use bootstrap to see if results are stable
3. **Count your trials** - more variations tested = higher chance of lucky winners
4. **Check assumptions** - don't use tests that require assumptions your data doesn't satisfy

Remember: This module helps you **research** whether you have an edge. It does not guarantee future profits. Always combine with proper risk management.

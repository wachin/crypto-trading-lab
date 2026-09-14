# Performance Metrics — Plain-Language Guide

This guide documents every performance metric Crypto Trading Lab
computes for a backtest (ROADMAP chapter 40). For each one you get a
technical definition, a plain explanation, a worked example, a misuse
warning, and its limits.

> **No single metric proves that a strategy is good.**
>
> Performance must be interpreted together with risk, drawdown,
> trading costs, number of trades, market conditions, out-of-sample
> performance, and robustness tests. A backtest describes the past it
> was run on. It does not predict the future.

---

## How to read the metrics

Every metric in the application comes with:

- its **technical definition** (the exact formula used);
- a **beginner-friendly definition**;
- a **worked example** with real numbers;
- a **warning about misuse**;
- whether **higher or lower** is generally preferred;
- its **limitations and required assumptions**.

The shared assumptions (chapter 40.7) are recorded with every report:

- **Periodicity:** one equity sample per candle; 365 periods per year
  by default (daily crypto candles).
- **Annualization method:** geometric compounding for returns;
  square-root-of-time scaling for volatility and ratios.
- **Assumed risk-free rate:** 0 by default.
- **Return calculation method:** simple per-period returns from the
  close-to-close equity curve.
- **Missing-data treatment:** none needed — the backtest engine
  produces a contiguous equity curve.
- **Treatment of zero returns:** kept; if volatility or downside
  deviation is exactly zero, the corresponding ratio is not computed
  (shown as "n/a").

**Statistical honesty (chapter 40.6).** When there is not enough data,
the application says so instead of showing a pretty number:

- annualized metrics are **not shown** for runs shorter than one year
  of periods;
- Sharpe and Sortino computed from fewer than 30 return observations
  are flagged as *descriptive, not statistically supported*;
- any run with fewer than 30 trades carries a *very small sample*
  warning.

These warnings are part of the result. Do not ignore them.

---

## Return and profit metrics (chapter 40.1)

### Initial capital / Final equity / Net profit & loss

- **Technical:** capital at the start; equity (cash + position valued
  at the last close) at the end; their difference.
- **Beginner:** how much you started with, how much you ended with,
  and the difference in money.
- **Example:** start 10 000, end 10 800 → net profit 800.
- **Higher is better** for net profit — but see the header: profit
  without knowing the risk taken means little.

### Gross profit / Gross loss

- **Technical:** sum of net P&L over winning trades only / losing
  trades only.
- **Beginner:** the total your winners made and the total your losers
  cost, before netting.
- **Example:** winners made 350, losers lost 100 → gross profit 350,
  gross loss −100.
- **Misuse warning:** a high gross profit with a nearly-as-high gross
  loss is a coin flip with fees, not an edge.

### Total return

- **Technical:** `(final equity − initial capital) / initial capital`.
- **Beginner:** your gain as a fraction of your starting money.
- **Example:** 10 000 → 10 800 is a total return of 0.08 (8%).
- **Higher is better**, *if* achieved with tolerable risk.

### Annualized return

- **Technical:** `(1 + total return) ^ (periods per year / periods)
  − 1` (geometric compounding).
- **Beginner:** what the run's return would correspond to if it kept
  the same pace for a full year.
- **Example:** doubling in one year (return 1.0 over 365 daily
  candles) annualizes to 1.0 (100%).
- **Misuse warning:** never extrapolate a short winning streak. That
  is why the application **refuses to show it** for runs shorter than
  a year. A 5% week is *not* "1171% per year" in any honest sense.
- **Limit:** assumes returns compound at a steady rate — real ones
  never do.

---

## Trade statistics (chapter 40.2)

### Number of trades / Winning / Losing trades

- **Technical:** count of closed round trips; winners have positive
  net P&L, losers negative.
- **Beginner:** how many bets the strategy placed and how many won.
- **Key limit:** **very few trades tell you very little.** Below 30
  trades the application shows a small-sample warning; statistics from
  3 trades are anecdotes, not evidence.

### Win rate

- **Technical:** winning trades ÷ total trades.
- **Beginner:** how often a trade makes money.
- **Misuse warning:** a high win rate with rare but huge losses still
  loses money ("picking up pennies in front of a steamroller").

### Average / Largest winning and losing trade

- **Technical:** mean, maximum, and minimum of per-trade net P&L over
  winners and losers.
- **Beginner:** the typical win, the typical loss, and the extremes.
- **Compare them:** strategy health needs the average win and average
  loss to balance the win rate.

### Average trade / Median trade / Expectancy

- **Technical:** mean per-trade net P&L; the middle value when sorted;
  expectancy is the same as the average trade (expected value per
  trade).
- **Beginner:** what one trade of this strategy was "worth" on
  average.
- **Example:** trades +200, −100, +150 → average 83.33, median 150,
  expectancy 83.33.
- **Higher is better**, and it must be well above zero **after all
  costs** or the strategy cannot survive.

### Profit factor

- **Technical:** gross profit ÷ |gross loss| (not computed when there
  are no losing trades).
- **Beginner:** how many units the winners made per unit the losers
  lost.
- **Example:** winners made 350, losers lost 100 → profit factor 3.5.
- **Misuse warning:** with few trades it is dominated by one lucky
  winner. Values below 1 mean the strategy lost money overall.

### Average holding time

- **Technical:** average of (exit time − entry time) across trades,
  in seconds.
- **Beginner:** how long the money is typically committed.

### Max consecutive wins / losses

- **Technical:** longest run of same-sign net P&L trades.
- **Beginner:** the longest lucky and unlucky streaks; losing streaks
  of this length **will** happen again, so you must be able to sit
  through them.

---

## Risk metrics (chapter 40.3)

### Maximum drawdown

- **Technical:** largest drop (fraction) from a prior equity peak:
  `(peak − trough) / peak`.
- **Beginner:** the worst "underwater" episode, as a percentage of
  where you had been.
- **Example:** equity peaks at 120 and sinks to 90 → max drawdown
  0.25 (25%).
- **Lower is better.** This is the metric that decides whether you can
  psychologically and financially survive the strategy.

### Maximum drawdown duration / Average drawdown

- **Technical:** longest streak of candles spent below the prior peak;
  mean of all non-zero drawdown fractions.
- **Beginner:** how long the pain lasts, and the typical depth.

### Volatility / Downside volatility

- **Technical:** population standard deviation of per-period returns
  (downside: only the returns below zero), annualized by √periods.
- **Beginner:** how violently the equity wiggles; downside volatility
  counts only the *bad* wiggles.
- **Lower is usually preferred** for the same return.

### Sharpe ratio

- **Technical:** `(mean return − risk-free per period) / volatility,
  scaled by √periods per year`.
- **Beginner:** return earned per unit of total risk taken.
- **Higher is better**, *but*: with few observations (the application
  requires ≥ 30) it is noise-shaped, and with fat-tailed returns it
  punishes *winning* volatility as much as losing volatility.

### Sortino ratio

- **Technical:** like Sharpe, but divided by downside deviation
  (returns below zero only).
- **Beginner:** return per unit of *harmful* risk only.
- **Limit:** not defined when no losing period exists (shown as n/a).

### Calmar ratio

- **Technical:** annualized return ÷ maximum drawdown.
- **Beginner:** yearly gain per unit of the worst dip.
- **Limit:** only computed when the annualized return is valid (a full
  year of data) and a drawdown exists.

### Risk-adjusted return

- **Technical:** total return ÷ annualized volatility.
- **Beginner:** how much total return each unit of wiggle bought.

### Market exposure / Long exposure

- **Technical:** fraction of candles holding a position (the engine is
  long-only: both numbers coincide; short exposure is not applicable
  and stays unimplemented until the engine supports shorts).
- **Beginner:** how much of the time your money is at risk at all. A
  strategy in the market 5% of the time and one always-in can share a
  return number with wildly different risk.

---

## Trading activity (chapter 40.4)

- **Turnover:** total traded notional (entries + exits). High turnover
  amplifies the effect of every fee.
- **Number of orders:** executed orders. Rejected and partially
  filled orders cannot occur in the current engine (all fills are
  complete); they are pending roadmap items until a paper-trading
  layer can produce them.
- **Commissions / Trading fees / Spread cost / Slippage:** exact sums
  of what the backtest charged for fees, the modeled bid–ask spread,
  and the modeled execution slippage. **Funding** is not applicable to
  spot trading and stays unimplemented. A strategy whose edge is
  smaller than these costs is not a strategy.

---

## Benchmark comparison (chapter 40.5)

Every report should state, side by side:

- **absolute performance** (the strategy's total return);
- **benchmark performance** (e.g. buy-and-hold's total return);
- **the difference** (excess return).

If a complicated strategy cannot beat simply buying and holding,
the honest conclusion is that it added nothing but costs and risk.

---

## The one rule that outranks all metrics

**No single metric proves that a strategy is good.** Read every report
next to: risk, drawdown, trading costs, number of trades, market
conditions, out-of-sample performance, and robustness tests. The
purpose of these metrics is to protect capital while searching for a
*statistically supported* edge — never to promise one.

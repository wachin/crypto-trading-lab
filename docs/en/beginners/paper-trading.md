# Paper trading, explained for beginners

Paper trading means **real market prices with imaginary money**. It is
the safest way to practise before any real money exists — and this guide
explains exactly what it can and cannot tell you.

## 1. What you need first

Paper trading replays **real candles**, so you need a dataset:

1. Open **File → Get historical data…**
2. Choose `BTC/USDT`, a timeframe (1 hour is a good start) and a period.
3. Press **Download historical data** and check that the screen says
   *ready for research*.

If the screen says the data is *not ready*, fix the gaps or duplicates
first. A result built on bad data is a bad result.

## 2. Run a paper session

1. Open **Tools → Paper Trading**.
2. Choose a strategy (SMA crossover is a good first one).
3. Set the **simulated capital** (for example 10000).
4. Set the **fraction of capital per trade**. Beginners should start
   small: 0.5 means “use half the account for one trade”, 0.1 means
   “use a tenth”. Smaller fractions survive losing streaks.
5. Set the costs: fee, slippage and spread. Leaving them at zero is
   self-deception — real trading charges you.
6. Press **Run paper session**.

## 3. How a decision becomes a trade

- The strategy looks at a candle's **close** and decides.
- The order is filled at the **next candle's open**, with fees and
  slippage applied. The program cannot see the future, and neither can
  the strategy.
- Every intended order passes through the **risk manager** first. If the
  risk manager rejects it, the trade does **not** happen and the journal
  records why.

## 4. Read the journal, not just the profit

The journal lists every decision with:

- the strategy and the signal;
- the time and the reference price;
- the risk decision and its reason;
- the simulated fill, slippage and fee;
- the exit and the final profit or loss.

Ask of every trade: *what did the strategy know at that moment, and what
did the market do afterwards?* That question teaches more than an equity
curve ever will.

## 5. What paper trading does **not** prove

- It does not reproduce the **fear** of losing real money.
- Its fills are optimistic: a thin order book would fill you worse.
- A good paper result is **permission to keep researching**, never proof
  that the strategy will earn money.

> A profitable paper session is not evidence of a persistent edge. It is
> a rehearsal. Capital protection still comes first: never risk money you
> need to live.

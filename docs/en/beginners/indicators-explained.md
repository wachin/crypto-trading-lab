# Technical Indicators — Plain-Language Guide

This guide explains every indicator built into Crypto Trading Lab.
Each one answers: what it measures, what its name means, a plain
explanation, common values, typical misuse, and limits.

**The one warning that applies to all of them:** an indicator is a
lens, not a crystal ball. It summarizes what *already happened*.
None of them — and no combination of them — can guarantee future
price movements.

---

## SMA — Simple Moving Average

**What it measures:** the average closing price over the last N
candles.

**What the name means:** "moving" because the window slides forward
one candle at a time; "simple" because every candle in the window
counts equally.

**Plain words:** if the last 20 candles closed at 100, 102, 101..., the
SMA-20 is their plain average. It turns a noisy price line into a
smoother one.

**Common values:** 20 (about a trading month on daily candles), 50,
200. Shorter = reacts faster but noisier; longer = calmer but slower.

**Typical misuse:** trading every tiny crossing of price and SMA. In
choppy markets that generates a flood of fee-paying trades with no
edge.

**Limits:** it lags by construction — it *is* the past. All
SMA-based signals arrive after the move has begun.

**Visual example:** price zigzags around a gently curving line; that
line is the SMA.

## EMA — Exponential Moving Average

**What it measures:** like the SMA, but recent candles count more.

**What the name means:** "exponential" because a candle's weight
decays exponentially as it gets older.

**Plain words:** the EMA asks "what's the average *recent* price?"
instead of treating last month and one minute ago the same.

**Common values:** 12 and 26 (classic MACD pair), 9, 20.

**Typical misuse:** assuming "faster" means "better". A faster
average just arrives at wrong conclusions faster in choppy markets.

**Limits:** still backward-looking; reacts strongly to one abnormal
candle.

## RSI — Relative Strength Index

**What it measures:** how strong recent gains are compared with
recent losses, on a 0–100 scale.

**What the name means:** "relative strength" = gains relative to
losses, not strength relative to other coins.

**Plain words:** RSI above 70 traditionally means "this market has
risen a lot recently" (often called *overbought*); below 30, "fallen
a lot recently" (*oversold*).

**Common values:** period 14, thresholds 70/30 (or 80/20 in strong
trends).

**Typical misuse:** "RSI is above 70 → short it immediately". In
strong trends RSI can stay above 70 for weeks while price keeps
climbing. Overbought ≠ about to fall.

**Limits:** it says the move was big, not that it will reverse.
Mean-reversion signals fail exactly when trends begin.

## Bollinger Bands

**What it measures:** a price envelope: an SMA center line plus/minus
a multiple of how much price has been swinging.

**What the name means:** named after John Bollinger; "bands" because
they draw two boundary lines around price.

**Plain words:** when the market is calm the bands squeeze close
together; when it turns volatile they widen. Price touching a band
means "unusually far from average", not "must reverse".

**Common values:** period 20, k = 2 standard deviations.

**Typical misuse:** shorting at the upper band in a trend — the band
rides *with* the trend, and touching it can mean strength.

**Limits:** the bands adapt to volatility, so they say "far from
recent average", never "impossible".

## ATR — Average True Range

**What it measures:** the typical size of a candle's movement,
including overnight gaps.

**What the name means:** "true range" = the real distance price
traveled, even when it gapped past the previous close.

**Plain words:** ATR tells you how roughly the market is behaving
right now. ATR 3% = candles typically swing 3% — position sizes and
stop distances should respect that.

**Common values:** period 14. Used for stops (e.g. stop = 2×ATR) more
than for direction.

**Typical misuse:** comparing ATR of different coins in different
units, or using ATR as a direction signal (it has none).

**Limits:** pure volatility measure; says nothing about up vs down.

## ROC — Rate of Change

**What it measures:** the percentage change of price over N candles.

**What the name means:** literally how fast the price is changing.

**Plain words:** ROC = +10 means "price is 10% higher than N candles
ago"; −10 means 10% lower.

**Common values:** 9–14 candles.

**Typical misuse:** buying just because ROC is positive — in a
falling market, ROC merely becomes *less* negative; that is not a
buy signal.

**Limits:** symmetric but blind to context; the same +10% means
different things in a trend versus a crash bounce.

---

## The honest summary

Every indicator here is arithmetic on past prices. They help you
*see* the market more clearly — trend direction, volatility,
extremes — but seeing clearly is not predicting. Strategies built on
indicators must still survive out-of-sample testing, fees, and
slippage before earning any trust. When a backtest using indicators
looks amazing, suspect overfitting first.

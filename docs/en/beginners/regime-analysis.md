# Market Regime Analysis (Chapter 46)

## What is a market regime?

A **market regime** is a period where the market behaves in a characteristic way. Common regimes include:

- **Trending**: Prices move predominantly in one direction
- **Ranging**: Prices oscillate without clear direction
- **High volatility**: Large price swings, frequent big moves
- **Low volatility**: Small price swings, quiet market

## Why do regimes matter?

A trading strategy that works in one regime may fail in another. For example:

- **Trend-following strategies** (like moving average crossovers) usually perform well in trending markets but lose money in ranging markets
- **Mean-reversion strategies** usually work well in ranging markets but can suffer large losses in strong trends

## How does this module detect regimes?

### Trending vs Ranging

Uses a **directionality ratio** similar to the ADX indicator:

```
Directionality = (Net Move) / (Total Distance Traveled)
```

- If prices move directly from point A to B, the ratio is close to 1 (trending)
- If prices oscillate between A and B, the ratio is close to 0 (ranging)

**Parameters**: `lookback` (window size) and `threshold` (minimum ratio to be considered trending)

### High vs Low Volatility

Compares recent volatility to historical average:

```
Is High Volatility = (Recent Std Dev) > (Historical Std Dev) × Multiplier
```

**Parameters**: `lookback` and `threshold_multiplier`

## Important warnings

### Regime detection is a MODEL, not ground truth

Different methods and parameters produce different regime labels. There is no single "correct" way to classify regimes. Treat regime classifications as **hypotheses** to be validated, not facts.

### Regime concentration warning

If a strategy's performance is concentrated (>80%) in one regime, it may be **regime-dependent** and risky. Such strategies can fail when market conditions change.

### Strategy performance per regime

This module allows you to:

- Compute performance metrics (return, profit factor, win rate) for each regime
- Compare strategy behavior across different market conditions
- Detect whether a strategy depends on one specific regime

## How to use this information

1. **Never assume your strategy works everywhere** - check if it depends on specific regimes
2. **Diversify across regimes** - strategies that perform reasonably across multiple regimes tend to be more robust
3. **Update regime detection parameters** based on your market and timeframe
4. **Remember** - past regime behavior doesn't guarantee future regimes

## Beginner example

If you backtest a trend-following strategy on BTC/USDT and find:

- **Trending regime**: +20% return, 55% win rate
- **Ranging regime**: -15% return, 35% win rate

This indicates **regime dependency**. The strategy may not be robust for real trading unless you add regime filters or combine it with other strategies.

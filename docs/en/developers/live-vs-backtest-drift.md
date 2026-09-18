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

## Checklist

* [x] Track backtest expectations
* [x] Monitor paper trading results
* [x] Compare metrics side-by-side
* [x] Alert on significant drift
* [x] Document root causes

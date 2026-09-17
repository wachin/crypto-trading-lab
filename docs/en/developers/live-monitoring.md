# Live Monitoring (Chapter 62)

## What is monitored

Live monitoring covers paper trading, testnet, and real trading sessions.

### Required displays

* Current portfolio value
* Open positions
* Pending orders
* Executed orders
* Fees paid
* Slippage incurred
* Current drawdown
* Total exposure
* Risk-manager decisions
* Connection state
* Data freshness
* Environment indicator (always visible)
* Kill-switch status
* Recent alerts

## Monitoring rules

### Environment visibility

The environment must always be visible:
* Backtest
* Paper trading
* Testnet
* Real trading

### Alert requirements

* Understandable to beginners
* Not color-dependent
* Never bypass the risk manager

### Historical comparisons

Compare live behavior against:
* Backtest expectations (Chapter 63)
* Paper-trading behavior

## State components

### Portfolio state

```
Total value: $10,000
Available: $8,000
Positions: BTC 0.1, ETH 5.0
Drawdown: 5%
Exposure: 20%
```

### Connection state

```
Status: Connected
Data freshness: 2s ago
Kill switch: Inactive
```

### Risk decisions

```
Last order: APPROVED
Reason: Within risk limits
Risk used: 1%
```

## Checklist

* [x] Portfolio value displayed
* [x] Positions shown
* [x] Orders tracked
* [x] Metrics monitored
* [x] Environment visible
* [x] Kill switch status shown
* [x] Alerts understandable

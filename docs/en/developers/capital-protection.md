# Capital Protection (Chapter 61)

## Principle

> **Capital preservation takes priority over strategy execution.**

This principle is enforced at multiple levels. No strategy can bypass capital-protection mechanisms.

## What is protected

1. **Risk limits** - Position sizes, exposure limits, loss limits
2. **Kill switch** - Emergency stop available in every environment
3. **Exposure limits** - Maximum portfolio risk
4. **Account restrictions** - Balance verification, minimum capital
5. **Safety gates** - Pre-trade protection layer

## Enforcement

### Risk manager (Chapter 58)

Enforces all capital-protection rules:
* Position size limits
* Loss limits (daily, weekly, drawdown)
* Operational limits (trades per day)

### Kill switch (Chapter 59)

Provides emergency stop:
* Available in backtest, paper, and real environments
* When active: blocks all new orders
* When active: cancels pending tasks

### Safety gates (Chapter 67)

Verify conditions before real orders:
* Data freshness
* Connection state
* Balance verification
* Risk limits
* Kill switch status

## Education

### Why preservation comes first

* Drawdowns are harder to recover as they grow
* 50% loss requires 100% gain to recover
* Capital preservation enables survival through bad seasons

### Relationship between position sizing and risk

* Larger position sizes → larger drawdowns
* Larger drawdowns → higher risk of ruin
* Appropriate sizing → sustainable trading

### Recovery math

| Drawdown | Required gain to recover |
|----------|-------------------------|
| 10% | 11% |
| 20% | 25% |
| 30% | 43% |
| 40% | 67% |
| 50% | 100% |

## Protection of essential funds

Before real trading:

1. Confirm funds are not essential (not needed for living expenses)
2. Accept risk warning
3. Complete paper trading phase first

The application must recommend paper trading for users who cannot afford losses.

## What we never do

* Offer credit, leverage, or margin as solutions
* Enable real trading without confirmation
* Allow any component to disable protection mechanisms

## Checklist

* [x] Risk manager enforces rules
* [x] Kill switch available everywhere
* [x] Safety gates verify conditions
* [x] No component can disable protection
* [x] Beginner education included
* [x] Essential funds protection

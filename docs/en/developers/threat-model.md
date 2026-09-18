# Threat Model

## Objective

Identify security and financial risks in Crypto Trading Lab and document mitigations.

## Assets to Protect

1.  **User capital** - Financial safety is the highest priority
2.  **User credentials** - Exchange API keys and account access
3.  **Research data** - Historical data, strategy logic, results
4.  **System integrity** - Application stability during errors

## Trust Boundaries

```
┌─────────────────┐
│    User Input   │ ← Untrusted (user decisions)
└────────┬────────┘
         │
┌────────▼────────┐
│   Application   │ ← Partially trusted (our code)
└────────┬────────┘
         │
┌────────▼────────┐
│  System Keyring │ ← Trusted (OS security)
└────────┬────────┘
         │
┌────────▼────────┐
│   Exchange API  │ ← External (network)
└─────────────────┘
```

## Threat Analysis

### Credential Theft (STRIDE: T)

* **Risk**: API keys exposed in logs or configuration files
* **Impact**: Unauthorized trading, financial loss
* **Mitigation**:
    - Keys stored in system keyring only
    - All logs redact sensitive data
    - No credentials in version control

### Incorrect Execution (STRIDE: I)

* **Risk**: Order executes at unintended price or quantity
* **Impact**: Financial loss
* **Mitigation**:
    - Safety gates validate before transmission
    - Paper trading validates logic first
    - Kill switch allows immediate halt

### Strategy Overfitting (STRIDE: N/A - Financial Risk)

* **Risk**: Strategy works on historical data only
* **Impact**: Losses in live trading
* **Mitigation**:
    - Backtesting requires out-of-sample testing
    - Robustness checks (Monte Carlo, walk-forward)
    - Qualification process (Chapter 66)

### Data Integrity (STRIDE: R)

* **Risk**: Market data corrupted or incomplete
* **Impact**: Incorrect decisions
* **Mitigation**:
    - SQLite constraints prevent invalid candles
    - Data freshness checks in safety gates
    - Validation on CSV import

### Unintended Trading (STRIDE: N/A - Financial Risk)

* **Risk**: Strategy makes errors due to bug
* **Impact**: Financial loss
* **Mitigation**:
    - Paper trading default
    - Risk manager limits exposure
    - Real trading requires explicit enable

### Key Loss (STRIDE: A)

* **Risk**: API keys lost or inaccessible
* **Impact**: Can't withdraw funds
* **Mitigation**:
    - Export credentials option
    - Regular backup reminders
    - Keyring fallback to file (encrypted)

## Risk Prioritization

| Risk | Impact | Likelihood | Priority |
|------|--------|------------|----------|
| Credential theft | High | Medium | 1 |
| Unintended trading | High | Low | 1 |
| Data integrity | High | Low | 2 |
| Strategy overfitting | High | High | 2 |
| Key loss | Medium | Low | 3 |

## Security Checklist

* [x] Credentials never in plain text
* [x] All API calls use HTTPS
* [x] Kill switch blocks all orders when active
* [x] Safety gates validate risk limits
* [x] Real trading requires explicit user confirmation
* [x] Paper trading is default mode
* [x] All errors logged without exposing credentials

## Emergency Procedures

1.  **Activate kill switch**: Stops all trading
2.  **Review logs**: Check for error patterns
3.  **Disable real trading**: Switch to paper mode
4.  **Contact support**: If credentials may be compromised
5.  **Rotate credentials**: Revoke and regenerate API keys

## Assumptions

* System keyring is secure
* Internet connection is encrypted
* User operates on secure device
* Exchange APIs are reliable

## Limitations

* Cannot prevent user from overriding safety
* Cannot predict market crashes
* Does not provide financial advice
* Paper trading differs from reality

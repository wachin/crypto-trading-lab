# Live market data, testnet and real trading — status and plan

This document records **what is not built yet** and why, so nobody can
mistake the current laboratory for a live trading system. Real trading is
**disabled by default** and stays that way until every item below is
implemented, tested and documented (ROADMAP chapters 26.2, 27, 56, 68).

> Honest summary: today the application can download history, replay it,
> research it and paper-trade it. It **cannot** stream live prices and it
> must not touch a real account.

## 1. Where the data comes from today

| Source | State | Notes |
|---|---|---|
| CSV import | Implemented | chapter 28, with validation and a pre-import summary |
| Binance Spot public REST (download) | Implemented | `market_data/historical.py`, stdlib only, versioned datasets |
| Paper trading over a replayed dataset | Implemented | `paper_session.py`, chapter 57 |
| Continuous WebSocket stream | **Not implemented** | chapter 26.2 |
| Coinbase adapter | **Implemented** | chapter 26.3, read-only public data |
| CCXT adapter | **Implemented** | `exchanges/ccxt/adapter.py`, multiple exchanges |

## 2. The pipeline a live system needs

```text
Exchange
   ↓  WebSocket (public streams)
Market data collector ── retry/backoff ── circuit breaker
   ↓
Data validator (stale data, gaps, out-of-order ticks)
   ↓
Strategy (signals at bar close only)
   ↓
Risk manager (chapter 58)  ← strategies can never bypass it
   ↓
Paper execution (chapter 56/57)
   ↓
Paper account ── journal (chapter 79)
```

Every arrow above exists today **except** the WebSocket collector. The
retry/backoff/circuit-breaker layer and the staleness detector are now
implemented in `exchanges/ccxt/adapter.py` and `connection_manager.py`
and integrated into the CCXT adapter.
```

## 3. Required before any live data

- [ ] WebSocket client for Binance public streams (klines, trades).
- [x] Reconnection with exponential backoff and a circuit breaker. (Implemented in `exchanges/ccxt/adapter.py` and `connection_manager.py`)
- [x] Rate-limit accounting shared by REST and WebSocket. (Implemented in `exchanges/ccxt/adapter.py` and `rate_limiter.py`)
- [ ] Clock synchronisation against the exchange server time.
- [x] Stale-data detection that halts strategy evaluation. (Implemented in `connection_manager.py` and `exchanges/ccxt/adapter.py`)
- [ ] Out-of-order and duplicate tick handling.
- [ ] Persisted feed health metrics.

None of these need a new dependency: a WebSocket client can be written on
the standard library, but the dependency STOP rule (AGENTS.md §2) must be
re-checked first if a library is preferred.

## 4. Required before testnet

- [ ] Credential storage verified end to end (keyring, chapter 9).
- [x] Binance Spot Testnet endpoints and a separate environment key. (Implemented in `exchanges/binance/config.py` and `exchanges/binance/adapter.py`)
- [x] Order placement, cancellation and reconciliation against balances. (Implemented in `exchanges/binance/adapter.py`)
- [x] Idempotency identifiers and duplicate-order prevention (chapter 30). (Implemented in `exchanges/binance/adapter.py`)
- [x] Complete pre-trade pipeline: tick size, step size, min notional, risk limits, data freshness (chapter 30). (Implemented in `exchanges/binance/adapter.py`)
- [x] Audit trail for every order and every rejection (chapter 10). (Implemented in `exchanges/binance/adapter.py`)

## 5. Required before real money (chapter 68)

- [ ] Explicit, deliberate activation flow that cannot be triggered by
      accident (no environment variable, no config default).
- [ ] Strategy qualification (chapter 66) passed and recorded.
- [ ] Independent review of the strategy's out-of-sample and robustness
      evidence, with the validity dashboard fully green — including
      liquidity realism, which is currently reported as unmet.
- [ ] Kill switch tested against a live account.
- [ ] Position and loss limits validated with real fills.
- [ ] Confirmation that the capital at risk is money the user can afford
      to lose. The application will keep repeating this, not hide it.

## 6. What the user should do meanwhile

1. Learn in the Learning Center (levels 1 to 3).
2. Download a dataset and study its quality.
3. Research a hypothesis in the Research Wizard and read the validity
   dashboard honestly.
4. Paper-trade the surviving idea and read the trading journal trade by
   trade.
5. Accept that the honest answer may be “no edge exists” — and that this
   protects capital.

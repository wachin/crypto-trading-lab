# ADR 0001 — Exchange adapter spike: port, MockExchange, CCXT adapter

- Status: accepted (spike)
- Date: 2026-09-06
- Roadmap anchors: chapters 6 (architecture), 7 (domain models), 26 (adapters), 27 (states, partial), 30 (precision, partial), 14.3 (contract tests), 15 (packaging)
- Reference study: Part D of `docs/en/developers/reference-projects.md`

## Context

Chapter 26 requires an `ExchangeAdapter` interface with separate
operations for markets, tickers, candles, four subscription kinds,
balances, orders, order creation/cancellation, order updates, and API
permissions. Chapter 6.1 separates execution from research/risk;
chapter 7 mandates `Decimal` money and UTC timestamps; chapter 14.3
requires a common contract-test suite for every adapter; chapter 14
forbids real network calls in automated tests. Phase 2 of chapter 69
makes MockExchange the first adapter to implement.

## Decision

### 1. Hexagonal port, domain-owned

`ExchangeAdapter` (ABC) lives in `src/crypto_trading_lab/exchanges/base/`
and is owned by the application. Exchange specifics stay behind it; no
CCXT type crosses into the domain (chapter 6/7).

### 2. CCXT is injected, never imported

`CcxtExchangeAdapter` accepts any duck-typed client (`CcxtClient`
protocol). The package imports — and the full test suite runs — with
**ccxt not installed** (verified). Error mapping uses exception class
*names* (`RateLimitExceeded` → `AdapterRateLimited`, …), verified
against the study of the actual ccxt source, so real ccxt and test
fakes behave identically. This also keeps chapter 14's no-network rule
trivially satisfied and defers the chapter 4 dependency decision
(no `python3-ccxt` Debian package exists; PyPI-only — see the CCXT
study) until the app actually needs live data.

### 3. Read-only is the default; trading is an explicit opt-in

Both adapters strip the `TRADING` capability unless constructed with
`allow_trading=True`; order operations then raise
`AdapterNotSupported`. This encodes the capital-protection posture
(chapters 60/61) at the adapter boundary from day one.

### 4. `Decimal` everywhere, aware-UTC everywhere, validation in the model

Money/price/quantity are `Decimal` (no float anywhere in the critical
path; the CCXT adapter converts with `Decimal(str(value))`, never
`Decimal(float)`). Timestamps must be timezone-aware **UTC** — naive
datetimes raise `TypeError`, non-zero offsets raise `ValueError`
(chapter 7: "UTC internally; local timezone only for presentation").
Domain models validate themselves (`Candle` rejects high/low
violations, inverted times, negative volume; `Ticker` rejects
bid > ask; `Market` rejects negative fees).

### 5. Precision normalization stays in the adapter (chapter 30)

ccxt `precisionMode` is normalized inside `CcxtExchangeAdapter`:
`DECIMAL_PLACES` is taken directly; `TICK_SIZE` markets derive decimal
places from the smallest increment. The domain sees one convention.

### 6. Connection states modeled now, full machine later (chapter 27)

All ten chapter-27 states exist as an enum, each with a
beginner-facing explanation (chapter 27's UI requirement). Errors map
to states via `suggest_connection_state` (rate-limited → `RATE_LIMITED`,
network → `RECONNECTING`, auth → `ERROR`). Backoff, jitter, circuit
breaker, and WebSocket reconnection are **out of scope** for this
spike and documented as such.

### 7. Contract tests are the adapter quality gate (chapter 14.3)

`tests/exchanges/contract.py::AdapterContract` is a suite both adapters
pass: lifecycle/states, normalized market data, chronological valid
candles, subscription delivery, read-only default, order+update flow,
permission probing. Suite hooks (`make_adapter`, `trigger_ticker`,
`cleanup`) hide the mechanical difference between a publish-driven mock
and a delegation adapter.

### 8. MockExchange is deterministic and scriptable (chapter 26.1)

Everything chapter 26.1 lists is implementable via explicit scripting:
`queue_error`, `queue_rejection`, `queue_partial_fill`,
`simulate_disconnection`, rate limits (sliding window), latency
(monkeypatched sleep in tests — no real sleeps), slippage, and candle
replay (`replay_candles`) via `publish_*` handlers. Seeded RNG;
`generate_candles` provides deterministic fixtures. The mock refuses
orders the local account cannot cover (`AdapterInsufficientFunds`) —
balances never go silently negative.

## Consequences

- The chapter 26 operation surface is proven feasible with 83 passing
  tests (81 passed, 2 conditional skips in read-only suites that enable
  trading).
- Binance Spot Testnet endpoints are centralized in
  `exchanges/binance/config.py` (26.2: "do not scatter endpoint
  strings"); futures environments intentionally absent.
- Live streaming (`ccxt.pro watch_*`), the asyncio→Qt bridge
  (chapter 12), backoff/circuit-breaker (chapter 27), order-book/trade
  domain models, and credential-store integration (chapter 9) are
  deliberately **not** in this spike; the handler registries and
  `dispatch_ticker` seam are where they attach.
- `pyproject.toml` scaffolding (setuptools, src layout) exists with
  `ccxt` as an *optional* extra; chapter 15's full packaging (entry
  points, translations, icons) remains open.

## Verification

```bash
python3 -m pytest tests/ -q      # 81 passed, 2 skipped
python3 -m compileall -q src/ tests/
PYTHONPATH=src python3 -c "import crypto_trading_lab.exchanges.ccxt"  # works without ccxt
```

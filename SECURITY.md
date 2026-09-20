# Security policy

Crypto Trading Lab handles *simulated* money and, eventually, API
credentials. Security and honesty about what is protected are part of the
product, not an afterthought.

## Current posture

- **Real trading is disabled by default** and gated behind the chapter-68
  activation flow. See [`docs/en/developers/live-trading-roadmap.md`](docs/en/developers/live-trading-roadmap.md).
- **No real credentials** belong in this repository, its tests or its
  documentation. The test suite uses fakes and a memory-backed credential
  store only.
- API keys, when used, are stored through the keyring-backed credential
  store and **redacted in every log**.
- Withdrawals are blocked at the adapter layer.
- The full threat analysis (key theft, secrets in logs, malicious
  strategy files, malformed CSV, stale data, duplicate orders, accidental
  real trading, misleading backtests, …) lives in
  [`docs/en/developers/threat-model.md`](docs/en/developers/threat-model.md).

## Reporting a vulnerability

Please **do not open a public issue** for a security problem. Instead,
contact the maintainer privately through GitHub
([@wachin](https://github.com/wachin)) and include:

- what the problem is and where,
- exact steps or a command to reproduce it,
- the impact you believe it has,
- any suggested fix.

You will get an acknowledgment, an honest assessment of severity, and
credit in the fix unless you prefer otherwise.

## Out of scope

This is a research and education project in alpha. The following are
known and documented limitations rather than vulnerabilities:

- backtest results can be misleading if the assumptions are ignored
  (that is why every report carries warnings and an evidence level);
- no continuous live-data feed exists yet;
- no liquidity/market-impact model exists yet, and the validity dashboard
  reports that as an unmet check on purpose.

Reports that contradict a documented limitation are welcome as
*roadmap discussions*, not as security advisories.

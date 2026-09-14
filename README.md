# Crypto Trading Lab

Crypto Trading Lab is a personal idea:

**Crypto Trading Lab → plataforma de investigación, backtesting, paper trading y posteriormente trading real.**

**Status: early development.** This repository is being built AI-agent-first: a complete written specification drives the work, and an AI Agent implements it phase by phase. Real trading is disabled by default and will remain behind strict safety gates.

## Vision and mission

Some people genuinely make a living from the cryptocurrency markets — not by luck or hope, but by studying, measuring, and surviving bad seasons. Crypto Trading Lab exists to give its user a real, honest chance of becoming one of them.

The farmer's truth applies: no one can promise in which year it will rain well. This program can never **guarantee** gains. What it can do is maximize the user's real chances: search for a genuine, measurable edge with scientific discipline, validate it out-of-sample, protect the capital, and tell the truth when no edge exists.

Priority order, non-negotiable:

1. **Survive** — never risk money needed to live.
2. **Validate** — only statistically defensible edges.
3. **Earn** — attempt real profits only after (1) and (2).

The method follows the discipline of *Advances in Financial Machine
Learning* (Marcos López de Prado, Wiley, 2018) — cited here by
bibliographic reference only. Its techniques are implemented from the study notes
in `docs/en/developers/reference-projects.md` and the MIT-licensed
exercise repository under `external/`, with attribution.

## What the finished program will be used for

Once completed, Crypto Trading Lab will let you:

- visualize cryptocurrency markets with candlestick charts;
- download and store historical market data;
- calculate technical indicators (SMA, EMA, RSI, MACD, Bollinger Bands, and more);
- create rule-based trading strategies without writing code;
- run backtests against historical data, with realistic costs and bias prevention;
- validate strategies statistically (out-of-sample testing, walk-forward analysis, overfitting detection);
- practice with paper trading using simulated money;
- analyze performance and risk through honest metrics and reports;
- qualify strategies through a mandatory promotion pipeline before any real trading is ever considered;
- learn from scratch with built-in lessons, a glossary, and tutorials for complete beginners.

## Current state

Implemented so far (each with passing tests):

- validated domain models (Decimal money, UTC timestamps, self-checking entities);
- exchange adapter port + MockExchange + CCXT adapter (read-only by default, contract tests);
- credential store abstraction (system keyring, in-memory, mock; withdrawal permissions blocked);
- logging with secret redaction and an audit trail;
- SQLite/SQLAlchemy persistence with candle repository;
- CSV import with full validation and pre-import summary;
- indicators: SMA, EMA, RSI, Bollinger Bands, ATR, ROC;
- PyQtGraph candlestick charts (zoom, crosshair with OHLCV readout, gap-aware time axis);
- deterministic backtesting engine (commissions, slippage, spread, next-open execution, no look-ahead);
- strategies: SMA crossover, buy-and-hold, null baseline;
- beginner documentation (start guide, glossary, indicators explained);
- Learning Center shell with the 20-lesson path.

## How to start the creation process

This repository is ready for an AI Agent to initiate or continue the creation of the program. No programming knowledge is required.

1. Open an AI Agent (such as opencode) inside this repository.
2. Tell it to read `AGENT-HANDOFF.md` (it explains where development
   stands and what comes next). For a brand-new start, use `GENESIS.md`.
3. The Agent will continue building step by step, following the
   specification in `ROADMAP.md`.

### After migrating to a new repository

Verify the migration is clean, then let the Agent continue:

```bash
# 1. Install dependencies if needed (all Debian packages):
sudo apt install python3-pyqt6 python3-pyqtgraph python3-sqlalchemy \
                 python3-platformdirs python3-pytest qt6-l10n-tools

# 2. Add the reference submodules (see "Reference submodules" below).

# 3. Verify the test baseline:
QT_QPA_PLATFORM=offscreen python3 -m pytest tests/ -q
# → expect: 229 passed, 2 skipped
```

In the new repo, open the AI Agent and tell it: **"read
AGENT-HANDOFF.md"** — development continues exactly where it left
off.

## Repository contents

| Path | Purpose |
|------|---------|
| `AGENT-HANDOFF.md` | Migration guide and continuation instructions — start here |
| `AGENTS.md` | Ground rules every AI Agent must follow in this repository |
| `GENESIS.md` | The original first-session instruction (kept for fresh starts) |
| `ROADMAP.md` | The complete project specification (72 chapters in checklist format, for tracking progress) |
| `docs/` | Developer documentation: ADRs, reference-project studies, beginner guides |
| `src/` | Application source code (domain, adapters, security, logging, persistence, indicators, backtesting, UI) |
| `tests/` | Automated tests (unit, GUI, persistence, backtesting) |
| `external/` | Git submodules with reference projects studied during development (all open source) |
| `pyproject.toml` | Python packaging |

## Reference submodules

The `external/` directory contains open-source projects studied as
references during development (see `docs/en/developers/reference-projects.md`
for the conclusions). To clone this repository with all submodules:

```bash
git clone --recurse-submodules https://github.com/wachin/crypto-trading-lab
```

If you cloned without them, initialize and pull all submodules:

```bash
git submodule update --init --recursive
```

To add them individually to a fresh repository (complete list):

```bash
git submodule add https://github.com/freqtrade/freqtrade.git external/freqtrade
git submodule add https://github.com/hummingbot/hummingbot.git external/hummingbot
git submodule add https://github.com/jesse-ai/jesse.git external/jesse
git submodule add https://github.com/ccxt/ccxt.git external/ccxt
git submodule add https://github.com/polakowo/vectorbt.git external/vectorbt
git submodule add https://github.com/mementum/backtrader.git external/backtrader
git submodule add https://github.com/TA-Lib/ta-lib.git external/ta-lib
git submodule add https://github.com/fernandodelacalle/adv-financial-ml-marcos-exercises external/adv-financial-ml-marcos-exercises
```

## Running

```bash
# Tests (headless):
QT_QPA_PLATFORM=offscreen python3 -m pytest tests/ -q

# GUI:
PYTHONPATH=src python3 -m crypto_trading_lab
```

## Dependencies

All dependencies are Debian system packages (no venv needed):

```bash
sudo apt install python3-pyqt6 python3-pyqtgraph python3-sqlalchemy \
                 python3-platformdirs python3-pytest qt6-l10n-tools
```

## License

GPL-3.0

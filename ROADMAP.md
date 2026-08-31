# Project: Crypto Trading Lab

Act as a senior software architect, Python/PyQt6 developer, financial systems specialist, automated testing engineer, application security specialist, Debian packaging specialist, technical writer, and educator.

Design and develop a professional desktop application called:

# Crypto Trading Lab

Crypto Trading Lab will be an educational, research, simulation, and market-analysis platform for:

- visualizing cryptocurrency markets;
- downloading and storing historical data;
- displaying candlestick charts;
- calculating technical indicators;
- creating rule-based trading strategies;
- running backtests;
- performing paper trading;
- analyzing performance and risk;
- optionally connecting to cryptocurrency exchanges through adapters;
- learning how cryptocurrency markets work;
- teaching complete beginners how to use the application;
- allowing real trading only after strict safety mechanisms have been implemented and validated.

The application must never be presented as a tool that guarantees profits.

It must clearly explain that:

- cryptocurrency trading involves substantial risk;
- users can lose part or all of their capital;
- historical performance does not guarantee future results;
- paper trading does not reproduce every real-market condition;
- backtesting can produce misleading results if implemented incorrectly;
- the application is primarily an educational, research, simulation, and risk-management tool.

---

- [ ] # 1. Supported platforms and technologies

## 1.1 Supported platforms

The application must be developed primarily for:

- [ ] Debian 12 Bookworm;
- [ ] Debian 13;
- [ ] MX Linux;
- [ ] AV Linux MXe;
- [ ] Ubuntu;
- [ ] Ubuntu-based distributions;
- [ ] other Debian-based GNU/Linux distributions.

## 1.2 Main technologies

Main technologies:

- [ ] Python 3;
- [ ] PyQt6;
- [ ] SQLite;
- [ ] Qt Linguist;
- [ ] Qt translation tools;
- [ ] `pyproject.toml`;
- [ ] pytest;
- [ ] Debian `.deb` packaging;
- [ ] an architecture prepared for AppImage distribution.

The AppImage packaging process must remain separate from the official Debian package.

The project must be Free Software and use a Debian-compatible license, preferably:

```text
GPL-3.0-or-later
```

Do not use proprietary components or services that require mandatory payment.

---

- [ ] # 2. Debian dependency priority

Prioritize dependencies available in the official Debian 12 repositories before adding dependencies from PyPI.

Before choosing any dependency:

1. confirm whether it exists in Debian 12;
2. confirm its exact Debian package name;
3. verify its version;
4. verify its license;
5. determine whether it is suitable for runtime, development, packaging, or optional use;
6. avoid adding a PyPI dependency when the Python standard library, Qt, or an official Debian package already solves the problem adequately.

## 2.1 Graphical interface

Evaluate and use the following Debian packages where appropriate:

- [ ] `python3-pyqt6`
- [ ] `python3-pyqt6.qtcharts`
- [ ] `python3-pyqt6.qtwebsockets`
- [ ] `python3-pyqt6.qtsvg`
- [ ] `python3-pyqt6.qtdesigner`
- [ ] `pyqt6-dev-tools`
- [ ] `python3-superqt`

## 2.2 Charting libraries

Research and evaluate:

- [ ] `python3-pyqtgraph`
- [ ] `python3-pyqt6.qtcharts`
- [ ] `python3-matplotlib`

- [ ] Create an internal chart abstraction so that the chart backend can be replaced without modifying the financial domain or strategy logic.

Initial preference:

- [ ] PyQtGraph for real-time charts, candlesticks, volume, and fast updates;
- [ ] Matplotlib for static reports, statistical charts, and exported graphics;
- [ ] Qt Charts where it is suitable and does not create performance limitations.

- [ ] Do not use Qt WebEngine for the main charts unless there is a documented technical justification.

## 2.3 Data processing and analysis

Evaluate:

- [ ] `python3-numpy`
- [ ] `python3-pandas`
- [ ] `python3-scipy`
- [ ] `python3-statsmodels`
- [ ] `python3-sklearn`
- [ ] `python3-numba`

Use:

- [ ] NumPy for numerical arrays and vectorized calculations;
- [ ] pandas for time series, tables, imports, exports, and analysis;
- [ ] SciPy when advanced statistical or numerical functions are required;
- [ ] statsmodels when statistically justified;
- [ ] scikit-learn only for optional research experiments;
- [ ] Numba only as an optional performance optimization.

- [ ] Machine learning must not be a mandatory part of the initial application.
- [ ] Do not describe machine learning as a method that can predict the market with certainty.

## 2.4 Networking

Evaluate:

- [ ] `python3-aiohttp`
- [ ] `python3-websockets`
- [ ] `python3-requests`
- [ ] `python3-requests-cache`
- [ ] `python3-ratelimiter`

Analyze whether the application should use:

- [ ] 1. `aiohttp` for REST and WebSocket communication;
- [ ] 2. `websockets` for WebSocket connections;
- [ ] 3. `QNetworkAccessManager` and `QWebSocket` for Qt-native networking.

- [ ] Create interfaces that remain independent of the specific transport implementation.
- [ ] Never block the Qt main thread.

## 2.5 Persistence and validation

Evaluate:

- [ ] `python3-sqlalchemy`
- [ ] `python3-pydantic`
- [ ] `python3-dateutil`
- [ ] `python3-platformdirs`
- [ ] `python3-yaml`
- [ ] `python3-jsonschema`

- [ ] SQLite must be the default database.
- [ ] Do not make PostgreSQL a requirement for the desktop application.
- [ ] PostgreSQL may be considered as a future optional backend, but it must not be part of the MVP runtime requirements.

## 2.6 Security

Evaluate:

- [ ] `python3-keyring`
- [ ] `python3-cryptography`

API keys and secrets must never be stored:

- [ ] in plain text;
- [ ] inside the Git repository;
- [ ] in `.json` files;
- [ ] in `.yaml` files;
- [ ] in `.toml` files;
- [ ] in `.ini` files;
- [ ] in debug logs;
- [ ] in error reports;
- [ ] in SQLite without proper protection.

- [ ] Use the operating system credential store through `keyring`.

The application must also work without credentials for:

- [ ] public market data;
- [ ] imported CSV data;
- [ ] offline demonstrations;
- [ ] backtesting;
- [ ] paper trading;
- [ ] educational exercises.

## 2.7 Testing and code quality

Evaluate:

- [ ] `python3-pytest`
- [ ] `python3-pytest-asyncio`
- [ ] `python3-pytest-cov`
- [ ] `python3-requests-mock`
- [ ] `python3-freezegun`
- [ ] `python3-flake8`
- [ ] `python3-mypy`
- [ ] `python3-bandit`
- [ ] `python3-black`
- [ ] `python3-isort`

Classify each dependency as one of the following:

- [ ] required runtime dependency;
- [ ] recommended runtime dependency;
- [ ] optional dependency;
- [ ] development-only dependency;
- [ ] packaging-only dependency;
- [ ] available only from PyPI;
- [ ] unnecessary because the standard library or Qt is sufficient.

- [ ] Do not add external dependencies unnecessarily.

---

- [ ] # 3. Mandatory project principles

The application must comply with the following rules:

- [ ] 1. Paper trading must be the default mode.
- [ ] 2. Real trading must be disabled in the initial build.
- [ ] 3. Futures must not be implemented in the MVP.
- [ ] 4. Margin trading must not be implemented in the MVP.
- [ ] 5. Leverage must not be implemented in the MVP.
- [ ] 6. The MVP must support spot markets only.
- [ ] 7. Martingale strategies must not be implemented.
- [ ] 8. The application must never double position size automatically after a loss.
- [ ] 9. The application must never promise profits.
- [ ] 10. The application must never request API withdrawal permissions.
- [ ] 11. The application must reject or warn about API keys with withdrawal permissions.
- [ ] 12. Strategies must never bypass the central risk manager.
- [ ] 13. Every order must pass through validation before being submitted.
- [ ] 14. The application must operate fully without API keys.
- [ ] 15. Automated tests must never use real funds.
- [ ] 16. The application must not implement market manipulation.
- [ ] 17. The application must not implement spoofing.
- [ ] 18. The application must not implement wash trading.
- [ ] 19. The application must not implement front-running.
- [ ] 20. The application must not abuse exchange APIs.
- [ ] 21. User strategy rules must not execute arbitrary Python code.
- [ ] 22. Do not use `eval()`.
- [ ] 23. Do not use `exec()`.
- [ ] 24. Do not dynamically import untrusted strategy code.
- [ ] 25. Educational explanations must accompany complex financial concepts.
- [ ] 26. Every financial metric must include a plain-language explanation.
- [ ] 27. Every warning must be understandable to a complete beginner.

---

- [ ] # 4. Architecture

Use a modular, maintainable, testable architecture.

- [ ] Propose a Clean Architecture or Hexagonal Architecture adapted to a PyQt6 desktop application.

Clearly separate:

- [ ] financial domain;
- [ ] application use cases;
- [ ] market-data providers;
- [ ] exchange adapters;
- [ ] strategy engine;
- [ ] backtesting engine;
- [ ] paper-trading engine;
- [ ] execution engine;
- [ ] order management;
- [ ] risk management;
- [ ] portfolio management;
- [ ] persistence;
- [ ] PyQt6 interface;
- [ ] configuration;
- [ ] security;
- [ ] reporting;
- [ ] internationalization;
- [ ] beginner education;
- [ ] user documentation.

Suggested structure:

- [ ] `crypto-trading-lab/`
  - [ ] `pyproject.toml`
  - [ ] `README.md`
  - [ ] `LICENSE`
  - [ ] `CHANGELOG.md`
  - [ ] `CONTRIBUTING.md`
  - [ ] `SECURITY.md`
  - [ ] `CODE_OF_CONDUCT.md`
  - [ ] `src/`
    - [ ] `crypto_trading_lab/`
      - [ ] `__init__.py`
      - [ ] `__main__.py`
      - [ ] `application.py`
      - [ ] `domain/`
        - [ ] `entities/`
        - [ ] `value_objects/`
        - [ ] `services/`
        - [ ] `exceptions/`
        - [ ] `protocols/`
      - [ ] `use_cases/`
      - [ ] `market_data/`
        - [ ] `providers/`
        - [ ] `normalization/`
        - [ ] `aggregation/`
        - [ ] `cache/`
      - [ ] `exchanges/`
        - [ ] `base/`
        - [ ] `binance/`
        - [ ] `coinbase/`
        - [ ] `mock/`
      - [ ] `indicators/`
      - [ ] `strategies/`
      - [ ] `backtesting/`
      - [ ] `paper_trading/`
      - [ ] `execution/`
      - [ ] `risk/`
      - [ ] `portfolio/`
      - [ ] `analytics/`
      - [ ] `persistence/`
        - [ ] `database/`
        - [ ] `repositories/`
        - [ ] `migrations/`
      - [ ] `security/`
      - [ ] `configuration/`
      - [ ] `reporting/`
      - [ ] `education/`
        - [ ] `lessons/`
        - [ ] `glossary/`
        - [ ] `tutorials/`
        - [ ] `quizzes/`
        - [ ] `examples/`
      - [ ] `infrastructure/`
      - [ ] `ui/`
        - [ ] `main_window/`
        - [ ] `dashboards/`
        - [ ] `charts/`
        - [ ] `dialogs/`
        - [ ] `models/`
        - [ ] `delegates/`
        - [ ] `workers/`
        - [ ] `education/`
        - [ ] `resources/`
        - [ ] `generated/`
      - [ ] `i18n/`
        - [ ] `en/`
        - [ ] `es/`
        - [ ] `translations/`
        - [ ] `README.md`
  - [ ] `tests/`
    - [ ] `unit/`
    - [ ] `integration/`
    - [ ] `gui/`
    - [ ] `contract/`
    - [ ] `regression/`
    - [ ] `security/`
    - [ ] `education/`
    - [ ] `fixtures/`
  - [ ] `docs/`
    - [ ] `en/`
      - [ ] `beginners/`
      - [ ] `user-guide/`
      - [ ] `developers/`
      - [ ] `reference/`
    - [ ] `es/`
      - [ ] `beginners/`
      - [ ] `user-guide/`
      - [ ] `developers/`
      - [ ] `reference/`
  - [ ] `examples/`
  - [ ] `scripts/`
  - [ ] `data/`
    - [ ] `samples/`
  - [ ] `debian/`
  - [ ] `packaging/`
    - [ ] `appimage/`
  - [ ] `.github/`
    - [ ] `workflows/`

- [ ] The `ui/generated` directory may contain files generated from Qt Designer.
- [ ] Do not place business logic inside generated interface files.

---

- [ ] # 5. Domain models

Implement explicit, strongly validated models for:

- [ ] Exchange;
- [ ] Market;
- [ ] TradingPair;
- [ ] Asset;
- [ ] Candle;
- [ ] Trade;
- [ ] OrderBook;
- [ ] OrderBookLevel;
- [ ] Ticker;
- [ ] Balance;
- [ ] Position;
- [ ] Portfolio;
- [ ] Order;
- [ ] OrderRequest;
- [ ] OrderResult;
- [ ] Fill;
- [ ] Fee;
- [ ] Strategy;
- [ ] StrategySignal;
- [ ] RiskDecision;
- [ ] Backtest;
- [ ] BacktestResult;
- [ ] PaperAccount;
- [ ] PerformanceMetrics.

Use:

- [ ] `Decimal` for money;
- [ ] `Decimal` for prices;
- [ ] `Decimal` for quantities;
- [ ] `Decimal` for commissions;
- [ ] `Decimal` for balances;
- [ ] normalized timestamps;
- [ ] UTC internally;
- [ ] the local timezone only for presentation;
- [ ] dataclasses or Pydantic models where appropriate.

- [ ] Do not use `float` for critical monetary calculations.
- [ ] Every exchange adapter must normalize exchange-specific data into common domain models.

---

- [ ] # 6. Market precision and exchange rules

Every exchange adapter must retrieve and respect:

- [ ] minimum quantity;
- [ ] minimum order value;
- [ ] tick size;
- [ ] step size;
- [ ] price precision;
- [ ] quantity precision;
- [ ] supported order states;
- [ ] supported order types;
- [ ] known fees;
- [ ] rate limits;
- [ ] timestamp formats;
- [ ] time synchronization requirements.

Before creating an order:

- [ ] 1. normalize the price;
- [ ] 2. normalize the quantity;
- [ ] 3. apply tick-size rules;
- [ ] 4. apply step-size rules;
- [ ] 5. verify minimum notional value;
- [ ] 6. estimate fees;
- [ ] 7. verify available balance;
- [ ] 8. verify risk limits;
- [ ] 9. verify market-data freshness;
- [ ] 10. verify connection state;
- [ ] 11. prevent duplicate orders;
- [ ] 12. create an idempotency identifier;
- [ ] 13. produce a beginner-readable explanation of any rejection.

---

- [ ] # 7. Market-data sources and exchange adapters

Create an `ExchangeAdapter` interface or equivalent.

It must define separate operations for:

- [ ] retrieving markets;
- [ ] retrieving tickers;
- [ ] retrieving historical candles;
- [ ] subscribing to tickers;
- [ ] subscribing to candles;
- [ ] subscribing to trades;
- [ ] subscribing to the order book;
- [ ] retrieving balances;
- [ ] retrieving orders;
- [ ] creating an order;
- [ ] cancelling an order;
- [ ] receiving order updates;
- [ ] checking API permissions.

## 7.1 MockExchange

Implement a fully local provider for:

- [ ] automated tests;
- [ ] demonstrations;
- [ ] paper trading;
- [ ] historical replay;
- [ ] simulated failures;
- [ ] simulated disconnections;
- [ ] simulated latency;
- [ ] simulated slippage;
- [ ] partially filled orders;
- [ ] rejected orders;
- [ ] rate-limit simulations.

## 7.2 Binance Spot Testnet

Add initial support for Binance Spot Testnet using current official documentation.

- [ ] Endpoints must be configurable.
- [ ] Do not scatter endpoint strings throughout the codebase.

Include:

- [ ] REST;
- [ ] WebSocket;
- [ ] automatic reconnection;
- [ ] ping/pong handling;
- [ ] connection renewal;
- [ ] rate-limit management;
- [ ] time synchronization;
- [ ] out-of-order message detection;
- [ ] duplicate message tolerance;
- [ ] secure logging.

- [ ] Do not implement Binance Futures.

## 7.3 Coinbase

Initially add:

- [ ] public market data;
- [ ] an architecture prepared for Advanced Trade;
- [ ] clearly labeled experimental support.

- [ ] Document that the Coinbase sandbox may return static or predefined data and must not be treated as a realistic profitability simulation.
- [ ] Do not mix Coinbase-specific models with the central domain.

---

- [ ] # 8. Connection state management

Create a connection state machine with:

- [ ] DISCONNECTED
- [ ] CONNECTING
- [ ] AUTHENTICATING
- [ ] SUBSCRIBING
- [ ] CONNECTED
- [ ] DEGRADED
- [ ] RECONNECTING
- [ ] RATE_LIMITED
- [ ] ERROR
- [ ] STOPPED

Implement:

- [ ] exponential backoff with jitter;
- [ ] a maximum number of consecutive retries;
- [ ] a circuit breaker;
- [ ] stale-data detection;
- [ ] subscription recovery;
- [ ] reconciliation after reconnection;
- [ ] visible warnings when data is outdated.

- [ ] Never generate buy or sell signals from stale data.

Every connection state must have:

- [ ] a technical description;
- [ ] a beginner-friendly explanation;
- [ ] a visible status label;
- [ ] a troubleshooting link.

---

- [ ] # 9. Database

Use SQLite with SQLAlchemy.

The database must store:

- [ ] configured exchanges;
- [ ] markets;
- [ ] candles;
- [ ] trades;
- [ ] optional order-book snapshots;
- [ ] strategies;
- [ ] strategy parameters;
- [ ] backtest runs;
- [ ] simulated orders;
- [ ] fills;
- [ ] fees;
- [ ] simulated balances;
- [ ] positions;
- [ ] performance metrics;
- [ ] alerts;
- [ ] audit records;
- [ ] non-secret configuration;
- [ ] educational progress;
- [ ] completed lessons;
- [ ] glossary bookmarks;
- [ ] beginner tutorial progress.

- [ ] Do not store API keys in SQLite.

Enable where appropriate:

- [ ] foreign keys;
- [ ] indexes;
- [ ] transactions;
- [ ] WAL mode;
- [ ] migrations;
- [ ] backups;
- [ ] integrity checks.

- [ ] Design a retention policy to prevent uncontrolled database growth.

Include import and export support for:

- [ ] CSV;
- [ ] JSON;
- [ ] optional Parquet if an acceptable Debian dependency exists.

Exports must include:

- [ ] exchange;
- [ ] trading pair;
- [ ] interval;
- [ ] time range;
- [ ] timezone;
- [ ] format;
- [ ] schema version.

---

- [ ] # 10. Financial charts

Implement charts for:

- [ ] OHLC candlesticks;
- [ ] volume;
- [ ] price lines;
- [ ] moving averages;
- [ ] bands;
- [ ] RSI;
- [ ] MACD;
- [ ] entry points;
- [ ] exit points;
- [ ] stop-loss levels;
- [ ] take-profit levels;
- [ ] equity curves;
- [ ] drawdowns;
- [ ] return distributions.

Requirements:

- [ ] zoom;
- [ ] panning;
- [ ] crosshair;
- [ ] OHLC information under the cursor;
- [ ] interval selection;
- [ ] auto-scaling;
- [ ] optional logarithmic scale;
- [ ] incremental updates;
- [ ] do not rebuild the entire chart on every tick;
- [ ] limit the number of visible points;
- [ ] separate chart data from visual representation;
- [ ] handle missing time intervals correctly.

- [ ] Do not update widgets directly from worker threads.
- [ ] Workers must emit Qt signals containing immutable data or safe copies.

Each chart must include an optional beginner explanation panel describing:

- [ ] what the chart shows;
- [ ] how to read it;
- [ ] what beginners often misunderstand;
- [ ] what the chart cannot predict;
- [ ] a simple example;
- [ ] a glossary link.

---

- [ ] # 11. Technical indicators

Initially implement:

- [ ] SMA;
- [ ] EMA;
- [ ] RSI;
- [ ] MACD;
- [ ] Bollinger Bands;
- [ ] ATR;
- [ ] ROC;
- [ ] historical volatility;
- [ ] average volume;
- [ ] rolling highs and lows;
- [ ] drawdown.

Every indicator must:

- [ ] use a common interface;
- [ ] validate parameters;
- [ ] document its formula;
- [ ] describe its warm-up period;
- [ ] handle missing values;
- [ ] avoid look-ahead bias;
- [ ] support batch calculation;
- [ ] support incremental updates where practical;
- [ ] include tests using small datasets with manually verifiable results.

- [ ] Do not add dozens of indicators without tests.

Every indicator must also include beginner documentation:

- [ ] what it measures;
- [ ] what its name means;
- [ ] a plain-language explanation;
- [ ] common parameter values;
- [ ] typical misuse;
- [ ] limitations;
- [ ] a visual example;
- [ ] a warning that it does not guarantee future price movements.

---

- [ ] # 12. Strategies

Strategies must use explicit, testable, declarative rules.

Initial strategies:

- [ ] 1. moving-average crossover;
- [ ] 2. RSI with filters;
- [ ] 3. rolling high or low breakout;
- [ ] 4. Bollinger mean reversion as an educational example;
- [ ] 5. buy-and-hold benchmark;
- [ ] 6. a null strategy that never trades.

Each strategy must declare:

- [ ] name;
- [ ] version;
- [ ] description;
- [ ] parameters;
- [ ] compatible markets;
- [ ] required interval;
- [ ] required indicators;
- [ ] warm-up period;
- [ ] entry rules;
- [ ] exit rules;
- [ ] order type;
- [ ] position-sizing rules;
- [ ] stop-loss;
- [ ] take-profit;
- [ ] cooldown;
- [ ] invalidation conditions;
- [ ] beginner explanation;
- [ ] risk warnings;
- [ ] known weaknesses.

- [ ] Strategies generate signals but do not create orders directly.

Mandatory flow:

- [ ] Market data
- [ ]     → Strategy
- [ ]     → Signal
- [ ]     → Portfolio and Risk Manager
- [ ]     → Approved Order Request
- [ ]     → Execution Engine
- [ ]     → Broker or Exchange

- [ ] No strategy may communicate directly with an exchange API.

---

- [ ] # 13. Visual strategy builder

Create a basic no-code strategy builder using blocks or forms for:

- [ ] indicator;
- [ ] operator;
- [ ] value;
- [ ] crossover;
- [ ] AND condition;
- [ ] OR condition;
- [ ] entry;
- [ ] exit;
- [ ] stop-loss;
- [ ] take-profit;
- [ ] time filter;
- [ ] volatility filter;
- [ ] cooldown.

- [ ] Do not use `eval()`.

- [ ] Convert rules into a validated expression tree.

Allow users to:

- [ ] save;
- [ ] duplicate;
- [ ] export;
- [ ] import;
- [ ] validate;
- [ ] view a natural-language explanation;
- [ ] view a beginner-friendly explanation;
- [ ] view warnings about possible overfitting.

- [ ] Use a versioned schema for strategy files.

---

- [ ] # 14. Backtesting

The backtesting engine must be deterministic.

It must include:

- [ ] initial capital;
- [ ] commissions;
- [ ] slippage;
- [ ] spread;
- [ ] simulated latency;
- [ ] partial execution;
- [ ] rejected orders;
- [ ] tick size;
- [ ] step size;
- [ ] minimum order value;
- [ ] missing data;
- [ ] chronological data separation;
- [ ] warm-up periods;
- [ ] time-ordered events;
- [ ] a buy-and-hold benchmark.

Avoid:

- [ ] look-ahead bias;
- [ ] survivorship bias where applicable;
- [ ] using a known closing price to execute at that same close without an explicit model;
- [ ] optimizing and evaluating over the same period;
- [ ] ignoring commissions;
- [ ] assuming all orders execute instantly.

Implement at least two execution models:

- [ ] 1. execution at the opening of the next candle;
- [ ] 2. a documented conservative intrabar execution model.

- [ ] When a candle reaches both stop-loss and take-profit during the same interval, use a configurable conservative policy and record the decision.

Every backtest result must include a beginner-oriented explanation covering:

- [ ] what was tested;
- [ ] what assumptions were made;
- [ ] why results can be misleading;
- [ ] what commissions and slippage mean;
- [ ] why real results may differ;
- [ ] why a profitable backtest does not guarantee future profits.

---

- [ ] # 15. Data splitting

Allow chronological division into:

- [ ] training or strategy-design data;
- [ ] validation data;
- [ ] out-of-sample test data.

- [ ] Add walk-forward analysis after the MVP.
- [ ] Never randomly shuffle time-series data for financial strategy evaluation.
- [ ] Display a warning when the user tries to evaluate a strategy using the same period used for optimization.
- [ ] Explain in beginner language why chronological separation matters.

---

- [ ] # 16. Parameter optimization

Initially include:

- [ ] limited grid search;
- [ ] limited random search.

- [ ] Do not include aggressive automatic optimization in the MVP.

Requirements:

- [ ] strict limits on the number of combinations;
- [ ] a cancel button;
- [ ] execution in a separate worker or process;
- [ ] visible progress;
- [ ] persisted results;
- [ ] out-of-sample comparison;
- [ ] complexity penalties;
- [ ] overfitting warnings.

- [ ] Do not select a strategy only because it has the highest net profit.
- [ ] Explain optimization to beginners using simple examples.

---

- [ ] # 17. Performance metrics

Calculate and display:

- [ ] total return;
- [ ] annualized return where appropriate;
- [ ] net profit;
- [ ] gross profit;
- [ ] gross loss;
- [ ] number of trades;
- [ ] winning trades;
- [ ] losing trades;
- [ ] win rate;
- [ ] average winning trade;
- [ ] average losing trade;
- [ ] profit factor;
- [ ] expectancy;
- [ ] maximum drawdown;
- [ ] maximum drawdown duration;
- [ ] volatility;
- [ ] Sharpe ratio;
- [ ] Sortino ratio;
- [ ] Calmar ratio;
- [ ] market exposure;
- [ ] turnover;
- [ ] commissions;
- [ ] total slippage;
- [ ] performance relative to buy-and-hold.

Document:

- [ ] periodicity;
- [ ] assumed risk-free rate;
- [ ] missing-data treatment;
- [ ] annualization method;
- [ ] limitations of each metric.

- [ ] Do not display misleading ratios when there is insufficient data.

Every metric must provide:

- [ ] a technical definition;
- [ ] a beginner-friendly definition;
- [ ] a worked example;
- [ ] a warning about misuse;
- [ ] an explanation of whether higher or lower values are generally preferred;
- [ ] a statement explaining that no single metric proves that a strategy is good.

---

- [ ] # 18. Paper trading

Paper trading must use real-time or replayed data with simulated money.

It must model:

- [ ] initial balance;
- [ ] balances by asset;
- [ ] market orders;
- [ ] limit orders;
- [ ] partially filled orders;
- [ ] fees;
- [ ] slippage;
- [ ] latency;
- [ ] cancellations;
- [ ] rejections;
- [ ] positions;
- [ ] portfolio value;
- [ ] complete history.

Include:

- [ ] real-time mode;
- [ ] historical replay mode;
- [ ] playback speed;
- [ ] pause;
- [ ] step-by-step advance;
- [ ] account reset;
- [ ] snapshots;
- [ ] benchmark comparison.

- [ ] Do not present paper trading as sufficient evidence of real-world profitability.

Add a beginner tutorial explaining:

- [ ] what paper trading is;
- [ ] why it is useful;
- [ ] what it cannot simulate perfectly;
- [ ] why beginners should use it before real money;
- [ ] how to reset the simulated account;
- [ ] how to interpret gains and losses.

---

- [ ] # 19. Risk manager

Create a central `RiskManager` service.

Configurable rules:

- [ ] maximum risk per trade;
- [ ] maximum position size;
- [ ] maximum percentage of the portfolio in one asset;
- [ ] maximum total exposure;
- [ ] maximum daily loss;
- [ ] maximum weekly loss;
- [ ] maximum drawdown;
- [ ] maximum trades per day;
- [ ] maximum open orders;
- [ ] cooldown after losses;
- [ ] blocking on stale data;
- [ ] blocking on disconnection;
- [ ] blocking on excessive volatility;
- [ ] blocking on excessive spread;
- [ ] blocking on time-synchronization errors;
- [ ] blocking on inconsistent balances;
- [ ] blocking duplicate orders.

Include profiles:

- [ ] Conservative;
- [ ] Moderate;
- [ ] Custom.

- [ ] Do not include a profile named “Aggressive” in the first version.

The `RiskManager` must return:

- [ ] approved;
- [ ] rejected;
- [ ] modified;
- [ ] reason;
- [ ] triggered rule;
- [ ] permitted size;
- [ ] timestamp;
- [ ] audit identifier;
- [ ] beginner-friendly explanation.

- [ ] Every risk rule must include educational documentation explaining why it exists.

---

- [ ] # 20. Emergency kill switch

Implement a visible and accessible kill switch.

When activated:

- [ ] no new orders may be created;
- [ ] automatic strategies must stop;
- [ ] pending internal tasks must be cancelled;
- [ ] the application must clearly display the state;
- [ ] the event must be logged;
- [ ] open exchange orders must not be cancelled automatically without an explicit setting and an additional confirmation.

- [ ] Add a configurable keyboard shortcut.

Provide a beginner explanation of:

- [ ] what the kill switch does;
- [ ] when it should be used;
- [ ] what it does not do;
- [ ] why open exchange orders may still require manual attention.

---

- [ ] # 21. Real trading

Real trading support must remain behind multiple protections.

In the MVP, it may be completely disabled by a feature flag.

A future activation flow must require:

- [ ] 1. enabling an advanced option;
- [ ] 2. displaying a risk warning;
- [ ] 3. requiring written confirmation;
- [ ] 4. confirming that the API key has no withdrawal permission;
- [ ] 5. checking the selected environment;
- [ ] 6. displaying the exchange and account;
- [ ] 7. configuring strict limits;
- [ ] 8. testing connectivity;
- [ ] 9. requiring a confirmation phrase;
- [ ] 10. permanently displaying “REAL TRADING” while active.

- [ ] Never use a real account in automated tests.
- [ ] Never enable real trading automatically after importing configuration.
- [ ] Never allow a strategy to modify risk limits.
- [ ] The beginner documentation must strongly recommend learning, backtesting, and paper trading before considering real funds.

---

- [ ] # 22. Main interface

Design a professional, clear, responsive interface.

## 22.1 Sidebar

Include:

- [ ] Overview;
- [ ] Markets;
- [ ] Charts;
- [ ] Strategies;
- [ ] Backtesting;
- [ ] Paper Trading;
- [ ] Portfolio;
- [ ] Orders;
- [ ] Risk;
- [ ] Reports;
- [ ] Learning Center;
- [ ] Glossary;
- [ ] Tutorials;
- [ ] Logs;
- [ ] Settings;
- [ ] Help.

## 22.2 Top toolbar

Include:

- [ ] exchange;
- [ ] environment;
- [ ] trading pair;
- [ ] interval;
- [ ] connection status;
- [ ] last-data time;
- [ ] current mode;
- [ ] kill-switch status;
- [ ] selected language.

## 22.3 Status bar

Include:

- [ ] connectivity;
- [ ] latency;
- [ ] active tasks;
- [ ] pending data;
- [ ] database status;
- [ ] risk warnings;
- [ ] educational hints.

Use:

- [ ] `QMainWindow`;
- [ ] `QDockWidget` where appropriate;
- [ ] `QAbstractTableModel`;
- [ ] proxy models for filtering and sorting;
- [ ] delegates for editing;
- [ ] `QSettings` only for non-sensitive preferences;
- [ ] clear dialogs;
- [ ] keyboard accessibility.

Avoid:

- [ ] overloaded interfaces;
- [ ] using color as the only status indicator;
- [ ] unnecessary modal dialogs;
- [ ] rebuilding entire tables for every update.

---

- [ ] # 23. Themes and appearance

Include:

- [ ] system theme;
- [ ] light theme;
- [ ] dark theme;
- [ ] interface scaling;
- [ ] saved window state;
- [ ] support for small screens;
- [ ] bundled SVG icons;
- [ ] good behavior under XFCE;
- [ ] good behavior under Fluxbox;
- [ ] good behavior under KDE;
- [ ] good behavior under GNOME;
- [ ] good behavior under LXQt.

- [ ] Do not depend on one desktop theme.
- [ ] Verify contrast and readability.
- [ ] Do not download icons at runtime.

---

- [ ] # 24. Multilingual support and Qt Linguist

The application must be multilingual from the beginning.

## 24.1 Language order

The language implementation order must be:

- [ ] 1. English as the primary and default language;
- [ ] 2. Spanish as the second supported language;
- [ ] 3. additional languages may be added later.

- [ ] The application must start in English on first launch unless the user has previously selected another language.
- [ ] The user must be able to change the language from the interface.
- [ ] The application should support either:
  - [ ] immediate language switching at runtime; or
  - [ ] language switching after restart if runtime switching creates excessive complexity.

- [ ] The chosen behavior must be documented.

## 24.2 Qt translation system

Use:

- [ ] `QTranslator`;
- [ ] `.ts` translation source files;
- [ ] `.qm` compiled translation files;
- [ ] Qt Linguist;
- [ ] `pylupdate6`;
- [ ] `lrelease`;
- [ ] `self.tr()` or the correct PyQt6 translation mechanism.

Suggested translation files:

- [ ] `src/crypto_trading_lab/i18n/translations/crypto_trading_lab_en.ts`
- [ ] `src/crypto_trading_lab/i18n/translations/crypto_trading_lab_es.ts`

- [ ] English is the source and default application language.
- [ ] Spanish must be maintained as a complete translation.
- [ ] Do not use Spanish source strings and translate them into English.
- [ ] Do not hard-code visible strings outside the translation system.
- [ ] Do not concatenate sentence fragments that are difficult to translate.

Translate:

- [ ] menus;
- [ ] buttons;
- [ ] labels;
- [ ] dialogs;
- [ ] warnings;
- [ ] errors;
- [ ] metric names;
- [ ] strategy descriptions;
- [ ] report text;
- [ ] units;
- [ ] connection states;
- [ ] risk messages;
- [ ] educational lessons;
- [ ] glossary terms;
- [ ] tutorials;
- [ ] onboarding screens;
- [ ] help text;
- [ ] accessibility labels.

Document commands such as:

- [ ] `pylupdate6`
- [ ] `linguist`
- [ ] `lrelease`

- [ ] Do not use absolute paths.

## 24.3 Translation workflow

- [ ] Create `docs/en/developers/translation-workflow.md` covering:
  - [ ] how source strings are marked;
  - [ ] how `.ts` files are updated;
  - [ ] how Qt Linguist is used;
  - [ ] how translations are reviewed;
  - [ ] how `.qm` files are generated;
  - [ ] how missing translations are detected;
  - [ ] how plural forms are handled;
  - [ ] how translator comments are added;
  - [ ] how screenshots are used for translation context.

- [ ] Create the Spanish equivalent:
  - [ ] `docs/es/developers/flujo-de-traduccion.md`

- [ ] Add automated checks for untranslated critical strings.

---

- [ ] # 25. Credential security

Create an abstract `CredentialStore`.

Initial implementations:

- [ ] system keyring;
- [ ] in-memory storage for tests;
- [ ] mock implementation for unit tests.

The application must:

- [ ] hide keys on screen;
- [ ] allow secure pasting;
- [ ] never log pasted secrets;
- [ ] never copy secrets automatically to the clipboard;
- [ ] clear sensitive fields;
- [ ] never log authentication headers;
- [ ] redact secrets from exceptions;
- [ ] block withdrawal permissions;
- [ ] warn about excessive permissions;
- [ ] allow credential deletion;
- [ ] display the last-use date without showing the secret.

Add a logging filter that redacts:

- [ ] API keys;
- [ ] tokens;
- [ ] signatures;
- [ ] JWTs;
- [ ] secrets;
- [ ] sensitive parameters;
- [ ] authorization headers.

---

- [ ] # 26. Logging and auditing

Use Python’s standard `logging` module.

Separate logs for:

- [ ] application;
- [ ] networking;
- [ ] trading;
- [ ] auditing;
- [ ] errors.

Features:

- [ ] rotation;
- [ ] configurable levels;
- [ ] human-readable format;
- [ ] optional JSON format;
- [ ] correlation IDs;
- [ ] secret redaction;
- [ ] support export;
- [ ] size limits;
- [ ] retention policy.

The audit log must record:

- [ ] mode changes;
- [ ] risk-setting changes;
- [ ] strategy creation;
- [ ] backtest start and completion;
- [ ] kill-switch activation;
- [ ] real-trading attempts;
- [ ] order creation and cancellation;
- [ ] credential changes;
- [ ] critical errors.

- [ ] Do not log secret values.

---

- [ ] # 27. Reports

Generate backtesting and paper-trading reports in:

- [ ] HTML;
- [ ] CSV;
- [ ] JSON;
- [ ] optional PDF.

Reports must include:

- [ ] strategy;
- [ ] version;
- [ ] parameters;
- [ ] dataset checksum or identifier;
- [ ] time range;
- [ ] exchange;
- [ ] trading pair;
- [ ] interval;
- [ ] initial capital;
- [ ] fees;
- [ ] slippage;
- [ ] execution model;
- [ ] metrics;
- [ ] trades;
- [ ] equity curve;
- [ ] drawdown;
- [ ] benchmark;
- [ ] warnings;
- [ ] Crypto Trading Lab version;
- [ ] generation date.

- [ ] Reports must not claim future profitability.
- [ ] Include an optional beginner summary that explains the results in plain language.

---

- [ ] # 28. Data import

Allow candle import from CSV.

Provide a wizard for mapping:

- [ ] timestamp;
- [ ] open;
- [ ] high;
- [ ] low;
- [ ] close;
- [ ] volume;
- [ ] symbol;
- [ ] interval.

Validate:

- [ ] duplicate timestamps;
- [ ] unordered timestamps;
- [ ] irregular intervals;
- [ ] negative values;
- [ ] high below low;
- [ ] open outside the high-low range;
- [ ] close outside the high-low range;
- [ ] missing values;
- [ ] unknown timezone;
- [ ] unrecognized columns.

- [ ] Display a summary before importing.
- [ ] Include a beginner explanation of OHLCV columns.

---

- [ ] # 29. Background processing

Do not block the GUI.

Use a consistent approach involving:

- [ ] `QThreadPool`;
- [ ] `QRunnable`;
- [ ] worker objects moved to `QThread`;
- [ ] signals and slots;
- [ ] carefully integrated asyncio;
- [ ] separate processes for CPU-intensive work when necessary.

- [ ] Do not mix multiple concurrency models without a clear abstraction.

Backtesting and optimization must:

- [ ] report progress;
- [ ] support cancellation;
- [ ] terminate cleanly;
- [ ] save safe partial results;
- [ ] notify errors.

- [ ] Do not update widgets directly from worker threads.

---

- [ ] # 30. Performance

Design for:

- [ ] hundreds of thousands of stored candles;
- [ ] charts with limited visible windows;
- [ ] batch insertion;
- [ ] indexed queries;
- [ ] vectorized processing;
- [ ] controlled caching;
- [ ] task cancellation;
- [ ] moderate memory usage.

- [ ] First build a correct and testable implementation.
- [ ] Optimize only after measuring.

Include benchmarks for:

- [ ] CSV loading;
- [ ] indicator calculation;
- [ ] backtesting;
- [ ] SQLite insertion;
- [ ] chart updates.

---

- [ ] # 31. Tests

Write tests from the beginning.

## 31.1 Unit tests

Test:

- [ ] monetary models;
- [ ] normalization;
- [ ] indicators;
- [ ] strategy rules;
- [ ] risk rules;
- [ ] position sizing;
- [ ] commissions;
- [ ] slippage;
- [ ] metrics;
- [ ] `Decimal` precision;
- [ ] educational text availability;
- [ ] translation-key availability.

## 31.2 Integration tests

Test:

- [ ] SQLite;
- [ ] repositories;
- [ ] migrations;
- [ ] CSV imports;
- [ ] mock providers;
- [ ] simulated HTTP clients;
- [ ] simulated WebSockets;
- [ ] credential-store abstractions.

## 31.3 Contract tests

- [ ] Every exchange adapter must pass a common contract-test suite.

## 31.4 GUI tests

Test:

- [ ] table models;
- [ ] validators;
- [ ] critical dialogs;
- [ ] language switching;
- [ ] English startup;
- [ ] Spanish translation loading;
- [ ] settings;
- [ ] kill switch;
- [ ] mode activation;
- [ ] Learning Center navigation;
- [ ] glossary search;
- [ ] tutorial progress.

- [ ] Do not make real network calls in normal automated tests.

## 31.5 Financial regression tests

- [ ] Include small frozen datasets and expected results to prevent silent changes in:

- [ ] trades;
- [ ] balances;
- [ ] metrics;
- [ ] equity curves;
- [ ] drawdowns.

## 31.6 Security tests

Verify that:

- [ ] secrets do not appear in logs;
- [ ] secrets are not stored in SQLite;
- [ ] secrets do not appear in exported files;
- [ ] real trading remains disabled;
- [ ] strategies cannot bypass the risk manager.

## 31.7 Documentation tests

Verify:

- [ ] required beginner guides exist;
- [ ] internal documentation links are valid;
- [ ] code examples are syntactically correct;
- [ ] English documentation is present;
- [ ] Spanish documentation structure mirrors the English structure where translated;
- [ ] glossary terms referenced by the interface exist.

---

- [ ] # 32. Python packaging

- [ ] Use `pyproject.toml`.
- [ ] Prefer a simple Debian-compatible backend such as setuptools.

Include:

- [ ] project metadata;
- [ ] graphical entry point;
- [ ] console entry point;
- [ ] translation files;
- [ ] icons;
- [ ] license;
- [ ] example files;
- [ ] typing information;
- [ ] resources through `importlib.resources`.

Expected commands:

- [ ] `python3 -m build`
- [ ] `python3 -m pytest`
- [ ] `python3 -m crypto_trading_lab`
- [ ] `crypto-trading-lab`

- [ ] Do not use paths that depend on the current working directory.

---

- [ ] # 33. Debian package

- [ ] Create a complete and valid `debian/` directory.

Expected files:

- [ ] `debian/changelog`
- [ ] `debian/control`
- [ ] `debian/copyright`
- [ ] `debian/rules`
- [ ] `debian/source/format`
- [ ] `debian/watch`
- [ ] `debian/upstream/metadata`
- [ ] `debian/crypto-trading-lab.install`
- [ ] `debian/crypto-trading-lab.manpages`
- [ ] `debian/crypto-trading-lab.desktop`
- [ ] `debian/crypto-trading-lab.metainfo.xml`

Use:

- [ ] debhelper-compat;
- [ ] dh-python;
- [ ] pybuild;
- [ ] `dh-sequence-python3` where appropriate;
- [ ] automatic Python dependency substitution;
- [ ] tests during package build;
- [ ] `Rules-Requires-Root: no`;
- [ ] source format `3.0 (quilt)`.

The package must:

- [ ] install into standard paths;
- [ ] not install into `/opt`;
- [ ] not include a virtual environment;
- [ ] not download dependencies during the build;
- [ ] not use pip during Debian package construction;
- [ ] not include prebuilt wheels;
- [ ] not modify user files during installation;
- [ ] respect XDG directories;
- [ ] store user data in appropriate user directories;
- [ ] install icons;
- [ ] install a `.desktop` file;
- [ ] install AppStream metadata;
- [ ] include a man page;
- [ ] pass `lintian` reasonably;
- [ ] build in a clean environment using `sbuild` or `pbuilder`.

Carefully classify:

- [ ] `Build-Depends`;
- [ ] `Depends`;
- [ ] `Recommends`;
- [ ] `Suggests`.

- [ ] Do not declare a development-only package as a mandatory runtime dependency.

Include instructions for:

- [ ] `dpkg-buildpackage -us -uc -b`
- [ ] `lintian ../*.changes`

- [ ] Verify exact Debian 12 package names before writing `debian/control`.

---

- [ ] # 34. Debian dependency documentation

Create:

- [ ] `docs/en/developers/debian-dependencies.md`

Include a table containing:

- [ ] purpose;
- [ ] Python import;
- [ ] Debian package;
- [ ] Debian 12 version;
- [ ] required or optional;
- [ ] runtime or build dependency;
- [ ] alternative;
- [ ] reason for selection;
- [ ] Debian 13 availability;
- [ ] PyPI equivalent.

Evaluate at least:

- [ ] `python3-pyqt6`
- [ ] `python3-pyqt6.qtcharts`
- [ ] `python3-pyqt6.qtwebsockets`
- [ ] `python3-pyqt6.qtsvg`
- [ ] `python3-pyqt6.qtdesigner`
- [ ] `pyqt6-dev-tools`
- [ ] `python3-pyqtgraph`
- [ ] `python3-superqt`
- [ ] `python3-numpy`
- [ ] `python3-pandas`
- [ ] `python3-scipy`
- [ ] `python3-matplotlib`
- [ ] `python3-statsmodels`
- [ ] `python3-sklearn`
- [ ] `python3-numba`
- [ ] `python3-aiohttp`
- [ ] `python3-websockets`
- [ ] `python3-requests`
- [ ] `python3-requests-cache`
- [ ] `python3-ratelimiter`
- [ ] `python3-sqlalchemy`
- [ ] `python3-pydantic`
- [ ] `python3-dateutil`
- [ ] `python3-platformdirs`
- [ ] `python3-yaml`
- [ ] `python3-jsonschema`
- [ ] `python3-keyring`
- [ ] `python3-cryptography`
- [ ] `python3-apscheduler`
- [ ] `python3-pytest`
- [ ] `python3-pytest-asyncio`
- [ ] `python3-pytest-cov`
- [ ] `python3-requests-mock`
- [ ] `python3-freezegun`
- [ ] `python3-flake8`
- [ ] `python3-mypy`
- [ ] `python3-bandit`
- [ ] `python3-black`
- [ ] `python3-isort`
- [ ] `python3-build`
- [ ] `python3-setuptools`
- [ ] `python3-wheel`
- [ ] `python3-debian`
- [ ] `dh-python`
- [ ] `debhelper-compat`
- [ ] `devscripts`
- [ ] `lintian`
- [ ] `sbuild`

- [ ] Do not assume every package must be installed.

- [ ] Create a Spanish translation later at `docs/es/developers/dependencias-debian.md`

- [ ] English documentation must be completed first.

---

- [ ] # 35. AppImage

- [ ] Prepare a separate AppImage strategy.
- [ ] Do not add AppImage tools to the official Debian package `Build-Depends`.

Create:

- [ ] `packaging/appimage/README.md`
- [ ] `packaging/appimage/AppRun`
- [ ] `packaging/appimage/crypto-trading-lab.desktop`
- [ ] `packaging/appimage/crypto-trading-lab.appdata.xml`
- [ ] `packaging/appimage/build-appimage.sh`

The build script must:

- [ ] use `set -euo pipefail`;
- [ ] detect errors;
- [ ] not require root;
- [ ] use a temporary directory;
- [ ] clean resources;
- [ ] document dependencies;
- [ ] generate checksums;
- [ ] avoid including credentials;
- [ ] verify the artifact.

- [ ] Do not download binaries without verifying their origin and checksum.

---

- [ ] # 36. Documentation

- [ ] Documentation is a core feature of the project, not an optional final task.
- [ ] Create and maintain documentation continuously as the application evolves.
- [ ] English documentation must be written first.
- [ ] Spanish translations must follow after the English documentation is stable.

## 36.1 Main project documentation

Create:

- [ ] `README.md`
- [ ] `INSTALL.md`
- [ ] `USER_GUIDE.md`
- [ ] `DEVELOPER_GUIDE.md`
- [ ] `ARCHITECTURE.md`
- [ ] `SECURITY.md`
- [ ] `CONTRIBUTING.md`
- [ ] `CHANGELOG.md`
- [ ] `ROADMAP.md`

Also create:

- [ ] `docs/en/developers/debian-packaging.md`
- [ ] `docs/en/developers/debian-dependencies.md`
- [ ] `docs/en/developers/exchange-adapters.md`
- [ ] `docs/en/developers/backtesting-methodology.md`
- [ ] `docs/en/developers/risk-management.md`
- [ ] `docs/en/developers/data-formats.md`
- [ ] `docs/en/developers/i18n.md`
- [ ] `docs/en/developers/threat-model.md`

## 36.2 “For Dummies” beginner documentation

- [ ] Create a complete beginner-friendly documentation series in English.

The writing style must be similar to a good “For Dummies” guide:

- [ ] welcoming;
- [ ] patient;
- [ ] non-judgmental;
- [ ] clear;
- [ ] practical;
- [ ] step-by-step;
- [ ] free from unnecessary jargon;
- [ ] full of simple examples;
- [ ] full of warnings before risky actions;
- [ ] suitable for readers who know nothing about cryptocurrency;
- [ ] suitable for readers who know nothing about trading;
- [ ] suitable for readers who know nothing about technical analysis;
- [ ] suitable for readers who have never used an exchange;
- [ ] suitable for readers who have never used a backtesting program.

- [ ] Do not assume prior knowledge.

Whenever a technical word is introduced:

- [ ] 1. define it immediately;
- [ ] 2. provide a simple example;
- [ ] 3. explain why it matters;
- [ ] 4. link it to the glossary;
- [ ] 5. mention common misunderstandings.

Create this documentation structure:

- [ ] `docs/en/beginners/00-start-here.md`
- [ ] `docs/en/beginners/01-what-is-money.md`
- [ ] `docs/en/beginners/02-what-is-digital-money.md`
- [ ] `docs/en/beginners/03-what-is-cryptocurrency.md`
- [ ] `docs/en/beginners/04-what-is-bitcoin.md`
- [ ] `docs/en/beginners/05-what-is-a-blockchain.md`
- [ ] `docs/en/beginners/06-wallets-explained.md`
- [ ] `docs/en/beginners/07-private-keys-and-seed-phrases.md`
- [ ] `docs/en/beginners/08-what-is-an-exchange.md`
- [ ] `docs/en/beginners/09-centralized-and-decentralized-exchanges.md`
- [ ] `docs/en/beginners/10-spot-markets.md`
- [ ] `docs/en/beginners/11-trading-pairs.md`
- [ ] `docs/en/beginners/12-bid-ask-and-spread.md`
- [ ] `docs/en/beginners/13-order-books.md`
- [ ] `docs/en/beginners/14-market-orders.md`
- [ ] `docs/en/beginners/15-limit-orders.md`
- [ ] `docs/en/beginners/16-fees.md`
- [ ] `docs/en/beginners/17-slippage.md`
- [ ] `docs/en/beginners/18-liquidity.md`
- [ ] `docs/en/beginners/19-volatility.md`
- [ ] `docs/en/beginners/20-candlestick-charts.md`
- [ ] `docs/en/beginners/21-ohlcv-data.md`
- [ ] `docs/en/beginners/22-timeframes.md`
- [ ] `docs/en/beginners/23-support-and-resistance.md`
- [ ] `docs/en/beginners/24-trends.md`
- [ ] `docs/en/beginners/25-technical-indicators.md`
- [ ] `docs/en/beginners/26-moving-averages.md`
- [ ] `docs/en/beginners/27-rsi.md`
- [ ] `docs/en/beginners/28-macd.md`
- [ ] `docs/en/beginners/29-bollinger-bands.md`
- [ ] `docs/en/beginners/30-atr-and-volatility.md`
- [ ] `docs/en/beginners/31-what-is-a-trading-strategy.md`
- [ ] `docs/en/beginners/32-risk-management.md`
- [ ] `docs/en/beginners/33-position-sizing.md`
- [ ] `docs/en/beginners/34-stop-loss.md`
- [ ] `docs/en/beginners/35-take-profit.md`
- [ ] `docs/en/beginners/36-drawdown.md`
- [ ] `docs/en/beginners/37-paper-trading.md`
- [ ] `docs/en/beginners/38-backtesting.md`
- [ ] `docs/en/beginners/39-look-ahead-bias.md`
- [ ] `docs/en/beginners/40-overfitting.md`
- [ ] `docs/en/beginners/41-training-validation-and-testing.md`
- [ ] `docs/en/beginners/42-why-backtests-can-lie.md`
- [ ] `docs/en/beginners/43-why-paper-trading-is-different.md`
- [ ] `docs/en/beginners/44-api-keys.md`
- [ ] `docs/en/beginners/45-api-key-security.md`
- [ ] `docs/en/beginners/46-common-scams.md`
- [ ] `docs/en/beginners/47-emotional-trading.md`
- [ ] `docs/en/beginners/48-common-beginner-mistakes.md`
- [ ] `docs/en/beginners/49-when-not-to-trade.md`
- [ ] `docs/en/beginners/50-learning-roadmap.md`
- [ ] `docs/en/beginners/glossary.md`

## 36.3 Program usage guide

- [ ] Create a complete beginner user guide:

- [ ] `docs/en/user-guide/00-welcome.md`
- [ ] `docs/en/user-guide/01-installing-on-debian.md`
- [ ] `docs/en/user-guide/02-first-launch.md`
- [ ] `docs/en/user-guide/03-interface-tour.md`
- [ ] `docs/en/user-guide/04-changing-the-language.md`
- [ ] `docs/en/user-guide/05-using-the-learning-center.md`
- [ ] `docs/en/user-guide/06-importing-csv-data.md`
- [ ] `docs/en/user-guide/07-opening-a-market-chart.md`
- [ ] `docs/en/user-guide/08-reading-a-candlestick-chart.md`
- [ ] `docs/en/user-guide/09-adding-an-indicator.md`
- [ ] `docs/en/user-guide/10-creating-a-simple-strategy.md`
- [ ] `docs/en/user-guide/11-running-your-first-backtest.md`
- [ ] `docs/en/user-guide/12-understanding-backtest-results.md`
- [ ] `docs/en/user-guide/13-starting-paper-trading.md`
- [ ] `docs/en/user-guide/14-placing-a-simulated-order.md`
- [ ] `docs/en/user-guide/15-reading-your-portfolio.md`
- [ ] `docs/en/user-guide/16-using-risk-profiles.md`
- [ ] `docs/en/user-guide/17-using-the-kill-switch.md`
- [ ] `docs/en/user-guide/18-exporting-a-report.md`
- [ ] `docs/en/user-guide/19-backing-up-your-data.md`
- [ ] `docs/en/user-guide/20-troubleshooting.md`
- [ ] `docs/en/user-guide/21-safe-next-steps.md`

Each guide must contain:

- [ ] objective;
- [ ] prerequisites;
- [ ] numbered steps;
- [ ] expected result;
- [ ] screenshots or screenshot placeholders;
- [ ] common mistakes;
- [ ] troubleshooting;
- [ ] safety notes;
- [ ] glossary links;
- [ ] a short knowledge check.

## 36.4 Spanish documentation

- [ ] After the English documentation is created and reviewed, create Spanish translations under `docs/es/`.
- [ ] The Spanish structure should mirror the English structure where practical.
- [ ] Do not automatically translate technical content without review.
- [ ] Use clear, neutral Spanish suitable for Latin American users.
- [ ] Maintain terminology consistently.

## 36.5 Documentation rules

Documentation must:

- [ ] evolve with each feature;
- [ ] be updated in the same change as the feature;
- [ ] never describe nonexistent features as completed;
- [ ] clearly label planned or experimental features;
- [ ] clearly distinguish paper trading from real trading;
- [ ] clearly distinguish education from financial advice;
- [ ] include version information where useful;
- [ ] include links between related topics;
- [ ] avoid unexplained abbreviations.

The README must clearly explain:

- [ ] that the application does not guarantee profits;
- [ ] that simulation is the default mode;
- [ ] that real trading is disabled initially;
- [ ] how to install Debian dependencies;
- [ ] how to run the application;
- [ ] how to run tests;
- [ ] how to build the `.deb`;
- [ ] how to contribute;
- [ ] where beginners should start learning.

---

- [ ] # 37. Built-in Learning Center

- [ ] Create a Learning Center inside the application.

It must include:

- [ ] beginner lessons;
- [ ] glossary;
- [ ] tutorials;
- [ ] examples;
- [ ] simple quizzes;
- [ ] progress tracking;
- [ ] bookmarks;
- [ ] links to relevant application screens.

The Learning Center should allow a user to:

- [ ] read a lesson;
- [ ] open the related chart or tool;
- [ ] try an example using simulated data;
- [ ] answer a short quiz;
- [ ] mark the lesson as completed;
- [ ] continue from the last lesson.

Initial learning path:

- [ ] 1. What is cryptocurrency?
- [ ] 2. What is a market?
- [ ] 3. What is a trading pair?
- [ ] 4. What is a candlestick?
- [ ] 5. What is volume?
- [ ] 6. What is a market order?
- [ ] 7. What is a limit order?
- [ ] 8. What are fees?
- [ ] 9. What is risk?
- [ ] 10. What is paper trading?
- [ ] 11. What is backtesting?
- [ ] 12. Build your first simple strategy.
- [ ] 13. Run your first backtest.
- [ ] 14. Understand a loss.
- [ ] 15. Understand drawdown.
- [ ] 16. Learn why profits are never guaranteed.

- [ ] The Learning Center must work offline.
- [ ] Do not require an internet connection for core educational content.

---

- [ ] # 38. Glossary

- [ ] Create an English glossary first, followed by Spanish.

The glossary must include terms such as:

- [ ] asset;
- [ ] cryptocurrency;
- [ ] Bitcoin;
- [ ] altcoin;
- [ ] blockchain;
- [ ] wallet;
- [ ] private key;
- [ ] seed phrase;
- [ ] exchange;
- [ ] trading pair;
- [ ] base asset;
- [ ] quote asset;
- [ ] bid;
- [ ] ask;
- [ ] spread;
- [ ] liquidity;
- [ ] volatility;
- [ ] order book;
- [ ] market order;
- [ ] limit order;
- [ ] stop-loss;
- [ ] take-profit;
- [ ] commission;
- [ ] fee;
- [ ] slippage;
- [ ] candle;
- [ ] OHLCV;
- [ ] timeframe;
- [ ] indicator;
- [ ] strategy;
- [ ] signal;
- [ ] position;
- [ ] portfolio;
- [ ] drawdown;
- [ ] backtest;
- [ ] paper trading;
- [ ] overfitting;
- [ ] look-ahead bias;
- [ ] API;
- [ ] API key;
- [ ] WebSocket;
- [ ] REST;
- [ ] rate limit.

Every glossary entry must include:

- [ ] a short definition;
- [ ] a plain-language explanation;
- [ ] an example;
- [ ] related terms;
- [ ] a warning when appropriate.

---

- [ ] # 39. Threat model and security documentation

- [ ] Create a threat model covering:

- [ ] API key theft;
- [ ] secrets appearing in logs;
- [ ] compromised dependencies;
- [ ] malicious strategy files;
- [ ] malformed CSV files;
- [ ] manipulated API responses;
- [ ] stale market data;
- [ ] incorrect local clock;
- [ ] replayed messages;
- [ ] duplicate orders;
- [ ] uncontrolled storage growth;
- [ ] GUI freezes;
- [ ] incomplete database updates;
- [ ] corrupted configuration;
- [ ] excessive API permissions;
- [ ] accidental real-trading activation;
- [ ] misleading educational content;
- [ ] users confusing simulation with real profitability.

- [ ] Document mitigations for each threat.

---

- [ ] # 40. Reproducibility

Every backtest must store:

- [ ] application version;
- [ ] strategy version;
- [ ] parameters;
- [ ] dataset checksum;
- [ ] commission configuration;
- [ ] slippage model;
- [ ] random seed;
- [ ] time range;
- [ ] schema version;
- [ ] environment information.

- [ ] Repeating a backtest with identical data and configuration must produce identical results.

---

- [ ] # 41. Accessibility

Include:

- [ ] full keyboard navigation;
- [ ] accessible labels;
- [ ] logical tab order;
- [ ] tooltips;
- [ ] messages that do not depend only on color;
- [ ] interface scaling;
- [ ] reasonable screen-reader support;
- [ ] configurable shortcuts;
- [ ] reduced-animation support;
- [ ] readable beginner documentation;
- [ ] clear heading structures;
- [ ] descriptive link text.

---

- [ ] # 42. Complementary CLI

- [ ] Add a basic CLI without duplicating business logic:

- [ ] `crypto-trading-lab --version`
- [ ] `crypto-trading-lab doctor`
- [ ] `crypto-trading-lab database check`
- [ ] `crypto-trading-lab import-csv file.csv`
- [ ] `crypto-trading-lab backtest strategy.yaml`
- [ ] `crypto-trading-lab list-strategies`
- [ ] `crypto-trading-lab list-lessons`
- [ ] `crypto-trading-lab glossary search "slippage"`

- [ ] The CLI must reuse the same use cases as the GUI.

The `doctor` command must check:

- [ ] Python version;
- [ ] required modules;
- [ ] database;
- [ ] permissions;
- [ ] keyring;
- [ ] public connectivity;
- [ ] system clock;
- [ ] Qt resources;
- [ ] translations;
- [ ] XDG paths;
- [ ] English documentation;
- [ ] Spanish translation availability.

- [ ] It must never display secrets.

---

- [ ] # 43. Development phases

- [ ] Do not try to implement the entire application in one change.

## Phase 0: Research

Before programming:

- [ ] 1. inspect the system;
- [ ] 2. confirm software versions;
- [ ] 3. verify Debian packages;
- [ ] 4. review official documentation;
- [ ] 5. propose the architecture;
- [ ] 6. create a dependency matrix;
- [ ] 7. identify risks;
- [ ] 8. write Architecture Decision Records;
- [ ] 9. define the documentation architecture;
- [ ] 10. define the translation workflow;
- [ ] 11. define the beginner-learning roadmap.

- [ ] Deliver a research report first.

## Phase 1: Project foundation

Create:

- [ ] `pyproject.toml`;
- [ ] project structure;
- [ ] minimal PyQt6 application;
- [ ] logging;
- [ ] configuration;
- [ ] English default language;
- [ ] Spanish translation framework;
- [ ] tests;
- [ ] SQLite;
- [ ] initial Debian package;
- [ ] initial English beginner documentation;
- [ ] initial Learning Center shell.

## Phase 2: Data and charts

Implement:

- [ ] MockExchange;
- [ ] CSV import;
- [ ] candles;
- [ ] storage;
- [ ] charts;
- [ ] basic indicators;
- [ ] beginner chart tutorials.

## Phase 3: Backtesting

Implement:

- [ ] deterministic engine;
- [ ] initial strategies;
- [ ] commissions;
- [ ] slippage;
- [ ] metrics;
- [ ] reports;
- [ ] beginner backtesting guide.

## Phase 4: Paper trading

Implement:

- [ ] simulated account;
- [ ] orders;
- [ ] fills;
- [ ] portfolio;
- [ ] replay;
- [ ] risk management;
- [ ] beginner paper-trading guide.

## Phase 5: Real-time public data

Implement:

- [ ] public Binance adapter;
- [ ] WebSocket;
- [ ] reconnection;
- [ ] rate limiting;
- [ ] stale-data detection;
- [ ] beginner guide to live market data.

## Phase 6: Testnet

Implement:

- [ ] secure credentials;
- [ ] Binance Spot Testnet;
- [ ] test orders;
- [ ] reconciliation;
- [ ] auditing;
- [ ] beginner API-key security guide.

## Phase 7: Maturity

Improve:

- [ ] accessibility;
- [ ] performance;
- [ ] complete English documentation;
- [ ] Spanish documentation;
- [ ] AppImage;
- [ ] package testing;
- [ ] complete translations;
- [ ] Learning Center quizzes;
- [ ] screenshots;
- [ ] tutorials.

- [ ] Do not proceed to a new phase if the previous phase does not compile or its tests fail.

---

- [ ] # 44. Working method

Before modifying files:

- [ ] 1. inspect the repository;
- [ ] 2. report what was found;
- [ ] 3. list the files that will be created or changed;
- [ ] 4. briefly explain the objective;
- [ ] 5. make small changes;
- [ ] 6. run tests;
- [ ] 7. show the results;
- [ ] 8. fix failures;
- [ ] 9. update documentation;
- [ ] 10. update translations where visible strings changed.

- [ ] Do not replace entire files unnecessarily.
- [ ] Do not hide errors.
- [ ] Do not claim that a test passed unless it was actually executed.

When a required tool is unavailable:

- [ ] state that clearly;
- [ ] provide the command the developer must run;
- [ ] do not pretend the action succeeded.

Every completed feature must include:

- [ ] code;
- [ ] tests;
- [ ] English documentation;
- [ ] translation-ready strings;
- [ ] Spanish translation where feasible;
- [ ] beginner-oriented explanation when the feature affects end users.

---

- [ ] # 45. First concrete task

- [ ] Begin only with Phase 0 and the minimum foundation of Phase 1.

Perform these tasks:

- [ ] 1. inspect the development environment;
- [ ] 2. verify dependencies available in Debian;
- [ ] 3. create `docs/en/developers/debian-dependencies.md`;
- [ ] 4. create `docs/en/developers/architecture-proposal.md`;
- [ ] 5. create `docs/en/developers/threat-model.md`;
- [ ] 6. create ADR-0001 for the architecture;
- [ ] 7. create ADR-0002 for charting;
- [ ] 8. create ADR-0003 for Qt and asyncio concurrency;
- [ ] 9. create ADR-0004 for credential storage;
- [ ] 10. create ADR-0005 for the packaging backend;
- [ ] 11. create ADR-0006 for internationalization;
- [ ] 12. create ADR-0007 for beginner documentation;
- [ ] 13. create the initial project structure;
- [ ] 14. create a minimal PyQt6 window;
- [ ] 15. make English the default language;
- [ ] 16. create the Spanish translation infrastructure;
- [ ] 17. configure Qt Linguist files;
- [ ] 18. create XDG configuration handling;
- [ ] 19. create logging with secret redaction;
- [ ] 20. create a minimal SQLite database;
- [ ] 21. create initial unit tests;
- [ ] 22. create `pyproject.toml`;
- [ ] 23. create an initial Debian package;
- [ ] 24. create the first English beginner guide;
- [ ] 25. create the initial glossary;
- [ ] 26. create the Learning Center placeholder;
- [ ] 27. execute available tests.

The initial application must open a window containing:

- [ ] the name “Crypto Trading Lab”;
- [ ] a File menu;
- [ ] a View menu;
- [ ] a Tools menu;
- [ ] a Help menu;
- [ ] a language selector;
- [ ] English selected by default;
- [ ] Spanish available as the second language;
- [ ] a visible “Mode: Paper Trading” indicator;
- [ ] a visible “Real trading: Disabled” indicator;
- [ ] a “Disconnected” status;
- [ ] a welcome panel;
- [ ] an educational warning;
- [ ] a button to load a CSV file;
- [ ] a button to open the Backtesting Lab, initially disabled;
- [ ] a button to open the Learning Center;
- [ ] a link to “Start Here: Cryptocurrency for Complete Beginners.”

- [ ] The first English beginner guide must be `docs/en/beginners/00-start-here.md`

It must explain:

- [ ] what Crypto Trading Lab is;
- [ ] what it is not;
- [ ] that profits are not guaranteed;
- [ ] that paper trading is the default;
- [ ] where a complete beginner should begin;
- [ ] how to open the Learning Center;
- [ ] why real money should not be used while learning.

- [ ] The first glossary file must be `docs/en/beginners/glossary.md`

It must initially define at least:

- [ ] cryptocurrency;
- [ ] Bitcoin;
- [ ] exchange;
- [ ] trading pair;
- [ ] candle;
- [ ] volume;
- [ ] order;
- [ ] fee;
- [ ] slippage;
- [ ] volatility;
- [ ] strategy;
- [ ] backtesting;
- [ ] paper trading;
- [ ] risk;
- [ ] drawdown.

---

- [ ] # 46. Expected result of the first iteration

At the end, provide:

- [ ] 1. architecture summary;
- [ ] 2. project file tree;
- [ ] 3. dependencies used;
- [ ] 4. dependencies rejected and the reasons;
- [ ] 5. commands executed;
- [ ] 6. test results;
- [ ] 7. problems found;
- [ ] 8. files created;
- [ ] 9. documentation created;
- [ ] 10. translation files created;
- [ ] 11. next steps;
- [ ] 12. exact Debian 12 execution instructions.

- [ ] Do not implement real-money operations yet.
- [ ] Do not include example keys that look real.
- [ ] Do not use real funds.
- [ ] Do not claim that Crypto Trading Lab can guarantee profits.
- [ ] Do not leave beginner documentation until the end of the project.
- [ ] Documentation, translation, education, tests, and code must evolve together.
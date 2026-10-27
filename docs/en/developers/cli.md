# The command-line interface (chapter 22)

The desktop application and the CLI are two front ends over the same
use cases. Every command below that does work calls a function in
`src/crypto_trading_lab/application.py`, and the GUI calls the same
functions, so the two cannot drift apart. The CLI never prints a secret
and never claims success it did not achieve: a command that cannot do
its job prints the reason and returns a non-zero exit status.

## Running it

From a source checkout:

```bash
PYTHONPATH=src python3 -m crypto_trading_lab --help
```

After an install (pip or the Debian package):

```bash
crypto-trading-lab --help
```

With no arguments it starts the graphical application; with any
argument it runs the CLI.

## Commands

| Command | What it really does |
|---|---|
| `crypto-trading-lab --version` | Prints the package version. |
| `crypto-trading-lab doctor` | Runs every chapter 22 diagnostic (see below). |
| `crypto-trading-lab database check` | Opens the SQLite file, runs `PRAGMA integrity_check`, prints the schema version and the row count of every table. A missing database is reported as missing — nothing is created. |
| `crypto-trading-lab import-csv file.csv` | Validates the file with the chapter 28 parser and stores the candles. Invalid rows are rejected **before** the database is created. |
| `crypto-trading-lab backtest strategy.yaml` | Loads stored candles and runs the chapter 37 engine plus the chapter 40 metric catalogue. |
| `crypto-trading-lab list-strategies` | Lists the chapter 36 registry (built-ins and imported metadata). |
| `crypto-trading-lab list-lessons` | Lists the 48-lesson curriculum; `--level` 1, 2 or 3 filters it. |
| `crypto-trading-lab glossary search "slippage"` | Searches the English beginner glossary; entry-name matches are listed first, definition matches after. Exit status 1 when nothing matches. |

`import-csv` accepts `--symbol` (default `BTC/USDT`) and `--interval`
(default `1m`). Every data-reading command accepts `--data-dir`, which
points the CLI at another XDG data directory — useful for scripts and
for tests that must not touch your real data.

The grouped spellings `list strategies` and `list lessons` still work;
chapter 22 names the hyphenated forms.

## Writing a strategy configuration

`backtest` takes a small key/value file. JSON works everywhere. YAML
needs PyYAML: the Debian package depends on `python3-yaml`, pip users get
it from `requirements-all.txt` or `pip install -e ".[yaml]"`, and a
missing reader is reported with the install command instead of a
traceback.

```yaml
strategy: ma_crossover     # any id from list-strategies
fast: 10                   # strategy parameters, validated against
slow: 30                   #   the registry's parameter schema
initial_capital: 10000
position_fraction: 1       # 0 < fraction <= 1
maker_fee: 0.001
taker_fee: 0.001
slippage: 0.0005
spread: 0.0002
benchmark: buy_and_hold    # buy_and_hold | null_strategy | none
# symbol: BTC/USDT         # optional: which stored market to use
# interval: 1m
```

Unknown keys are rejected with the list of allowed ones, so a typo is
never silently ignored. When `symbol`/`interval` are omitted the CLI
uses the most recent matching dataset, or the stored market with the
most candles.

The output is the same evidence the Lab shows: net profit, drawdown,
trade statistics, risk ratios, cost attribution, the benchmark
comparison, every statistical warning, and the disclaimer. A backtest
that looks profitable and a backtest that says "no edge here" are both
legitimate results.

## doctor

`doctor` checks, in order: Python version, required modules, the
database, filesystem permissions, keyring availability, public
connectivity, system-clock drift, Qt resources, translations, XDG
paths, English documentation and Spanish translation availability.

Two checks need the outside world (connectivity and clock drift). They
are **off by default** so the command is deterministic and the test
suite stays offline; `doctor --network` runs them. The report uses
`PASS`, `WARN`, `SKIP` and `FAIL`, and the exit status is 1 only when
something failed — a warning is information, not a build breaker.

`doctor` never reads a credential store, so it cannot print a secret.
A test enforces that by making `KeyringCredentialStore.load` and
`.list` raise if they are ever called during a doctor run.

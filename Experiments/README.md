# Experiments — verification kit

This folder exists for one reason: the whole test suite is verified on
**Debian 13** (`702 passed, 2 skipped`) and on **Windows 10** (see the result
below). Everything else — macOS, a different Linux, another Python — is
expected to work, but nobody has measured it yet. This kit turns that
"should work" into a real result you can send back.

It is safe: the application is research, backtesting and paper trading. It
**never** trades real money, and it refuses to by default.

## Result: Windows 10, 2026-10-01

Measured, not assumed, on Windows 10 (10.0.19045, AMD64) with Python
**3.14.7** and every package from PyPI:

- the virtualenv and `pip install` worked;
- the PowerShell activation error **did** appear, and
  `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` fixed it;
- **the application window opened and stayed open with no crash**;
- CSV import, backtest and paper trading produced numbers *identical* to
  Debian (return `44.3041 %`, 4 trades, equity `14430.412140744344810846567`,
  paper `12055.252086818242739372290`);
- `ccxt` 4.5.85 covered 104 exchanges and reached the network
  (`BTC/USDT last=84266.19`);
- the suite reported `698 passed, 2 skipped`.

The raw PowerShell transcript is kept as
[`20261001-resultado-de-la-instalacion-en-Windows-10.txt`](20261001-resultado-de-la-instalacion-en-Windows-10.txt).

**And it found a real bug.** The same run appeared to *fail*: the suite said
`698 passed` and then the process died with a segmentation fault, so the
exit code was non-zero and `make test`/CI would have reported failure. The
cause was chapter 68's safety module importing Qt and re-initialising a
`QObject` inside `deactivate()`. Both are fixed, and a regression test now
asserts that the module imports without Qt. A first run on a new platform
earns its keep.

## What is in here

| File | What it is |
|---|---|
| `README.md` | This manual. |
| `CHECKLIST.md` | The list of checks with `[ ]` boxes for you to tick. Fill it in and send it back. |
| `verify.py` | Runs the automated checks and writes `verify-report.md`. |
| `requirements-all.txt` | **Every** dependency, including `ccxt`, for a machine without Debian packages. |
| `setup_windows.bat` | One-click Windows setup (uses `cmd.exe`, so the PowerShell execution policy never gets in the way). |
| `run_verify.cmd` | Activates the virtualenv and runs `verify.py`. |
| `sample-data/btc-usdt-1h-sample.csv` | 400 hourly BTC/USDT candles so the whole pipeline can be exercised **offline**. |
| `verify-report.md` | Generated when you run `verify.py`; send it back with the checklist. |

Nothing here is part of the application; you can delete the folder without
affecting it.

---

## Windows, the short path (recommended, no PowerShell policy involved)

1. Install **Python 3.11 or newer** from <https://www.python.org/downloads/>
   and tick **“Add python.exe to PATH”** during the installation.
2. Get the repository onto the machine (clone it, or copy the folder).
3. Double-click **`Experiments\setup_windows.bat`**.
   It creates `.venv`, installs every dependency (PyQt6, pyqtgraph,
   SQLAlchemy, platformdirs, pytest, **ccxt**, pypdf, keyring) and installs
   the project itself.
4. Double-click **`Experiments\run_verify.cmd`** to run the checks.
5. Fill in **`CHECKLIST.md`** and send it back with **`verify-report.md`**.

---

## Windows, step by step (PowerShell)

Open PowerShell in the repository folder.

```powershell
# 1. Check Python (3.11+). On Windows it is `py -3` or `python`, never `python3`.
py -3 --version

# 2. Create the virtualenv
py -3 -m venv .venv

# 3. Activate it
.\.venv\Scripts\Activate.ps1

# 4. Upgrade pip and install everything, including ccxt
python -m pip install --upgrade pip
python -m pip install -r Experiments\requirements-all.txt
python -m pip install -e .

# 5. Run the checks
python Experiments\verify.py
python Experiments\verify.py --network
python Experiments\verify.py --gui
python Experiments\verify.py --tests
```

### If step 3 is blocked: the activation error

PowerShell refuses to run the activation script by default:

```text
.\.venv\Scripts\Activate.ps1 : File ... cannot be loaded because running
scripts is disabled on this system.
```

Allow it **for this window only**, then activate:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

`-Scope Process` is the important word: the change applies to the current
PowerShell session and nothing else — no administrator rights, nothing
written to the system, and it reverts when you close the window. Do **not**
run `Set-ExecutionPolicy Unrestricted` machine-wide.

Three ways to avoid the policy entirely:

- use `cmd.exe`, where it never appears: `.venv\Scripts\activate.bat`
  (this is what `setup_windows.bat` uses);
- use Git Bash: `source .venv/Scripts/activate`;
- do not activate at all — call the interpreter directly:
  ```powershell
  .\.venv\Scripts\python.exe -m pip install -e .
  .\.venv\Scripts\python.exe Experiments\verify.py
  ```
  This last form is exactly what the project's CI does.

---

## macOS

No system packages are needed; Apple Silicon and Intel both have wheels.

```bash
# Python 3.11+:  brew install python@3.13   (or the python.org installer)
python3 --version
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r Experiments/requirements-all.txt
python -m pip install -e .

python Experiments/verify.py
python Experiments/verify.py --network
python Experiments/verify.py --gui
python Experiments/verify.py --tests
```

---

## What the checks mean

`verify.py` runs twelve checks and prints one line each:

| Check | What it proves |
|---|---|
| python version | 3.11 or newer |
| operating system | records the platform |
| runtime imports | PyQt6, pyqtgraph, SQLAlchemy, platformdirs import |
| numpy | arrives with pyqtgraph |
| package imports | the project itself imports |
| sample dataset present | the bundled CSV is there |
| CSV importer | the sample parses to 400 valid 1h candles |
| backtest engine | a backtest runs on it |
| paper trading | a paper session runs on it |
| Qt window (offscreen) | the whole UI imports and the main window constructs |
| ccxt adapter | ccxt is present and the project adapter accepts a real client |
| optional extras | which of keyring / pypdf / aiohttp / websockets are installed |

Flags:

- `--tests` runs the full suite (about a minute) and records the summary line.
- `--gui` opens the real window for eight seconds: if it stays open without a
  traceback, the graphical part works.
- `--network` asks ccxt for one public price (needs internet).

It writes **`Experiments/verify-report.md`** with the platform, the Python,
the table of results and the totals. **Send that file back.**

### Expected values on the bundled dataset

These are deterministic, so they are a good reference. If yours differ
materially, that difference is the finding.

| | Expected |
|---|---|
| CSV importer | 400 rows, symbol `BTC/USDT`, interval `1h` |
| Backtest (SMA 5×20) | total return ≈ **44.30 %**, **4 trades**, final equity ≈ **14430.41** |
| Paper trading (same strategy) | final equity ≈ **12055.25**, **4 closed trades** |
| Test suite | **702 passed, 2 skipped** |

Qt may print harmless platform-plugin noise to the console (on Linux, the
theme plugin; on Windows, usually nothing). Only a `Traceback` counts as an
error.

---

## How to report back

1. Fill in `Experiments/CHECKLIST.md` (tick the boxes you ran, paste the raw
   output of anything that failed).
2. Run `python Experiments/verify.py --tests` so `verify-report.md` is complete.
3. Send both files back — commit them, or paste their contents.

If a screen misbehaves, a screenshot helps. The raw console text helps more:
it is what can actually be fixed.

---

## Honest limitations

- This kit verifies; it cannot fix. The failures it finds are the useful part.
- Windows 10 is verified (2026-10-01, above). **macOS is not** — nobody has
  run it. A preview of what could differ: `tools/make_banner_gif.py` (which
  only regenerates the README banner, not the application) hardcodes Debian
  font paths; `debian/` is Debian packaging and is irrelevant elsewhere;
  `keyring` is optional and the application says so if it is missing;
  `reproducibility` calls `git` and simply records no revision when git is
  not installed.
- The `--tests` stage reports a failure if the process exits non-zero even
  when pytest says everything passed. That is deliberate: on Windows 10 it
  is exactly how the chapter-68 segmentation fault was found.

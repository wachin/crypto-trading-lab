"""Tests for the command-line interface (ROADMAP chapter 22).

Every subcommand must do real work and must return a non-zero status
when it cannot. The tests drive main() exactly as a user would.
"""

from __future__ import annotations

import json
import math
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from crypto_trading_lab import cli


def write_candles(path: Path, count: int = 120) -> Path:
    start = datetime(2024, 1, 1, tzinfo=timezone.utc)
    lines = ["timestamp,open,high,low,close,volume"]
    for index in range(count):
        open_ = 100 + 8 * math.sin(index / 7)
        close = 100 + 8 * math.sin((index + 1) / 7)
        stamp = (start + timedelta(minutes=index)).isoformat()
        lines.append(
            f"{stamp},{open_:.4f},{max(open_, close) + 0.5:.4f},"
            f"{min(open_, close) - 0.5:.4f},{close:.4f},10"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def run(argv: list[str]) -> int:
    return cli.main(argv)


# -- surface ---------------------------------------------------------------


def test_parser_exposes_every_chapter_22_command():
    parser = cli.build_parser()
    actions = [
        action for action in parser._actions if action.dest == "command"
    ]
    commands = set(actions[0].choices)
    for expected in (
        "doctor",
        "database",
        "import-csv",
        "backtest",
        "list-strategies",
        "list-lessons",
        "glossary",
    ):
        assert expected in commands


def test_version_exits_zero(capsys):
    with pytest.raises(SystemExit) as exit_info:
        cli.main(["--version"])
    assert exit_info.value.code == 0
    assert "Crypto Trading Lab" in capsys.readouterr().out


def test_no_arguments_prints_help(capsys):
    assert cli.main([]) == 0
    assert "usage:" in capsys.readouterr().out


# -- doctor ----------------------------------------------------------------


def test_doctor_passes_offline_and_skips_network_checks(tmp_path, capsys):
    code = run(["doctor", "--data-dir", str(tmp_path / "data")])
    output = capsys.readouterr().out
    assert code == 0
    assert "[PASS] python_version" in output
    assert "[SKIP] public_connectivity" in output
    assert "[SKIP] system_clock" in output
    assert "Doctor finished:" in output


def test_doctor_never_reads_a_credential(tmp_path, monkeypatch, capsys):
    from crypto_trading_lab.security.credentials import KeyringCredentialStore

    def forbidden(*_args, **_kwargs):
        raise AssertionError("doctor must not read credentials")

    monkeypatch.setattr(KeyringCredentialStore, "load", forbidden)
    monkeypatch.setattr(KeyringCredentialStore, "list", forbidden)
    assert run(["doctor", "--data-dir", str(tmp_path / "data")]) == 0
    assert "credential" in capsys.readouterr().out.lower()


# -- database check --------------------------------------------------------


def test_database_check_without_a_database_fails_honestly(tmp_path, capsys):
    code = run(["database", "check", "--data-dir", str(tmp_path / "data")])
    captured = capsys.readouterr()
    assert code == 1
    assert "Nothing was checked" in captured.err
    assert "passed" not in captured.out.lower()


def test_database_check_reports_real_rows(tmp_path, capsys):
    data_dir = tmp_path / "data"
    csv_path = write_candles(tmp_path / "candles.csv", count=5)
    assert run(["import-csv", str(csv_path), "--data-dir", str(data_dir)]) == 0
    capsys.readouterr()
    code = run(["database", "check", "--data-dir", str(data_dir)])
    output = capsys.readouterr().out
    assert code == 0
    assert "candles: 5 row(s)" in output
    assert "Integrity: ok" in output
    assert "Database check passed." in output


# -- import-csv ------------------------------------------------------------


def test_import_csv_imports_and_reports(tmp_path, capsys):
    data_dir = tmp_path / "data"
    csv_path = write_candles(tmp_path / "candles.csv", count=3)
    code = run(["import-csv", str(csv_path), "--data-dir", str(data_dir)])
    output = capsys.readouterr().out
    assert code == 0
    assert "Imported 3 candles of BTC/USDT (1m)." in output
    assert (data_dir / "crypto-trading-lab.db").exists()


def test_import_csv_rejects_invalid_rows(tmp_path, capsys):
    data_dir = tmp_path / "data"
    csv_path = tmp_path / "bad.csv"
    csv_path.write_text(
        "timestamp,open,high,low,close,volume\n"
        "2024-01-01T00:00:00+00:00,100,110,90,-5,10\n",
        encoding="utf-8",
    )
    code = run(["import-csv", str(csv_path), "--data-dir", str(data_dir)])
    captured = capsys.readouterr()
    assert code == 1
    assert "negative" in captured.err
    assert not (data_dir / "crypto-trading-lab.db").exists()


def test_import_csv_reports_a_missing_file(tmp_path, capsys):
    code = run(
        ["import-csv", str(tmp_path / "nope.csv"), "--data-dir", str(tmp_path / "data")]
    )
    assert code == 1
    assert "does not exist" in capsys.readouterr().err


# -- listings --------------------------------------------------------------


def test_list_strategies_prints_builtins(tmp_path, capsys):
    code = run(["list-strategies", "--data-dir", str(tmp_path / "data")])
    output = capsys.readouterr().out
    assert code == 0
    assert "ma_crossover" in output
    assert "null_strategy" in output


def test_list_strategies_alias_still_works(tmp_path, capsys):
    assert run(["list", "strategies", "--data-dir", str(tmp_path / "data")]) == 0
    assert "ma_crossover" in capsys.readouterr().out


def test_list_lessons_prints_the_curriculum(tmp_path, capsys):
    code = run(["list-lessons", "--data-dir", str(tmp_path / "data")])
    output = capsys.readouterr().out
    assert code == 0
    assert "Total: 48 lesson(s)." in output


def test_list_lessons_filters_by_level(tmp_path, capsys):
    code = run(
        ["list-lessons", "--level", "3", "--data-dir", str(tmp_path / "data")]
    )
    output = capsys.readouterr().out
    assert code == 0
    assert "[Level 3]" in output
    assert "[Level 1]" not in output


# -- glossary --------------------------------------------------------------


def test_glossary_search_prints_the_definition(capsys):
    code = run(["glossary", "search", "slippage"])
    output = capsys.readouterr().out
    assert code == 0
    assert "### slippage" in output
    assert "Definition:" in output
    assert "1 entry matched" in output or "entries matched" in output


def test_glossary_search_without_matches_returns_one(capsys):
    code = run(["glossary", "search", "zzzz-not-a-term"])
    assert code == 1
    assert "No glossary entry matched" in capsys.readouterr().err


# -- backtest --------------------------------------------------------------


def test_backtest_runs_and_prints_metrics(tmp_path, capsys):
    data_dir = tmp_path / "data"
    csv_path = write_candles(tmp_path / "candles.csv")
    assert run(["import-csv", str(csv_path), "--data-dir", str(data_dir)]) == 0
    config = tmp_path / "strategy.json"
    config.write_text(
        json.dumps({"strategy": "ma_crossover", "fast": 5, "slow": 20}),
        encoding="utf-8",
    )
    capsys.readouterr()
    code = run(["backtest", str(config), "--data-dir", str(data_dir)])
    output = capsys.readouterr().out
    assert code == 0
    assert "Strategy: SMA(5)xSMA(20) crossover" in output
    assert "Net profit:" in output
    assert "Benchmark (Buy and hold)" in output
    assert "do not predict future returns" in output


def test_backtest_with_a_broken_config_fails_with_a_reason(tmp_path, capsys):
    data_dir = tmp_path / "data"
    csv_path = write_candles(tmp_path / "candles.csv", count=10)
    assert run(["import-csv", str(csv_path), "--data-dir", str(data_dir)]) == 0
    config = tmp_path / "strategy.json"
    config.write_text(json.dumps({"strategy": "nope"}), encoding="utf-8")
    capsys.readouterr()
    code = run(["backtest", str(config), "--data-dir", str(data_dir)])
    captured = capsys.readouterr()
    assert code == 1
    assert "Backtest not run" in captured.err
    assert "unknown strategy" in captured.err


def test_backtest_without_any_data_explains_what_to_do(tmp_path, capsys):
    config = tmp_path / "strategy.json"
    config.write_text(json.dumps({"strategy": "ma_crossover"}), encoding="utf-8")
    code = run(["backtest", str(config), "--data-dir", str(tmp_path / "data")])
    captured = capsys.readouterr()
    assert code == 1
    assert "import-csv" in captured.err


# -- entry point (console script and python -m) ----------------------------


def test_main_module_dispatches_arguments_to_the_cli(capsys):
    from crypto_trading_lab.__main__ import main as entry_point

    assert entry_point(["list-lessons"]) == 0
    assert "Total: 48 lesson(s)." in capsys.readouterr().out


def _run_entry_point(source: str) -> "subprocess.CompletedProcess[str]":
    import os
    import subprocess

    src = str(Path(__file__).resolve().parents[1] / "src")
    environment = dict(os.environ, PYTHONPATH=src)
    environment.pop("QT_QPA_PLATFORM", None)
    return subprocess.run(
        [sys.executable, "-c", source],
        capture_output=True,
        text=True,
        timeout=60,
        env=environment,
    )


def test_entry_point_runs_the_cli_without_a_display():
    # The console script used to point at the GUI function, so every
    # subcommand opened a window and ignored its arguments.
    completed = _run_entry_point(
        "from crypto_trading_lab.__main__ import main; "
        "raise SystemExit(main(['list-lessons']))"
    )
    assert completed.returncode == 0
    assert "Total: 48 lesson(s)." in completed.stdout


def test_entry_point_does_not_import_qt_for_the_cli():
    completed = _run_entry_point(
        "import sys, crypto_trading_lab.__main__ as entry; "
        "print('PyQt6' in sys.modules)"
    )
    assert completed.returncode == 0
    assert completed.stdout.strip() == "False"

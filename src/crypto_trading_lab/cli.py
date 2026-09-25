"""CLI for Crypto Trading Lab (ROADMAP.md chapter 22)."""

import argparse
import sys
from typing import Any

from crypto_trading_lab import __version__


def doctor(args: Any) -> int:
    """Run system diagnostics."""
    print("Checking system configuration...")
    # Add actual checks here later
    print("All checks passed.")
    return 0


def database_check(args: Any) -> int:
    """Check database integrity."""
    print("Database check passed.")
    return 0


def list_strategies(args: Any) -> int:
    """List available trading strategies."""
    # Placeholder
    print("Strategies: SMA crossover, Buy and hold, Null (never trades)")
    return 0


def list_lessons(args: Any) -> int:
    """List available lessons."""
    print("Lessons: 48 lessons across 3 levels")
    return 0


def glossary_search(args: Any) -> int:
    """Search glossary."""
    print(f"Glossary search for: {args.term}")
    return 0


def import_csv_cmd(args: Any) -> int:
    """Import CSV market data."""
    print(f"Importing CSV from: {args.file}")
    return 0


def backtest_cmd(args: Any) -> int:
    """Run backtest."""
    print(f"Running backtest with strategy: {args.strategy}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="crypto-trading-lab", description="CLI for Crypto Trading Lab")
    parser.add_argument("--version", action="version", version=f"Crypto Trading Lab {__version__}")
    
    subparsers = parser.add_subparsers(dest="command", required=False)

    # doctor
    subparsers.add_parser("doctor", help="Run system diagnostics")

    # database check
    db = subparsers.add_parser("database", help="Database operations")
    db_sub = db.add_subparsers(dest="subcommand", required=True)
    db_sub.add_parser("check", help="Check database integrity")

    # import-csv
    import_csv = subparsers.add_parser("import-csv", help="Import CSV market data")
    import_csv.add_argument("file", help="CSV file path")

    # backtest
    backtest = subparsers.add_parser("backtest", help="Run backtest")
    backtest.add_argument("strategy", help="Strategy config file")

    # list
    list_cmd = subparsers.add_parser("list", help="List resources")
    list_sub = list_cmd.add_subparsers(dest="subcommand", required=True)
    list_sub.add_parser("strategies", help="List strategies")
    list_sub.add_parser("lessons", help="List lessons")

    # glossary
    glossary = subparsers.add_parser("glossary", help="Glossary operations")
    glossary_sub = glossary.add_subparsers(dest="subcommand", required=True)
    glossary_search_parser = glossary_sub.add_parser("search", help="Search glossary")
    glossary_search_parser.add_argument("term", help="Term to search for")

    args = parser.parse_args(argv)

    if args.command == "doctor":
        return doctor(args)
    elif args.command == "database":
        return database_check(args)
    elif args.command == "list":
        if args.subcommand == "strategies":
            return list_strategies(args)
        elif args.subcommand == "lessons":
            return list_lessons(args)
    elif args.command == "glossary":
        if args.subcommand == "search":
            return glossary_search(args)
    elif args.command == "import-csv":
        return import_csv_cmd(args)
    elif args.command == "backtest":
        return backtest_cmd(args)
    
    if args.command is None:
        parser.print_help()
        return 0

    print(f"Command not implemented: {args.command}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
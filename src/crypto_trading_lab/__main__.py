"""``python3 -m crypto_trading_lab`` entry point."""

import sys
from crypto_trading_lab.cli import main as run_cli
from crypto_trading_lab.ui.main_window.window import run as run_ui

if __name__ == "__main__":
    if len(sys.argv) > 1:
        raise SystemExit(run_cli(sys.argv[1:]))
    else:
        raise SystemExit(run_ui())

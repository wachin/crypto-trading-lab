"""Entry point shared by the console script and python -m.

No arguments opens the graphical application; any argument runs the CLI
(ROADMAP chapter 22). Both imports are lazy on purpose: before this
dispatcher existed the console script pointed straight at the GUI, so
"crypto-trading-lab doctor" opened a window and ignored every argument.
Keeping the GUI import inside the branch also means the CLI never needs a
display.
"""

from __future__ import annotations

import sys


def main(argv: list[str] | None = None) -> int:
    """Run the CLI when given arguments, the GUI otherwise."""
    arguments = list(sys.argv[1:] if argv is None else argv)
    if arguments:
        from crypto_trading_lab.cli import main as run_cli

        return run_cli(arguments)

    from crypto_trading_lab.ui.main_window.window import run as run_ui

    return run_ui()


if __name__ == "__main__":
    raise SystemExit(main())

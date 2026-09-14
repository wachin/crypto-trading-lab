"""Test bootstrap: make the src-layout package importable without install.

The spike runs tests directly from a source checkout; once the project
is pip-installed (chapter 15) this file can shrink to nothing.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
for path in (ROOT / "src", ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

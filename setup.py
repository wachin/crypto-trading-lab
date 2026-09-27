#!/usr/bin/env python3
"""Compatibility shim for tooling that still calls ``setup.py`` directly.

All project metadata lives in ``pyproject.toml`` (PEP 621). This file
deliberately contains no metadata of its own: the previous version
duplicated the name, version, dependencies and entry points, and the two
copies drifted apart (``setup.py`` required PyQt6/SQLAlchemy while
``pyproject.toml`` declared none, and it omitted pyqtgraph and
platformdirs entirely).

Keep it this way. A new dependency belongs in ``pyproject.toml`` — and,
per ``AGENTS.md`` rule 2, in a STOP report to the maintainer before it is
installed. Debian packaging reads this shim through ``debian/rules``.
"""

from setuptools import setup

setup()

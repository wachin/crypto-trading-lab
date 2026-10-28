#!/usr/bin/env python3
"""Check every reference written inside a docstring.

Nothing else catches this. ``tools/check_doc_links.py`` reads Markdown, and
the test suite never reads prose, so a docstring that says
``:class:`RuleStrategySpec``` or ``docs/en/developers/afml-techniques.md``
keeps pointing at nothing after a rename. That is the same failure mode the
link checker exists for, one layer further in.

What it checks
--------------
1. **Roles.** ``:class:``, ``:func:``, ``:meth:``, ``:mod:``, ``:attr:``
   and ``:exc:`` targets must name something the package defines, a module
   that exists, or a dotted path whose parts resolve.
2. **Paths.** A repository-relative path ending in ``.md`` must exist.

What it deliberately does not check
-----------------------------------
- Anchors inside those paths. ``check_doc_links.py`` does that for real
  Markdown links; a ``#fragment`` in a docstring is checked for existence
  of the file only.
- Attributes of standard-library or third-party objects, which would
  require importing them. Only names this package defines are inspected.
- Prose that mentions a file without backticks or a role.

It reads the AST instead of importing modules, so it needs no optional
dependency (no Qt, no websockets) and cannot execute project code.

Run it from anywhere:

    python3 tools/check_docstring_refs.py

It exits 0 when everything resolves and 1 when something does not.
"""

from __future__ import annotations

import argparse
import ast
import importlib.util
import re
import sys
from pathlib import Path

ROLE = re.compile(r":(class|func|meth|mod|attr|exc):`([^`]+)`")
MARKDOWN_PATH = re.compile(r"`{0,2}([A-Za-z0-9_./-]+\.md)(?:#[A-Za-z0-9_-]+)?`{0,2}")


def _defined_names(body):
    """Names a module or class body binds at its top level."""
    names = set()
    for node in body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names.add(node.name)
        elif isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            for target in targets:
                if isinstance(target, ast.Name):
                    names.add(target.id)
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            for alias in node.names:
                names.add(alias.asname or alias.name.split(".")[0])
    return names


def _dotted_name(path, root, package):
    """``.../pkg/mod.py`` → ``pkg.mod``."""
    rel = path.relative_to(root).with_suffix("")
    parts = list(rel.parts)
    if parts and parts[-1] == "__init__":
        parts.pop()
    return ".".join([package] + parts) if parts else package


class SymbolTable:
    """Every name the package defines, read from the AST."""

    def __init__(self, root: Path, package: str) -> None:
        self.root = root
        self.package = package
        self.by_module: dict[str, dict[str, object]] = {}
        self.everything: set[str] = set()
        self.module_names: set[str] = set()

    def scan(self) -> None:
        for path in sorted(self.root.rglob("*.py")):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            classes = {
                node.name: _defined_names(node.body)
                for node in tree.body
                if isinstance(node, ast.ClassDef)
            }
            names = _defined_names(tree.body)
            self.by_module[str(path)] = {"names": names, "classes": classes}
            self.module_names.add(_dotted_name(path, self.root, self.package))
            self.everything |= names
            for members in classes.values():
                self.everything |= members

    def _class_members(self, module_path: str, class_name: str):
        entry = self.by_module[module_path]
        return entry["classes"].get(class_name)

    def _module_names(self, dotted: str):
        for path, entry in self.by_module.items():
            if _dotted_name(Path(path), self.root, self.package) == dotted:
                return entry["names"]
        return None

    def resolves(self, role: str, target: str, module_path: str, holder: str | None) -> bool:
        name = target.split("(")[0].strip().lstrip("~")
        if not name:
            return False
        if role == "mod":
            if name in self.module_names:
                return True
            try:
                return importlib.util.find_spec(name) is not None
            except (ImportError, ValueError):
                return False
        if "." in name:
            head, _, tail = name.rpartition(".")
            names = self._module_names(head)
            if names is not None:
                return tail in names or any(
                    tail in members
                    for members in self.by_module_names(head)
                )
            members = self._class_members(module_path, head)
            if members is not None:
                return tail in members
            try:
                return importlib.util.find_spec(head) is not None
            except (ImportError, ValueError):
                return False
        if holder is not None:
            members = self._class_members(module_path, holder)
            if members is not None and name in members:
                return True
        entry = self.by_module[module_path]
        if name in entry["names"]:
            return True
        return name in self.everything

    def by_module_names(self, dotted: str):
        for path, entry in self.by_module.items():
            if _dotted_name(Path(path), self.root, self.package) == dotted:
                yield from entry["classes"].values()


def _holders(tree):
    """Map a function node to the class that contains it, if any."""
    owner = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            for item in node.body:
                owner[id(item)] = node.name
    return owner


def check(root: Path, package: str) -> tuple[list[str], int, int]:
    table = SymbolTable(root, package)
    table.scan()
    problems: list[str] = []
    roles = 0
    paths = 0
    for path in sorted(root.rglob("*.py")):
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        holders = _holders(tree)
        entries = [(None, ast.get_docstring(tree) or "")]
        for node in ast.walk(tree):
            if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                entries.append((node, ast.get_docstring(node) or ""))
        for node, text in entries:
            if not text:
                continue
            holder = None
            if isinstance(node, ast.ClassDef):
                holder = node.name
            elif node is not None:
                holder = holders.get(id(node))
            for role, target in ROLE.findall(text):
                roles += 1
                if not table.resolves(role, target, str(path), holder):
                    label = getattr(node, "name", "<module>")
                    problems.append(
                        f"{path}: {label}: :{role}:`{target}` does not resolve"
                    )
            for rel in MARKDOWN_PATH.findall(text):
                paths += 1
                if not (root.parent.parent / rel).exists() and not (root.parent / rel).exists():
                    problems.append(f"{path}: {rel} does not exist")
    if not roles and not paths:
        problems.append(
            "no references were found at all; the scanner is probably broken"
        )
    return problems, roles, paths


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--package-root",
        type=Path,
        default=None,
        help="package directory to scan (default: src/crypto_trading_lab)",
    )
    args = parser.parse_args()
    repo = Path(__file__).resolve().parent.parent
    root = args.package_root or repo / "src" / "crypto_trading_lab"
    problems, roles, paths = check(root, root.name)

    print("Docstring references")
    print("=" * 50)
    print(f"  roles checked: {roles}")
    print(f"  Markdown paths checked: {paths}")
    for line in problems:
        print(f"  {line}")
    if problems:
        print(f"{len(problems)} unresolved reference(s).")
        return 1
    print("  Every role and Markdown path resolves.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

# AGENTS.md — Crypto Trading Lab

Ground rules for any AI Agent working in this repository.
Read `AGENT-HANDOFF.md` first if you are starting a session in a
freshly migrated copy, then `GENESIS.md`, then `ROADMAP.md`.

## Non-negotiable rules

1. **ROADMAP.md is the specification.** Do not replace, simplify,
   reinterpret, or silently omit its requirements. If something is
   unclear, say so explicitly instead of guessing. Mark completed
   items with `[x]` as you finish them.
2. **Dependency STOP rule.** If development needs a new dependency:
   STOP at that task. Do NOT install anything yourself (no apt, no
   pip, no venv creation). Notify the developer with: package name,
   Debian-or-PyPI source, reason, and the exact command to run.
   PyPI-only packages require the developer to create a venv
   (`.venv`) — the Agent uses it afterwards but never creates or
   installs into one. So far no venv has been needed; every
   dependency is a system Debian package.
3. **Security posture.** No real credentials in code/tests; no
   `eval()`/`exec()`; real trading stays disabled by default and
   only activates through the chapter 68 flow; strategies never
   bypass the risk manager; secrets are redacted in every log.
4. **Vision and mission.** Survive → validate → earn. The program
   never promises profits and must tell the user the truth when no
   statistical edge exists. Capital protection outranks profit
   seeking: never encourage trading money needed to live.
5. **Honesty in reporting.** Only claim a test passed if you ran it.
   Show real command output. If a tool is missing, say so and give
   the command; never pretend success.
6. **The AFML book rule.** *Advances in Financial Machine Learning*
   (Marcos López de Prado, Wiley 2018) is cited by bibliographic
   reference only. Record every technique mapping and definition in
   `docs/en/developers/reference-projects.md` and
   `docs/en/developers/afml-techniques.md`; cite the book as
   "López de Prado (2018), Advances in Financial Machine Learning,
   ch. N"; never copy book text, code, figures, or tables into the
   repository; never commit or redistribute the book itself — printed
   text or local exhibit compilation — which stays a local reference.
7. **Language.** English is the source language for code, docs, and
   UI strings; Spanish via Qt Linguist (`pylupdate6` → `.ts` →
   `lrelease` → `.qm`). Never hard-code visible strings outside
   `self.tr()`.
8. **Working method.** Small changes; run the full test suite
   (`QT_QPA_PLATFORM=offscreen python3 -m pytest tests/ -q`) after
   every iteration; update documentation in the same change;
   beginner-oriented explanations accompany user-facing features.

## Environment facts (verify at session start)

- Debian 13, Python 3.13.5, PyQt6 + pyqtgraph + SQLAlchemy +
  platformdirs from system packages (no venv)
- Expected baseline: **229 passed, 2 skipped**
- GUI tests run offscreen (`QT_QPA_PLATFORM=offscreen`)

## Current position

Phase 3 (backtesting). Engine and strategies are done; next is
chapter 40 (performance metrics) then the Backtesting Lab UI. See
`AGENT-HANDOFF.md` §5 for the exact continuation point.

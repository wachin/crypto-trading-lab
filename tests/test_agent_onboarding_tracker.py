"""Tests for the agent-onboarding tracker (docs/en/developers/agent-onboarding-tracker.md).

The tracker is the single place to check whether the agent-onboarding
surface is complete and current. These tests verify it stays in sync
with reality: every file it lists exists, every reading list it claims
includes AGENTS.md does, and the test baseline it quotes matches the one
in AGENTS.md. If any of these drift, the test fails and the tracker must
be updated in the same change.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TRACKER = ROOT / "docs" / "en" / "developers" / "agent-onboarding-tracker.md"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


# -- The tracker exists --------------------------------------------------------

def test_tracker_file_exists():
    assert TRACKER.is_file(), "agent-onboarding-tracker.md must exist"


def test_tracker_has_last_verified_date():
    text = _read(TRACKER)
    assert re.search(r"Last verified:\s*\d{4}-\d{2}-\d{2}", text), (
        "tracker must carry a 'Last verified: YYYY-MM-DD' date"
    )


# -- Core files listed in the tracker exist ------------------------------------

CORE_FILES = [
    "AGENTS.md",
    "CLAUDE.md",
    "AGENT-HANDOFF.md",
    "ROADMAP.md",
    "CONTRIBUTING.md",
]


def test_core_agent_files_exist():
    for name in CORE_FILES:
        assert (ROOT / name).is_file(), f"{name} is listed in the tracker but missing"


def test_tracker_lists_every_core_file():
    text = _read(TRACKER)
    for name in CORE_FILES:
        assert name in text, f"tracker does not mention core file {name}"


# -- Reading lists include AGENTS.md -------------------------------------------

READING_LISTS = {
    "README.md": "AGENTS.md",
    "CONTRIBUTING.md": "AGENTS.md",
    "CLAUDE.md": "AGENTS.md",
    "docs/en/developers/README.md": "AGENTS.md",
    "docs/en/developers/working-method.md": "AGENTS.md",
}


def test_reading_lists_mention_agents_md():
    for rel, needle in READING_LISTS.items():
        text = _read(ROOT / rel)
        assert needle in text, f"{rel} does not mention {needle}"


def test_tracker_lists_every_reading_list():
    text = _read(TRACKER)
    for rel in READING_LISTS:
        name = Path(rel).name
        assert name in text, f"tracker does not list reading-list file {name}"


# -- Baseline sync -------------------------------------------------------------

def _extract_baseline(text: str) -> str | None:
    """Pull the first 'NNN passed, M skipped' from text."""
    m = re.search(r"(\d+)\s+passed,\s+(\d+)\s+skipped", text)
    if m:
        return f"{m.group(1)} passed, {m.group(2)} skipped"
    return None


def test_tracker_baseline_matches_agents_md():
    """The baseline quoted in the tracker must match AGENTS.md."""
    tracker_baseline = _extract_baseline(_read(TRACKER))
    agents_baseline = _extract_baseline(_read(ROOT / "AGENTS.md"))
    assert tracker_baseline is not None, "tracker has no baseline string"
    assert agents_baseline is not None, "AGENTS.md has no baseline string"
    assert tracker_baseline == agents_baseline, (
        f"tracker says '{tracker_baseline}' but AGENTS.md says "
        f"'{agents_baseline}' — update the tracker"
    )


def test_tracker_baseline_matches_all_listed_files():
    """Every file the tracker says references the baseline must actually
    quote the same number."""
    expected = _extract_baseline(_read(TRACKER))
    assert expected is not None
    passed = expected.split(" passed")[0]

    sync_files = [
        "AGENTS.md",
        "AGENT-HANDOFF.md",
        "README.md",
        "CONTRIBUTING.md",
        "docs/en/developers/working-method.md",
    ]
    for rel in sync_files:
        text = _read(ROOT / rel)
        assert passed in text, (
            f"{rel} does not quote '{passed} passed' — the tracker says it "
            f"should; update the file or the tracker"
        )


# -- Tracker update rule is in AGENTS.md and CLAUDE.md -------------------------

def test_agents_md_has_tracker_update_rule():
    """AGENTS.md must instruct agents to update the tracker when onboarding
    files change."""
    text = _read(ROOT / "AGENTS.md")
    assert "agent-onboarding-tracker" in text, (
        "AGENTS.md must reference the tracker so agents know to update it"
    )


def test_claude_md_has_tracker_update_rule():
    text = _read(ROOT / "CLAUDE.md")
    assert "agent-onboarding-tracker" in text, (
        "CLAUDE.md must reference the tracker so auto-loaded sessions "
        "know to update it"
    )

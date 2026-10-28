"""Tests for connection state descriptors (ROADMAP chapter 27)."""

from crypto_trading_lab.domain.models import ConnectionState
from crypto_trading_lab.exchanges.connection_state_descriptors import (
    ConnectionStateDescriptor,
    get_all_descriptors,
    get_descriptor,
)


class TestConnectionStateDescriptors:
    def test_all_states_have_descriptors(self):
        descriptors = get_all_descriptors()
        assert len(descriptors) == 10
        
        for state in ConnectionState:
            assert any(d.state == state for d in descriptors)
            
    def test_descriptor_has_all_fields(self):
        for state in ConnectionState:
            desc = get_descriptor(state)
            assert isinstance(desc, ConnectionStateDescriptor)
            assert desc.state == state
            assert len(desc.technical_description) > 20
            assert len(desc.beginner_explanation) > 20
            assert len(desc.status_label) > 0
            # Some states may not have troubleshooting links
            assert isinstance(desc.troubleshooting_link, str)
            assert desc.severity in ('info', 'warning', 'error')
            
    def test_beginner_explanations_match_connection_state(self):
        for state in ConnectionState:
            desc = get_descriptor(state)
            # Beginner explanation should match the ConnectionState one
            assert desc.beginner_explanation == state.beginner_explanation
            
    def test_severity_levels(self):
        # Error state should be error severity
        error_desc = get_descriptor(ConnectionState.ERROR)
        assert error_desc.severity == 'error'
        
        # Degraded and reconnecting should be warnings
        degraded_desc = get_descriptor(ConnectionState.DEGRADED)
        assert degraded_desc.severity == 'warning'
        
        reconnecting_desc = get_descriptor(ConnectionState.RECONNECTING)
        assert reconnecting_desc.severity == 'warning'
        
        # Connected should be info
        connected_desc = get_descriptor(ConnectionState.CONNECTED)
        assert connected_desc.severity == 'info'
        
    def test_status_labels_are_user_friendly(self):
        for state in ConnectionState:
            desc = get_descriptor(state)
            # Status labels should be capitalized and readable
            assert desc.status_label[0].isupper()
            assert ' ' in desc.status_label or len(desc.status_label) > 0


def test_every_troubleshooting_link_resolves():
    """Chapter 27: the link must lead somewhere, not just exist as a string.

    The descriptors pointed at `docs/en/user-guide/20-troubleshooting.md`,
    which did not exist, and two states had no link at all. A dead link in a
    troubleshooting panel is worse than no panel: it tells the user where to
    look and then wastes their time.
    """
    import re
    from pathlib import Path

    root = Path(__file__).resolve().parents[2]

    def slugify(heading: str) -> str:
        text = heading.strip().lower()
        text = re.sub(r"[^\w\s-]", "", text)
        return text.replace(" ", "-")

    anchors: dict[Path, set[str]] = {}

    def anchors_of(path: Path) -> set[str]:
        if path not in anchors:
            found = {
                slugify(match.group(2))
                for match in re.finditer(
                    r"^(#{1,6})\s+(.*?)\s*$",
                    path.read_text(encoding="utf-8"),
                    re.MULTILINE,
                )
            }
            anchors[path] = found
        return anchors[path]

    for descriptor in get_all_descriptors():
        link = descriptor.troubleshooting_link
        assert link, f"{descriptor.state.value} has no troubleshooting link"
        target, _, anchor = link.partition("#")
        path = root / target
        assert path.is_file(), f"{link} does not exist"
        assert anchor in anchors_of(path), (
            f"{link} points at a heading that is not in {target}"
        )

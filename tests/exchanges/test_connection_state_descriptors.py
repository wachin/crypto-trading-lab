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

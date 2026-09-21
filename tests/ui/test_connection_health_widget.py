"""Tests for connection health widget (ROADMAP chapter 27)."""

import pytest
from unittest.mock import MagicMock

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication

from crypto_trading_lab.domain.models import ConnectionState
from crypto_trading_lab.ui.connection_health_widget import ConnectionHealthWidget


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


class TestConnectionHealthWidget:
    def test_initial_state(self, qapp):
        widget = ConnectionHealthWidget()
        assert widget._current_state == ConnectionState.DISCONNECTED
        
    def test_update_state_changes_display(self, qapp):
        widget = ConnectionHealthWidget()
        
        widget.update_state(ConnectionState.CONNECTED)
        assert widget._current_state == ConnectionState.CONNECTED
        assert "Connected" in widget.state_label.text()
        
        widget.update_state(ConnectionState.DEGRADED)
        assert widget._current_state == ConnectionState.DEGRADED
        assert "Degraded" in widget.state_label.text()
        
    def test_state_changed_signal(self, qapp):
        widget = ConnectionHealthWidget()
        callback = MagicMock()
        widget.state_changed.connect(callback)
        
        widget.update_state(ConnectionState.CONNECTING)
        callback.assert_called_once_with(
            ConnectionState.CONNECTING,
            widget.explanation_label.text()
        )
        
    def test_all_states_have_display(self, qapp):
        widget = ConnectionHealthWidget()
        
        for state in ConnectionState:
            widget.update_state(state)
            assert widget.state_label.text() != ""
            assert widget.explanation_label.text() != ""
            
    def test_severity_styling(self, qapp):
        widget = ConnectionHealthWidget()
        
        # Error severity
        widget.update_state(ConnectionState.ERROR)
        style = widget.status_frame.styleSheet()
        assert "#d32f2f" in style  # Red border
        
        # Warning severity
        widget.update_state(ConnectionState.DEGRADED)
        style = widget.status_frame.styleSheet()
        assert "#f57c00" in style  # Orange border
        
        # Info severity
        widget.update_state(ConnectionState.CONNECTED)
        style = widget.status_frame.styleSheet()
        assert "#4caf50" in style  # Green border
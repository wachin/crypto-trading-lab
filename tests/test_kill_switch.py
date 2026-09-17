"""Tests for kill switch (ROADMAP.md chapter 59)."""

from __future__ import annotations

import pytest

from crypto_trading_lab.kill_switch import (
    KillSwitch,
    KillSwitchManager,
    KillSwitchState,
)


def test_kill_switch_inactive_by_default():
    """Kill switch should be inactive by default."""
    ks = KillSwitch()
    
    assert ks.state == KillSwitchState.INACTIVE
    assert not ks.is_active()


def test_kill_switch_activation():
    """Should activate kill switch."""
    ks = KillSwitch()
    ks.activate(by="manual", reason="test reason")
    
    assert ks.state == KillSwitchState.ACTIVE
    assert ks.is_active()
    assert ks.activated_by == "manual"
    assert ks.reason == "test reason"


def test_kill_switch_deactivation():
    """Should deactivate kill switch."""
    ks = KillSwitch()
    ks.activate(by="manual")
    ks.deactivate()
    
    assert ks.state == KillSwitchState.INACTIVE
    assert not ks.is_active()


def test_kill_manager_activation():
    """Kill switch manager should activate switch."""
    ks = KillSwitch()
    manager = KillSwitchManager(ks)
    
    manager.activate_on_manual(reason="testing")
    
    assert ks.is_active()


def test_kill_manager_error_activation():
    """Kill switch manager should activate on error."""
    ks = KillSwitch()
    manager = KillSwitchManager(ks)
    
    manager.activate_on_error("System failure")
    
    assert ks.is_active()
    assert ks.activated_by == "system_error"


def test_kill_switch_check_allowed():
    """Check allowed should return false when active."""
    ks = KillSwitch()
    manager = KillSwitchManager(ks)
    
    # Inactive - allowed
    assert manager.check_allowed("trade")
    
    # Active - not allowed
    ks.activate()
    assert not manager.check_allowed("trade")


def test_kill_switch_get_state():
    """Get state should return dict."""
    ks = KillSwitch()
    state = ks.get_state()
    
    assert "state" in state
    assert state["state"] == "inactive"

"""Tests for safety gates (ROADMAP.md chapter 67)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from crypto_trading_lab.safety_gates import (
    GateStatus,
    SafetyGates,
)


def test_data_freshness_pass():
    """Should pass when data is fresh."""
    gates = SafetyGates()
    now = datetime.now(timezone.utc)
    
    result = gates.check_data_freshness(now - timedelta(seconds=30))
    
    assert result.status == GateStatus.PASS


def test_data_freshness_fail():
    """Should fail when data is stale."""
    gates = SafetyGates(data_freshness_seconds=60)
    now = datetime.now(timezone.utc)
    
    result = gates.check_data_freshness(now - timedelta(minutes=2))
    
    assert result.status == GateStatus.FAIL


def test_connection_pass():
    """Should pass when connected."""
    gates = SafetyGates()
    
    result = gates.check_connection_state(True)
    
    assert result.status == GateStatus.PASS


def test_connection_fail():
    """Should fail when not connected."""
    gates = SafetyGates()
    
    result = gates.check_connection_state(False)
    
    assert result.status == GateStatus.FAIL


def test_balance_pass():
    """Should pass when balance is sufficient."""
    gates = SafetyGates()
    
    result = gates.check_balance_verification(Decimal("100"))
    
    assert result.status == GateStatus.PASS


def test_balance_fail():
    """Should fail when balance is too low."""
    gates = SafetyGates(min_balance_verification=Decimal("10"))
    
    result = gates.check_balance_verification(Decimal("5"))
    
    assert result.status == GateStatus.FAIL


def test_risk_limit_pass():
    """Should pass when order risk is within limits."""
    gates = SafetyGates()
    
    result = gates.check_risk_limit(Decimal("0.01"), Decimal("0.02"))
    
    assert result.status == GateStatus.PASS


def test_risk_limit_fail():
    """Should fail when order risk exceeds limits."""
    gates = SafetyGates()
    
    result = gates.check_risk_limit(Decimal("0.05"), Decimal("0.02"))
    
    assert result.status == GateStatus.FAIL


def test_kill_switch_pass():
    """Should pass when kill switch is inactive."""
    gates = SafetyGates()
    
    result = gates.check_kill_switch(False)
    
    assert result.status == GateStatus.PASS


def test_kill_switch_fail():
    """Should fail when kill switch is active."""
    gates = SafetyGates()
    
    result = gates.check_kill_switch(True)
    
    assert result.status == GateStatus.FAIL


def test_check_all_pass():
    """Should pass all checks when conditions are good."""
    gates = SafetyGates()
    now = datetime.now(timezone.utc)
    
    all_passed, results = gates.check_all(
        data_timestamp=now,
        is_connected=True,
        balance=Decimal("1000"),
        order_risk=Decimal("0.01"),
        max_risk=Decimal("0.02"),
        is_kill_switch_active=False,
    )
    
    assert all_passed
    assert len(results) == 5


def test_check_all_fails_on_kill_switch():
    """Should fail all checks when kill switch is active."""
    gates = SafetyGates()
    now = datetime.now(timezone.utc)
    
    all_passed, results = gates.check_all(
        data_timestamp=now,
        is_connected=True,
        balance=Decimal("1000"),
        order_risk=Decimal("0.01"),
        max_risk=Decimal("0.02"),
        is_kill_switch_active=True,
    )
    
    assert not all_passed
    kill_results = [r for r in results if r.gate_type.value == "kill_switch"]
    assert kill_results[0].status == GateStatus.FAIL


def test_history_recorded():
    """Should record gate checks in history."""
    gates = SafetyGates()
    now = datetime.now(timezone.utc)
    
    gates.check_data_freshness(now)
    gates.check_connection_state(True)
    
    history = gates.get_history()
    assert len(history) == 2

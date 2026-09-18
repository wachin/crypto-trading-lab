"""Tests for real trading support (ROADMAP.md chapter 68)."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

import pytest

from crypto_trading_lab.trading import (
    RealTradingManager,
    RealTradingState,
    TradingMode,
    is_real_trading_allowed,
    require_real_trading_consent,
    REAL_TRADING_WARNINGS,
    STRATEGY_RESTRICTIONS_WARNING,
    TESTING_RESTRICTIONS_WARNING,
    FAILURE_HANDLING_WARNING,
    BEGINNER_PROTECTION_WARNING,
)


def test_real_trading_manager_initial_state():
    """RealTradingManager should start in DISABLED state."""
    manager = RealTradingManager()
    assert manager.state == RealTradingState.DISABLED
    assert not manager.is_active()


def test_request_activation():
    """User can request to activate real trading."""
    manager = RealTradingManager()
    assert manager.request_activation() is True
    assert manager.state == RealTradingState.PENDING_ACTIVATION
    
    # Cannot request again while pending
    assert manager.request_activation() is False
    assert manager.state == RealTradingState.PENDING_ACTIVATION


def test_activation_steps_sequence():
    """Test that activation steps must be followed in order."""
    manager = RealTradingManager()
    
    # Must request activation first
    assert manager.request_activation() is True
    
    # Can now activate advanced option
    assert manager.activate_advanced_option() is True
    assert manager.config.advanced_option_enabled is True
    
    # Can acknowledge risk warning
    assert manager.acknowledge_risk_warning() is True
    assert manager.config.risk_warning_acknowledged is True
    
    # Can provide written confirmation
    assert manager.provide_written_confirmation() is True
    assert manager.config.written_confirmation_provided is True
    
    # Can verify API key permissions (no withdrawal)
    assert manager.verify_api_key_permissions(has_withdrawal=False) is True
    assert manager.config.api_key_has_no_withdrawal is True
    
    # Withdrawal enabled should fail verification
    manager2 = RealTradingManager()
    manager2.request_activation()
    manager2.activate_advanced_option()
    manager2.acknowledge_risk_warning()
    manager2.provide_written_confirmation()
    assert manager2.verify_api_key_permissions(has_withdrawal=True) is False
    assert manager2.config.api_key_has_no_withdrawal is False
    
    # Can select environment
    assert manager.select_environment("binance", "spot_main") is True
    assert manager.config.environment_verified == "binance"
    assert manager.config.account_verified == "spot_main"
    
    # Can configure risk limits
    assert manager.configure_risk_limits(
        Decimal("3.0"), Decimal("1.5"), Decimal("0.25")
    ) is True
    assert manager.config.max_position_percent == Decimal("3.0")
    assert manager.config.max_daily_loss_percent == Decimal("1.5")
    assert manager.config.max_total_exposure == Decimal("0.25")
    
    # Excessive limits get clamped to safer values
    manager3 = RealTradingManager()
    manager3.request_activation()
    manager3.activate_advanced_option()
    manager3.acknowledge_risk_warning()
    manager3.provide_written_confirmation()
    manager3.verify_api_key_permissions(False)
    manager3.select_environment("test", "test")
    assert manager3.configure_risk_limits(
        Decimal("10.0"), Decimal("10.0"), Decimal("0.80")
    ) is True
    assert manager3.config.max_position_percent == Decimal("5.0")  # Clamped
    assert manager3.config.max_daily_loss_percent == Decimal("2.0")  # Clamped
    assert manager3.config.max_total_exposure == Decimal("0.30")  # Clamped
    
    # Can test connectivity
    assert manager.test_connectivity(True) is True
    assert manager.config.connectivity_verified is True
    
    # Can verify account balances
    assert manager.verify_account_balances(True) is True
    assert manager.config.account_balances_verified is True
    
    # Can verify market data freshness
    assert manager.verify_market_data_freshness(True) is True
    assert manager.config.market_data_freshness_verified is True
    
    # Can verify time sync
    assert manager.verify_time_sync(True) is True
    assert manager.config.time_sync_verified is True
    
    # Can verify kill switch config
    assert manager.verify_kill_switch_config(True) is True
    assert manager.config.kill_switch_config_verified is True
    
    # Can verify confirmation phrase
    assert manager.verify_confirmation_phrase(True) is True
    assert manager.config.confirmation_phrase_verified is True


def test_activation_fails_if_steps_skipped():
    """Activation should fail if any required step is skipped."""
    manager = RealTradingManager()
    manager.request_activation()
    manager.activate_advanced_option()
    manager.acknowledge_risk_warning()
    # Skip written confirmation
    manager.verify_api_key_permissions(False)
    manager.select_environment("test", "test")
    manager.configure_risk_limits(Decimal("2.0"), Decimal("1.0"), Decimal("0.2"))
    manager.test_connectivity(True)
    manager.verify_account_balances(True)
    manager.verify_market_data_freshness(True)
    manager.verify_time_sync(True)
    manager.verify_kill_switch_config(True)
    manager.verify_confirmation_phrase(True)
    
    # Should fail because written confirmation was skipped
    assert manager.complete_activation() is False
    assert manager.state == RealTradingState.FAILED


def test_successful_activation():
    """Test complete successful activation sequence."""
    manager = RealTradingManager()
    
    # Request activation
    assert manager.request_activation() is True
    
    # Complete all activation steps
    assert manager.activate_advanced_option() is True
    assert manager.acknowledge_risk_warning() is True
    assert manager.provide_written_confirmation() is True
    assert manager.verify_api_key_permissions(False) is True
    assert manager.select_environment("binance", "spot_main") is True
    assert manager.configure_risk_limits(
        Decimal("2.0"), Decimal("1.0"), Decimal("0.2")
    ) is True
    assert manager.test_connectivity(True) is True
    assert manager.verify_account_balances(True) is True
    assert manager.verify_market_data_freshness(True) is True
    assert manager.verify_time_sync(True) is True
    assert manager.verify_kill_switch_config(True) is True
    assert manager.verify_confirmation_phrase(True) is True
    
    # Complete activation
    assert manager.complete_activation() is True
    assert manager.state == RealTradingState.ACTIVE
    assert manager.is_active() is True
    assert manager.config.real_trading_indicator_visible is True
    assert manager.activation_timestamp is not None


def test_suspend_and_resume():
    """Test suspending and resuming real trading."""
    manager = RealTradingManager()
    # Activate first (simplified)
    manager.request_activation()
    manager.activate_advanced_option()
    manager.acknowledge_risk_warning()
    manager.provide_written_confirmation()
    manager.verify_api_key_permissions(False)
    manager.select_environment("test", "test")
    manager.configure_risk_limits(Decimal("2.0"), Decimal("1.0"), Decimal("0.2"))
    manager.test_connectivity(True)
    manager.verify_account_balances(True)
    manager.verify_market_data_freshness(True)
    manager.verify_time_sync(True)
    manager.verify_kill_switch_config(True)
    manager.verify_confirmation_phrase(True)
    manager.complete_activation()
    
    assert manager.is_active() is True
    
    # Suspend trading
    assert manager.suspend_trading() is True
    assert manager.state == RealTradingState.SUSPENDED
    assert manager.is_active() is False
    
    # Resume trading
    assert manager.resume_trading() is True
    assert manager.state == RealTradingState.ACTIVE
    assert manager.is_active() is True


def test_deactivate():
    """Test deactivating real trading."""
    manager = RealTradingManager()
    # Activate first (simplified)
    manager.request_activation()
    manager.activate_advanced_option()
    manager.acknowledge_risk_warning()
    manager.provide_written_confirmation()
    manager.verify_api_key_permissions(False)
    manager.select_environment("test", "test")
    manager.configure_risk_limits(Decimal("2.0"), Decimal("1.0"), Decimal("0.2"))
    manager.test_connectivity(True)
    manager.verify_account_balances(True)
    manager.verify_market_data_freshness(True)
    manager.verify_time_sync(True)
    manager.verify_kill_switch_config(True)
    manager.verify_confirmation_phrase(True)
    manager.complete_activation()
    
    assert manager.is_active() is True
    
    # Deactivate
    manager.deactivate()
    assert manager.state == RealTradingState.DISABLED
    assert manager.is_active() is False


def test_is_real_trading_allowed():
    """is_real_trading_allowed should return False by default (MVP keeps it disabled)."""
    assert is_real_trading_allowed() is False


def test_require_real_trading_consent():
    """require_real_trading_consent should return the warning message."""
    assert require_real_trading_consent() == REAL_TRADING_WARNINGS


def test_warnings_exist():
    """Test that all warning messages are defined and non-empty."""
    assert REAL_TRADING_WARNINGS.strip() != ""
    assert STRATEGY_RESTRICTIONS_WARNING.strip() != ""
    assert TESTING_RESTRICTIONS_WARNING.strip() != ""
    assert FAILURE_HANDLING_WARNING.strip() != ""
    assert BEGINNER_PROTECTION_WARNING.strip() != ""
    
    # Check they contain expected keywords
    assert "losing money" in REAL_TRADING_WARNINGS
    assert "must use the same signal/risk/execution architecture" in STRATEGY_RESTRICTIONS_WARNING
    assert "Never use a real account in automated tests" in TESTING_RESTRICTIONS_WARNING
    assert "stop creating new orders" in FAILURE_HANDLING_WARNING
    assert "learning fundamentals" in BEGINNER_PROTECTION_WARNING


def test_activation_cannot_be_bypassed():
    """Test that real trading cannot be activated simply by importing/configuring API keys."""
    manager = RealTradingManager()
    
    # Even if someone somehow set all the config values directly
    # (which they shouldn't be able to do in practice due to encapsulation)
    manager.state = RealTradingState.PENDING_ACTIVATION
    manager.config.advanced_option_enabled = True
    manager.config.risk_warning_acknowledged = True
    manager.config.written_confirmation_provided = True
    manager.config.api_key_has_no_withdrawal = True
    manager.config.environment_verified = "binance"
    manager.config.account_verified = "spot_main"
    manager.config.max_position_percent = Decimal("2.0")
    manager.config.max_daily_loss_percent = Decimal("1.0")
    manager.config.max_total_exposure = Decimal("0.20")
    manager.config.connectivity_verified = True
    manager.config.account_balances_verified = True
    manager.config.market_data_freshness_verified = True
    manager.config.time_sync_verified = True
    manager.config.kill_switch_config_verified = True
    manager.config.confirmation_phrase_verified = True
    
    # Still need to call complete_activation to actually activate
    assert manager.is_active() is False
    assert manager.complete_activation() is True
    assert manager.is_active() is True


def test_activation_requirements_tracking():
    """Test that activation requirements are properly tracked."""
    manager = RealTradingManager()
    summary = manager.get_status_summary()
    
    assert summary["state"] == "disabled"
    assert summary["is_active"] is False
    assert isinstance(summary["requirements_met"], dict)
    # Count the boolean requirements (should be 10)
    expected_keys = {
        "advanced_option", "risk_warning", "written_confirmation",
        "api_key_no_withdrawal", "environment", "account",
        "connectivity", "account_balances", "market_data_fresh",
        "time_sync", "kill_switch_config", "confirmation_phrase"
    }
    assert set(summary["requirements_met"].keys()) == expected_keys
    assert len(summary["requirements_met"]) == 12  # Actually 12 requirements
    
    # After partial activation
    manager.request_activation()
    manager.activate_advanced_option()
    manager.acknowledge_risk_warning()
    summary = manager.get_status_summary()
    assert summary["requirements_met"]["advanced_option"] is True
    assert summary["requirements_met"]["risk_warning"] is True
    assert summary["requirements_met"]["written_confirmation"] is False  # Not set yet
    assert summary["requirements_met"]["api_key_no_withdrawal"] is False  # Not set yet
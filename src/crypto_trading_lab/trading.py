"""Real trading support (ROADMAP.md chapter 68).

Real trading support must remain behind multiple independent safety protections.
The MVP keeps real trading completely disabled through a feature flag.
Real trading must never become active simply because an API key or exchange 
configuration was imported.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Optional


class TradingMode(Enum):
    """Trading mode enumeration (68.4)."""
    BACKTEST = "backtest"
    PAPER = "paper"
    TESTNET = "testnet"
    REAL = "real"


class RealTradingState(Enum):
    """Real trading activation state."""
    DISABLED = "disabled"          # Default state
    PENDING_ACTIVATION = "pending"  # User initiated activation process
    ACTIVE = "active"              # Fully activated for real trading
    SUSPENDED = "suspended"        # Temporarily suspended due to safety check
    FAILED = "failed"              # Activation failed due to invalid credentials/etc.


@dataclass
class RealTradingConfig:
    """Configuration for real trading activation (68.1, 68.2)."""
    # Activation requirements
    advanced_option_enabled: bool = False
    risk_warning_acknowledged: bool = False
    written_confirmation_provided: bool = False
    api_key_has_no_withdrawal: bool = False  # Must be verified
    environment_verified: str = ""           # selected exchange
    account_verified: str = ""               # selected account/environment
    
    # Risk limits (must be configured strictly)
    max_position_percent: Decimal = Decimal("5.0")   # More conservative than paper
    max_daily_loss_percent: Decimal = Decimal("2.0") 
    max_total_exposure: Decimal = Decimal("0.30")    # 30% of portfolio
    
    # Connectivity and data requirements
    connectivity_verified: bool = False
    account_balances_verified: bool = False
    market_data_freshness_verified: bool = False
    time_sync_verified: bool = False
    kill_switch_config_verified: bool = False
    
    # Final confirmation
    confirmation_phrase_verified: bool = False
    real_trading_indicator_visible: bool = False


@dataclass
class RealTradingManager:
    """
    Manages real trading activation and safety (68).
    
    Implements multiple independent safety protections as required by
    Chapter 68. Real trading remains disabled by default and requires
    explicit multi-step activation.
    """
    state: RealTradingState = RealTradingState.DISABLED
    config: RealTradingConfig = field(default_factory=RealTradingConfig)
    activation_timestamp: Optional[datetime] = None
    
    # Safety requirements from Chapter 68.3
    _risk_manager_override_attempts: int = 0
    _credential_access_attempts: int = 0
    _strategy_modification_attempts: int = 0
    
    def request_activation(self) -> bool:
        """
        User requests to activate real trading (68.1).
        
        Returns True if activation request was accepted for processing.
        """
        if self.state != RealTradingState.DISABLED:
            return False
            
        self.state = RealTradingState.PENDING_ACTIVATION
        return True
    
    def activate_advanced_option(self) -> bool:
        """Step 1: Enable explicit advanced option (68.1.1)."""
        if self.state != RealTradingState.PENDING_ACTIVATION:
            return False
        self.config.advanced_option_enabled = True
        return True
    
    def acknowledge_risk_warning(self) -> bool:
        """Step 2: Display and acknowledge prominent risk warning (68.1.2)."""
        if self.state != RealTradingState.PENDING_ACTIVATION:
            return False
        self.config.risk_warning_acknowledged = True
        return True
    
    def provide_written_confirmation(self) -> bool:
        """Step 3: Require written confirmation (68.1.3)."""
        if self.state != RealTradingState.PENDING_ACTIVATION:
            return False
        self.config.written_confirmation_provided = True
        return True
    
    def verify_api_key_permissions(self, has_withdrawal: bool = True) -> bool:
        """Step 4: Check API key has no withdrawal permission (68.1.4, 68.2)."""
        if self.state != RealTradingState.PENDING_ACTIVATION:
            return False
        # In reality, this would check actual exchange API permissions
        self.config.api_key_has_no_withdrawal = not has_withdrawal
        return not has_withdrawal  # Return True only if NO withdrawal permission
    
    def select_environment(self, exchange: str, account: str) -> bool:
        """Steps 5-6: Display selected exchange and account (68.1.5-68.1.6)."""
        if self.state != RealTradingState.PENDING_ACTIVATION:
            return False
        self.config.environment_verified = exchange
        self.config.account_verified = account
        return True
    
    def configure_risk_limits(self, max_position_pct: Decimal, 
                            max_daily_loss_pct: Decimal,
                            max_total_exposure: Decimal) -> bool:
        """Step 8: Configure strict risk limits (68.1.8)."""
        if self.state != RealTradingState.PENDING_ACTIVATION:
            return False
        # Apply more conservative limits for real trading
        self.config.max_position_percent = min(max_position_pct, Decimal("5.0"))
        self.config.max_daily_loss_percent = min(max_daily_loss_pct, Decimal("2.0"))
        self.config.max_total_exposure = min(max_total_exposure, Decimal("0.30"))
        return True
    
    def test_connectivity(self, is_connected: bool) -> bool:
        """Step 9: Test connectivity (68.1.9)."""
        if self.state != RealTradingState.PENDING_ACTIVATION:
            return False
        self.config.connectivity_verified = is_connected
        return is_connected
    
    def verify_account_balances(self, has_sufficient_funds: bool) -> bool:
        """Step 10: Verify account balances (68.1.10)."""
        if self.state != RealTradingState.PENDING_ACTIVATION:
            return False
        self.config.account_balances_verified = has_sufficient_funds
        return has_sufficient_funds
    
    def verify_market_data_freshness(self, is_fresh: bool) -> bool:
        """Step 11: Verify market-data freshness (68.1.11)."""
        if self.state != RealTradingState.PENDING_ACTIVATION:
            return False
        self.config.market_data_freshness_verified = is_fresh
        return is_fresh
    
    def verify_time_sync(self, is_sync: bool) -> bool:
        """Step 12: Verify system time synchronization (68.1.12)."""
        if self.state != RealTradingState.PENDING_ACTIVATION:
            return False
        self.config.time_sync_verified = is_sync
        return is_sync
    
    def verify_kill_switch_config(self, is_configured: bool) -> bool:
        """Step 13: Confirm emergency kill switch configuration (68.1.13)."""
        if self.state != RealTradingState.PENDING_ACTIVATION:
            return False
        self.config.kill_switch_config_verified = is_configured
        return is_configured
    
    def verify_confirmation_phrase(self, phrase_correct: bool) -> bool:
        """Step 14: Require confirmation phrase (68.1.14)."""
        if self.state != RealTradingState.PENDING_ACTIVATION:
            return False
        self.config.confirmation_phrase_verified = phrase_correct
        return phrase_correct
    
    def complete_activation(self) -> bool:
        """Complete real trading activation after all steps passed (68.1.15)."""
        if self.state != RealTradingState.PENDING_ACTIVATION:
            return False
        
        # Check ALL requirements are met
        all_requirements_met = (
            self.config.advanced_option_enabled and
            self.config.risk_warning_acknowledged and
            self.config.written_confirmation_provided and
            self.config.api_key_has_no_withdrawal and
            bool(self.config.environment_verified) and
            bool(self.config.account_verified) and
            self.config.connectivity_verified and
            self.config.account_balances_verified and
            self.config.market_data_freshness_verified and
            self.config.time_sync_verified and
            self.config.kill_switch_config_verified and
            self.config.confirmation_phrase_verified
        )
        
        if all_requirements_met:
            self.state = RealTradingState.ACTIVE
            self.activation_timestamp = datetime.now(timezone.utc)
            self.config.real_trading_indicator_visible = True
            return True
        else:
            self.state = RealTradingState.FAILED
            return False
    
    def suspend_trading(self) -> bool:
        """Suspend real trading due to safety condition (68.6)."""
        if self.state == RealTradingState.ACTIVE:
            self.state = RealTradingState.SUSPENDED
            return True
        return False
    
    def resume_trading(self) -> bool:
        """Resume trading after suspension if conditions are met."""
        if self.state == RealTradingState.SUSPENDED:
            # In reality, would re-check all safety conditions
            self.state = RealTradingState.ACTIVE
            return True
        return False
    
    def deactivate(self) -> None:
        """Deactivate real trading and reset to disabled state."""
        self.state = RealTradingState.DISABLED
        self.__init__()  # Reset to initial state
    
    def is_active(self) -> bool:
        """Check if real trading is currently active."""
        return self.state == RealTradingState.ACTIVE
    
    def get_status_summary(self) -> dict:
        """Get human-readable status summary for display."""
        return {
            "state": self.state.value,
            "is_active": self.is_active(),
            "activation_timestamp": (
                self.activation_timestamp.isoformat() 
                if self.activation_timestamp else None
            ),
            "requirements_met": {
                "advanced_option": self.config.advanced_option_enabled,
                "risk_warning": self.config.risk_warning_acknowledged,
                "written_confirmation": self.config.written_confirmation_provided,
                "api_key_no_withdrawal": self.config.api_key_has_no_withdrawal,
                "environment": bool(self.config.environment_verified),
                "account": bool(self.config.account_verified),
                "connectivity": self.config.connectivity_verified,
                "account_balances": self.config.account_balances_verified,
                "market_data_fresh": self.config.market_data_freshness_verified,
                "time_sync": self.config.time_sync_verified,
                "kill_switch_config": self.config.kill_switch_config_verified,
                "confirmation_phrase": self.config.confirmation_phrase_verified,
            },
            "risk_limits": {
                "max_position_percent": str(self.config.max_position_percent),
                "max_daily_loss_percent": str(self.config.max_daily_loss_percent),
                "max_total_exposure": str(self.config.max_total_exposure),
            }
        }


# Safety warnings and restrictions (68.3, 68.4, 68.6, 68.7)

REAL_TRADING_WARNINGS = (
    "Real trading involves the possibility of losing money. Historical performance, "
    "backtesting, paper trading, or statistical analysis cannot guarantee future profits. "
    "Only activate real trading after completing all safety steps and understanding the risks."
)

STRATEGY_RESTRICTIONS_WARNING = (
    "Real trading strategies must use the same signal/risk/execution architecture. "
    "Strategies must never modify risk limits or bypass the RiskManager."
)

TESTING_RESTRICTIONS_WARNING = (
    "Never use a real account in automated tests. Never send real orders from unit tests. "
    "Never enable real trading automatically. Never use real credentials in test fixtures."
)

FAILURE_HANDLING_WARNING = (
    "If a critical safety condition occurs: stop creating new orders, notify the user clearly, "
    "log the event, activate appropriate risk protection, and preserve the audit trail."
)

BEGINNER_PROTECTION_WARNING = (
    "Strongly recommend: learning fundamentals, testing historically, using out-of-sample "
    "evaluation, testing strategy robustness, paper trading, using testnet where supported, "
    "and starting with very limited exposure if choosing to trade real funds."
)


def is_real_trading_allowed() -> bool:
    """
    Check if real trading is currently allowed (safety gate).
    
    This function should be called before any real order execution.
    """
    # In a full implementation, this would check the global RealTradingManager instance
    # For now, return False to keep real trading disabled by default as required
    return False


def require_real_trading_consent() -> str:
    """
    Get the consent message that must be displayed before real trading activation.
    
    Returns the warning message that users must acknowledge.
    """
    return REAL_TRADING_WARNINGS
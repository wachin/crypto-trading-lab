"""Tests for safety gates (ROADMAP.md chapter 67)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from crypto_trading_lab.domain.models import OrderRequest, OrderSide, OrderType, Symbol
from crypto_trading_lab.safety_gates import (
    Environment,
    EnvironmentSwitchError,
    GateStatus,
    GateType,
    SafetyGates,
    SafetyGateError,
)


def _btc() -> Symbol:
    return Symbol("BTC/USDT")


def _order(qty: Decimal = Decimal("0.1"), price: Decimal | None = None) -> OrderRequest:
    return OrderRequest(
        symbol=_btc(),
        side=OrderSide.BUY,
        order_type=OrderType.MARKET if price is None else OrderType.LIMIT,
        quantity=qty,
        price=price,
    )


def test_data_freshness_pass():
    gates = SafetyGates()
    now = datetime.now(timezone.utc)
    assert gates.check_data_freshness(now - timedelta(seconds=30)).status == GateStatus.PASS


def test_data_freshness_fail():
    gates = SafetyGates(data_freshness_seconds=60)
    now = datetime.now(timezone.utc)
    assert gates.check_data_freshness(now - timedelta(minutes=2)).status == GateStatus.FAIL


def test_connection_pass():
    gates = SafetyGates()
    assert gates.check_connection_state(True).status == GateStatus.PASS


def test_connection_fail():
    gates = SafetyGates()
    assert gates.check_connection_state(False).status == GateStatus.FAIL


def test_balance_pass():
    gates = SafetyGates()
    assert gates.check_balance_verification(Decimal("100")).status == GateStatus.PASS


def test_balance_fail():
    gates = SafetyGates(min_balance_verification=Decimal("10"))
    assert gates.check_balance_verification(Decimal("5")).status == GateStatus.FAIL


def test_risk_limit_pass():
    gates = SafetyGates()
    assert gates.check_risk_limit(Decimal("0.01"), Decimal("0.02")).status == GateStatus.PASS


def test_risk_limit_fail():
    gates = SafetyGates()
    assert gates.check_risk_limit(Decimal("0.05"), Decimal("0.02")).status == GateStatus.FAIL


def test_kill_switch_pass():
    gates = SafetyGates()
    assert gates.check_kill_switch(False).status == GateStatus.PASS


def test_kill_switch_fail():
    gates = SafetyGates()
    assert gates.check_kill_switch(True).status == GateStatus.FAIL


def test_environment_pass():
    gates = SafetyGates(environment=Environment.PAPER_TRADING)
    assert gates.check_environment(Environment.PAPER_TRADING).status == GateStatus.PASS


def test_environment_fail():
    gates = SafetyGates(environment=Environment.BACKTEST)
    assert gates.check_environment(Environment.REAL_TRADING).status == GateStatus.FAIL


def test_real_trading_disabled_by_default():
    gates = SafetyGates(environment=Environment.REAL_TRADING)
    assert gates.check_real_trading_disabled().status == GateStatus.FAIL


def test_real_trading_allowed_when_enabled():
    gates = SafetyGates(environment=Environment.REAL_TRADING, real_trading_enabled=True)
    assert gates.check_real_trading_disabled().status == GateStatus.PASS


def test_exchange_constraint():
    gates = SafetyGates(expected_exchange="binance")
    assert gates.check_exchange("binance").status == GateStatus.PASS
    assert gates.check_exchange("kraken").status == GateStatus.FAIL


def test_account_constraint():
    gates = SafetyGates(expected_account="main")
    assert gates.check_account("main").status == GateStatus.PASS
    assert gates.check_account("other").status == GateStatus.FAIL


def test_order_parameters_pass():
    gates = SafetyGates()
    assert gates.check_order_parameters(_order()).status == GateStatus.PASS



def test_market_constraints_pass():
    gates = SafetyGates(allowed_symbols=frozenset({"BTC/USDT"}))
    assert gates.check_market_constraints(_btc()).status == GateStatus.PASS


def test_market_constraints_fail():
    gates = SafetyGates(allowed_symbols=frozenset({"ETH/USDT"}))
    assert gates.check_market_constraints(_btc()).status == GateStatus.FAIL


def test_position_limits():
    gates = SafetyGates(max_position=Decimal("1"))
    assert gates.check_position_limits(Decimal("0.5")).status == GateStatus.PASS
    assert gates.check_position_limits(Decimal("2")).status == GateStatus.FAIL


def test_exposure_limits():
    gates = SafetyGates(max_exposure=Decimal("1000"))
    assert gates.check_exposure_limits(Decimal("500")).status == GateStatus.PASS
    assert gates.check_exposure_limits(Decimal("2000")).status == GateStatus.FAIL


def test_evaluate_order_all_pass():
    gates = SafetyGates(environment=Environment.PAPER_TRADING)
    now = datetime.now(timezone.utc)
    allowed, results = gates.evaluate_order(
        request=_order(),
        data_timestamp=now,
        is_connected=True,
        balance=Decimal("1000"),
        order_risk=Decimal("0.01"),
        max_risk=Decimal("0.02"),
        is_kill_switch_active=False,
    )
    assert allowed
    assert all(r.status is not GateStatus.FAIL for r in results)


def test_evaluate_order_blocks_on_kill_switch():
    gates = SafetyGates(environment=Environment.PAPER_TRADING)
    now = datetime.now(timezone.utc)
    allowed, results = gates.evaluate_order(
        request=_order(),
        data_timestamp=now,
        is_connected=True,
        balance=Decimal("1000"),
        order_risk=Decimal("0.01"),
        max_risk=Decimal("0.02"),
        is_kill_switch_active=True,
    )
    assert not allowed
    kill = [r for r in results if r.gate_type is GateType.KILL_SWITCH]
    assert kill[0].status == GateStatus.FAIL


def test_evaluate_order_blocks_real_trading_when_disabled():
    gates = SafetyGates(environment=Environment.REAL_TRADING)
    now = datetime.now(timezone.utc)
    allowed, _ = gates.evaluate_order(
        request=_order(),
        data_timestamp=now,
        is_connected=True,
        balance=Decimal("1000"),
        order_risk=Decimal("0.01"),
        max_risk=Decimal("0.02"),
        is_kill_switch_active=False,
    )
    assert not allowed


def test_check_all_pass_backwards_compat():
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
    assert any(r.gate_type is GateType.ENVIRONMENT for r in results)


def test_check_all_fails_on_kill_switch():
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
    kill_results = [r for r in results if r.gate_type is GateType.KILL_SWITCH]
    assert kill_results[0].status == GateStatus.FAIL


def test_history_recorded():
    gates = SafetyGates()
    now = datetime.now(timezone.utc)
    gates.check_data_freshness(now)
    gates.check_connection_state(True)
    assert len(gates.get_history()) == 2


def test_environment_switch_requires_confirmation():
    gates = SafetyGates(environment=Environment.BACKTEST)
    try:
        gates.request_environment_switch(Environment.PAPER_TRADING, confirmed=False)
        assert False, "expected EnvironmentSwitchError"
    except EnvironmentSwitchError:
        pass
    assert gates.environment is Environment.BACKTEST


def test_environment_switch_with_confirmation():
    gates = SafetyGates(environment=Environment.BACKTEST)
    out = gates.request_environment_switch(Environment.PAPER_TRADING, confirmed=True)
    assert out is Environment.PAPER_TRADING
    assert gates.environment is Environment.PAPER_TRADING


def test_environment_switch_to_real_trading_blocked_when_disabled():
    gates = SafetyGates(environment=Environment.PAPER_TRADING)
    try:
        gates.request_environment_switch(Environment.REAL_TRADING, confirmed=True)
        assert False, "expected SafetyGateError"
    except SafetyGateError:
        pass
    assert gates.environment is Environment.PAPER_TRADING


def test_apply_configuration_requires_confirmation():
    gates = SafetyGates()
    try:
        gates.apply_configuration({"expected_exchange": "binance"}, confirmed=False)
        assert False, "expected SafetyGateError"
    except SafetyGateError:
        pass
    assert gates.expected_exchange is None


def test_apply_configuration_sets_exchange_with_confirmation():
    gates = SafetyGates()
    gates.apply_configuration({"expected_exchange": "binance"}, confirmed=True)
    assert gates.expected_exchange == "binance"

"""Tests for ROADMAP chapters 62 (live monitoring) and 63 (live vs backtest drift).

Covers the newly wired items: volatility/latency drift (63.1), drift
education (63.3), the monitored-state model and alert rules (62.1/62.2).
Offline and deterministic.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from crypto_trading_lab.live_vs_backtest import (
    DriftMetric,
    MonitoredState,
    drift_education,
    latency_drift,
    monitoring_alerts,
    volatility_drift,
    volatility_of_returns,
)

D = Decimal


def _curve(values):
    return [D(str(v)) for v in values]


def test_volatility_of_returns_is_zero_for_flat_curve():
    assert volatility_of_returns(_curve([100, 100, 100, 100])) == D(0)


def test_volatility_of_returns_detects_variation():
    vol = volatility_of_returns(_curve([100, 110, 95, 120, 90]))
    assert vol > 0


def test_volatility_of_returns_short_curve_is_zero():
    assert volatility_of_returns(_curve([100])) == D(0)
    assert volatility_of_returns(_curve([100, 110])) == D(0)


def test_volatility_drift_metric_shape():
    backtest = _curve([100, 101, 103, 102, 105])
    live = _curve([100, 99, 104, 98, 106])
    metric = volatility_drift(backtest, live)
    assert isinstance(metric, DriftMetric)
    assert metric.name == "volatility"
    assert metric.backtest_value == volatility_of_returns(backtest)
    assert metric.live_value == volatility_of_returns(live)
    assert metric.significance in ("low", "medium", "high")


def test_latency_drift_small_is_low_significance():
    metric = latency_drift(D("0.10"), D("0.12"))
    assert metric.name == "latency"
    assert metric.significance == "low"
    assert metric.difference == D("0.02")


def test_latency_drift_large_is_high_significance():
    metric = latency_drift(D("0.10"), D("0.50"))
    assert metric.significance == "high"
    assert metric.pct_difference > D("0.25") * 2


def test_latency_drift_zero_expected_is_high_when_actual_nonzero():
    metric = latency_drift(D("0"), D("0.05"))
    assert metric.significance == "high"
    metric_zero = latency_drift(D("0"), D("0"))
    assert metric_zero.significance == "low"


def test_drift_education_has_two_sentences():
    edu = drift_education()
    assert len(edu) == 2
    for sentence in edu:
        assert sentence[0].isupper()
        assert sentence.endswith(".")


def test_monitored_state_carries_all_62_1_fields():
    state = MonitoredState(
        portfolio_value=D("1000.00"),
        open_positions=3,
        pending_orders=1,
        executed_orders=12,
        fees=D("0.50"),
        slippage=D("0.10"),
        drawdown=D("0.05"),
        exposure=D("0.30"),
        risk_decisions="reduced exposure",
        connection_state="connected",
        data_freshness="10s old",
        environment="paper",
        kill_switch_status="armed",
    )
    assert state.portfolio_value == D("1000.00")
    assert state.open_positions == 3
    assert state.kill_switch_status == "armed"
    assert state.recent_alerts == ()


def test_monitoring_alerts_flags_risky_state():
    state = MonitoredState(
        portfolio_value=D("1000"),
        drawdown=D("0.25"),
        environment="real",
        kill_switch_status="disarmed",
        connection_state="down",
        recent_alerts=("slippage rising",),
    )
    alerts = monitoring_alerts(state)
    assert "environment is real" in alerts
    assert "kill switch is not armed" in alerts
    assert "connection is down" in alerts
    assert "drawdown exceeds 20 percent" in alerts


def test_monitoring_alerts_clean_when_all_good():
    state = MonitoredState(
        portfolio_value=D("1000"),
        drawdown=D("0.05"),
        environment="paper",
        kill_switch_status="armed",
        connection_state="connected",
    )
    alerts = monitoring_alerts(state)
    assert alerts == ["environment is paper"]


def test_monitoring_alerts_blank_environment_reports_nothing():
    state = MonitoredState(portfolio_value=D("1000"))
    assert monitoring_alerts(state) == []


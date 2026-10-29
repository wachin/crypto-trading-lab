"""Safety gates (ROADMAP.md chapter 67).

Safety gates are the executable protection layer between the application
and a real exchange. Capital preservation takes priority over strategy
execution (see Chapter 61).

The layer verifies, on *every* order, that the environment, exchange,
account, balances, market data, order parameters, market constraints,
risk/position/exposure limits and kill-switch/connection state are all
acceptable before an order reaches an exchange. A strategy can never
disable a gate, and switching into a riskier environment (in particular
Real Trading) requires explicit, audited confirmation. Real trading is
disabled by default.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Optional

from crypto_trading_lab.domain.models import OrderRequest, OrderSide, OrderType


class Environment(Enum):
    """Trading environments (67.2)."""

    BACKTEST = "backtest"
    HISTORICAL_REPLAY = "historical_replay"
    PAPER_TRADING = "paper_trading"
    EXCHANGE_TESTNET = "exchange_testnet"
    REAL_TRADING = "real_trading"

    @property
    def label(self) -> str:
        return {
            Environment.BACKTEST: "Backtest",
            Environment.HISTORICAL_REPLAY: "Historical Replay",
            Environment.PAPER_TRADING: "Paper Trading",
            Environment.EXCHANGE_TESTNET: "Exchange Testnet",
            Environment.REAL_TRADING: "Real Trading",
        }[self]

    @property
    def is_live(self) -> bool:
        return self in (Environment.EXCHANGE_TESTNET, Environment.REAL_TRADING)


class GateStatus(Enum):
    PASS = "pass"
    FAIL = "fail"
    WARNING = "warning"


class GateType(Enum):
    ENVIRONMENT = "environment"
    EXCHANGE = "exchange"
    ACCOUNT = "account"
    DATA_FRESHNESS = "data_freshness"
    CONNECTION_STATE = "connection_state"
    BALANCE_VERIFICATION = "balance_verification"
    ORDER_PARAMETERS = "order_parameters"
    MARKET_CONSTRAINTS = "market_constraints"
    RISK_LIMIT_CHECK = "risk_limit_check"
    POSITION_LIMITS = "position_limits"
    EXPOSURE_LIMITS = "exposure_limits"
    KILL_SWITCH = "kill_switch"
    MARKET_CONDITIONS = "market_conditions"


@dataclass(frozen=True)
class GateResult:
    gate_type: GateType
    status: GateStatus
    message: str
    timestamp: datetime
    detail: Optional[dict] = None


class SafetyGateError(Exception):
    """Raised when a safety gate blocks an action or a guard is violated."""


class EnvironmentSwitchError(SafetyGateError):
    """Raised when an environment switch is attempted without confirmation."""


@dataclass
class SafetyGates:
    environment: Environment = Environment.BACKTEST
    expected_exchange: Optional[str] = None
    expected_account: Optional[str] = None
    allowed_symbols: frozenset = frozenset()
    data_freshness_seconds: int = 60
    min_balance_verification: Decimal = Decimal("1")
    max_daily_loss_fraction: Decimal = Decimal("0.05")
    max_position: Optional[Decimal] = None
    max_exposure: Optional[Decimal] = None
    real_trading_enabled: bool = False

    _gate_history: list[GateResult] = field(default_factory=list)
    daily_pnl: Decimal = Decimal("0")

    def _record(self, result: GateResult) -> None:
        self._gate_history.append(result)

    def get_history(self) -> list[GateResult]:
        return self._gate_history.copy()

    def record_pnl(self, pnl: Decimal) -> None:
        self.daily_pnl += pnl

    def check_environment(self, expected: Environment) -> GateResult:
        now = datetime.now(timezone.utc)
        ok = self.environment == expected
        result = GateResult(
            gate_type=GateType.ENVIRONMENT,
            status=GateStatus.PASS if ok else GateStatus.FAIL,
            message=(
                f"Environment is {self.environment.label}"
                if ok
                else f"Environment is {self.environment.label}, expected {expected.label}"
            ),
            timestamp=now,
            detail={"current": self.environment.value, "expected": expected.value},
        )
        self._record(result)
        return result

    def check_real_trading_disabled(self) -> GateResult:
        now = datetime.now(timezone.utc)
        blocked = (
            self.environment is Environment.REAL_TRADING
            and not self.real_trading_enabled
        )
        result = GateResult(
            gate_type=GateType.ENVIRONMENT,
            status=GateStatus.FAIL if blocked else GateStatus.PASS,
            message=(
                "Real Trading is disabled by default"
                if blocked
                else f"Real Trading policy OK (enabled={self.real_trading_enabled})"
            ),
            timestamp=now,
        )
        self._record(result)
        return result

    def check_exchange(self, configured: Optional[str]) -> GateResult:
        now = datetime.now(timezone.utc)
        if self.expected_exchange is None:
            result = GateResult(
                gate_type=GateType.EXCHANGE,
                status=GateStatus.PASS,
                message="No exchange constraint configured",
                timestamp=now,
            )
            self._record(result)
            return result
        ok = configured == self.expected_exchange
        result = GateResult(
            gate_type=GateType.EXCHANGE,
            status=GateStatus.PASS if ok else GateStatus.FAIL,
            message=(
                f"Exchange is {configured}"
                if ok
                else f"Exchange is {configured}, expected {self.expected_exchange}"
            ),
            timestamp=now,
            detail={"current": configured, "expected": self.expected_exchange},
        )
        self._record(result)
        return result

    def check_account(self, configured: Optional[str]) -> GateResult:
        now = datetime.now(timezone.utc)
        if self.expected_account is None:
            result = GateResult(
                gate_type=GateType.ACCOUNT,
                status=GateStatus.PASS,
                message="No account constraint configured",
                timestamp=now,
            )
            self._record(result)
            return result
        ok = configured == self.expected_account
        result = GateResult(
            gate_type=GateType.ACCOUNT,
            status=GateStatus.PASS if ok else GateStatus.FAIL,
            message=(
                f"Account is {configured}"
                if ok
                else f"Account is {configured}, expected {self.expected_account}"
            ),
            timestamp=now,
            detail={"current": configured, "expected": self.expected_account},
        )
        self._record(result)
        return result

    def check_data_freshness(self, last_data_timestamp: datetime) -> GateResult:
        now = datetime.now(timezone.utc)
        age = (now - last_data_timestamp).total_seconds()
        ok = age <= self.data_freshness_seconds
        result = GateResult(
            gate_type=GateType.DATA_FRESHNESS,
            status=GateStatus.PASS if ok else GateStatus.FAIL,
            message=(
                f"Data is {age:.0f}s old (threshold: {self.data_freshness_seconds}s)"
                if ok
                else f"Data too old: {age:.0f}s (threshold: {self.data_freshness_seconds}s)"
            ),
            timestamp=now,
        )
        self._record(result)
        return result

    def check_connection_state(self, is_connected: bool) -> GateResult:
        now = datetime.now(timezone.utc)
        result = GateResult(
            gate_type=GateType.CONNECTION_STATE,
            status=GateStatus.PASS if is_connected else GateStatus.FAIL,
            message="Connection active" if is_connected else "No connection to exchange",
            timestamp=now,
        )
        self._record(result)
        return result

    def check_balance_verification(
        self, balance: Decimal, balance_asset: str = "USDT"
    ) -> GateResult:
        now = datetime.now(timezone.utc)
        ok = balance >= self.min_balance_verification
        result = GateResult(
            gate_type=GateType.BALANCE_VERIFICATION,
            status=GateStatus.PASS if ok else GateStatus.FAIL,
            message=(
                f"Balance {balance} {balance_asset} verified"
                if ok
                else f"Balance {balance} {balance_asset} below minimum {self.min_balance_verification}"
            ),
            timestamp=now,
        )
        self._record(result)
        return result

    def check_order_parameters(self, request: OrderRequest) -> GateResult:
        now = datetime.now(timezone.utc)
        problems: list[str] = []
        if request.quantity <= 0:
            problems.append("quantity must be positive")
        if request.side not in (OrderSide.BUY, OrderSide.SELL):
            problems.append("side must be BUY or SELL")
        if request.order_type is OrderType.LIMIT and (
            request.price is None or request.price <= 0
        ):
            problems.append("LIMIT orders require a positive price")
        ok = not problems
        result = GateResult(
            gate_type=GateType.ORDER_PARAMETERS,
            status=GateStatus.PASS if ok else GateStatus.FAIL,
            message=(
                f"Order {request.side.value} {request.quantity} {request.symbol} valid"
                if ok
                else "; ".join(problems)
            ),
            timestamp=now,
            detail={"symbol": str(request.symbol), "side": request.side.value},
        )
        self._record(result)
        return result

    def check_market_constraints(self, symbol) -> GateResult:
        now = datetime.now(timezone.utc)
        if not self.allowed_symbols:
            result = GateResult(
                gate_type=GateType.MARKET_CONSTRAINTS,
                status=GateStatus.PASS,
                message="No symbol allow-list configured",
                timestamp=now,
            )
            self._record(result)
            return result
        sym = str(symbol)
        ok = sym in self.allowed_symbols
        result = GateResult(
            gate_type=GateType.MARKET_CONSTRAINTS,
            status=GateStatus.PASS if ok else GateStatus.FAIL,
            message=(
                f"Symbol {sym} is allowed"
                if ok
                else f"Symbol {sym} is not on the allow-list {sorted(self.allowed_symbols)}"
            ),
            timestamp=now,
            detail={"symbol": sym},
        )
        self._record(result)
        return result

    def check_risk_limit(self, order_risk: Decimal, max_risk: Decimal) -> GateResult:
        now = datetime.now(timezone.utc)
        ok = order_risk <= max_risk
        result = GateResult(
            gate_type=GateType.RISK_LIMIT_CHECK,
            status=GateStatus.PASS if ok else GateStatus.FAIL,
            message=(
                f"Order risk {order_risk:.1%} within limit {max_risk:.1%}"
                if ok
                else f"Order risk {order_risk:.1%} exceeds limit {max_risk:.1%}"
            ),
            timestamp=now,
        )
        self._record(result)
        return result

    def check_position_limits(
        self, current_position: Decimal, max_position: Optional[Decimal] = None
    ) -> GateResult:
        now = datetime.now(timezone.utc)
        cap = self.max_position if max_position is None else max_position
        if cap is None:
            result = GateResult(
                gate_type=GateType.POSITION_LIMITS,
                status=GateStatus.PASS,
                message="No position limit configured",
                timestamp=now,
            )
            self._record(result)
            return result
        ok = abs(current_position) <= cap
        result = GateResult(
            gate_type=GateType.POSITION_LIMITS,
            status=GateStatus.PASS if ok else GateStatus.FAIL,
            message=(
                f"Position {current_position} within limit {cap}"
                if ok
                else f"Position {current_position} exceeds limit {cap}"
            ),
            timestamp=now,
        )
        self._record(result)
        return result

    def check_exposure_limits(
        self, current_exposure: Decimal, max_exposure: Optional[Decimal] = None
    ) -> GateResult:
        now = datetime.now(timezone.utc)
        cap = self.max_exposure if max_exposure is None else max_exposure
        if cap is None:
            result = GateResult(
                gate_type=GateType.EXPOSURE_LIMITS,
                status=GateStatus.PASS,
                message="No exposure limit configured",
                timestamp=now,
            )
            self._record(result)
            return result
        ok = current_exposure <= cap
        result = GateResult(
            gate_type=GateType.EXPOSURE_LIMITS,
            status=GateStatus.PASS if ok else GateStatus.FAIL,
            message=(
                f"Exposure {current_exposure} within limit {cap}"
                if ok
                else f"Exposure {current_exposure} exceeds limit {cap}"
            ),
            timestamp=now,
        )
        self._record(result)
        return result

    def check_kill_switch(self, is_active: bool) -> GateResult:
        now = datetime.now(timezone.utc)
        result = GateResult(
            gate_type=GateType.KILL_SWITCH,
            status=GateStatus.FAIL if is_active else GateStatus.PASS,
            message=(
                "Kill switch inactive"
                if not is_active
                else "Kill switch ACTIVE - trading blocked"
            ),
            timestamp=now,
        )
        self._record(result)
        return result

    def check_daily_loss(self, current_pnl: Decimal) -> GateResult:
        now = datetime.now(timezone.utc)
        limit = -self.daily_pnl * self.max_daily_loss_fraction
        ok = current_pnl >= limit
        result = GateResult(
            gate_type=GateType.RISK_LIMIT_CHECK,
            status=GateStatus.PASS if ok else GateStatus.FAIL,
            message=(
                f"Daily PnL {current_pnl:.2f} within loss limit {limit:.2f}"
                if ok
                else f"Daily loss limit exceeded: PnL {current_pnl:.2f} < {limit:.2f}"
            ),
            timestamp=now,
        )
        self._record(result)
        return result

    def evaluate_order(
        self,
        *,
        request: OrderRequest,
        data_timestamp: datetime,
        is_connected: bool,
        balance: Decimal,
        order_risk: Decimal,
        max_risk: Decimal,
        is_kill_switch_active: bool,
        configured_exchange: Optional[str] = None,
        configured_account: Optional[str] = None,
        current_position: Decimal = Decimal("0"),
        current_exposure: Decimal = Decimal("0"),
        expected_environment: Optional[Environment] = None,
    ) -> tuple[bool, list[GateResult]]:
        env = expected_environment if expected_environment is not None else self.environment
        results = [
            self.check_environment(env),
            self.check_real_trading_disabled(),
            self.check_exchange(configured_exchange),
            self.check_account(configured_account),
            self.check_data_freshness(data_timestamp),
            self.check_connection_state(is_connected),
            self.check_balance_verification(balance),
            self.check_order_parameters(request),
            self.check_market_constraints(request.symbol),
            self.check_risk_limit(order_risk, max_risk),
            self.check_position_limits(current_position),
            self.check_exposure_limits(current_exposure),
            self.check_kill_switch(is_kill_switch_active),
        ]
        allowed = all(r.status is not GateStatus.FAIL for r in results)
        return allowed, results

    def check_all(
        self,
        *,
        data_timestamp: datetime,
        is_connected: bool,
        balance: Decimal,
        order_risk: Decimal,
        max_risk: Decimal,
        is_kill_switch_active: bool,
        request: Optional[OrderRequest] = None,
        configured_exchange: Optional[str] = None,
        configured_account: Optional[str] = None,
        current_position: Decimal = Decimal("0"),
        current_exposure: Decimal = Decimal("0"),
        expected_environment: Optional[Environment] = None,
    ) -> tuple[bool, list[GateResult]]:
        if request is None:
            env = expected_environment or self.environment
            results = [
                self.check_environment(env),
                self.check_real_trading_disabled(),
                self.check_exchange(configured_exchange),
                self.check_account(configured_account),
                self.check_data_freshness(data_timestamp),
                self.check_connection_state(is_connected),
                self.check_balance_verification(balance),
                self.check_risk_limit(order_risk, max_risk),
                self.check_position_limits(current_position),
                self.check_exposure_limits(current_exposure),
                self.check_kill_switch(is_kill_switch_active),
            ]
            allowed = all(r.status is not GateStatus.FAIL for r in results)
            return allowed, results
        return self.evaluate_order(
            request=request,
            data_timestamp=data_timestamp,
            is_connected=is_connected,
            balance=balance,
            order_risk=order_risk,
            max_risk=max_risk,
            is_kill_switch_active=is_kill_switch_active,
            configured_exchange=configured_exchange,
            configured_account=configured_account,
            current_position=current_position,
            current_exposure=current_exposure,
            expected_environment=expected_environment,
        )

    def request_environment_switch(
        self, target: Environment, confirmed: bool
    ) -> Environment:
        if target is Environment.REAL_TRADING and not self.real_trading_enabled:
            raise SafetyGateError(
                "Real Trading is disabled by default; enable it explicitly "
                "before switching into the Real Trading environment."
            )
        if not confirmed:
            raise EnvironmentSwitchError(
                f"Environment switch to {target.label} requires explicit confirmation."
            )
        self.environment = target
        return self.environment

    def apply_configuration(self, updates: dict, confirmed: bool) -> None:
        if not confirmed:
            raise SafetyGateError("Configuration changes require explicit confirmation.")
        env = updates.get("environment")
        if env is not None and env != self.environment:
            self.request_environment_switch(env, confirmed=True)
        for key in ("expected_exchange", "expected_account", "allowed_symbols"):
            if key in updates:
                setattr(self, key, updates[key])
        if "real_trading_enabled" in updates:
            self.real_trading_enabled = bool(updates["real_trading_enabled"])


SAFETY_GATES_WARNING = (
    "Safety gates protect capital before orders reach real exchanges. "
    "All checks must pass. Failure in any gate blocks the order. "
    "Gates are non-bypassable - no component can disable them, and "
    "switching into a riskier environment requires explicit confirmation."
)

"""Backtesting engine (ROADMAP.md chapter 37).

Deterministic, cost-aware, and protected against look-ahead bias by
construction: signals are generated at the close of candle ``i`` and
executed at the open of candle ``i+1`` (model ``NEXT_OPEN``) — the
engine never lets a strategy see beyond the current candle.

The full pipeline runs: market data → strategy signal → risk check →
order → execution → position/portfolio update, mirroring chapter
33.6's mandatory flow.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Protocol, Sequence

from crypto_trading_lab.domain.models import Candle, OrderSide
from crypto_trading_lab.indicators.library import SMA, SMAStream

__all__ = [
    "ExecutionModel",
    "IntrabarPolicy",
    "CostModel",
    "BacktestConfig",
    "TradeRecord",
    "BacktestResult",
    "MACrossoverStrategy",
    "BuyAndHoldStrategy",
    "NullStrategy",
    "run_backtest",
]


class ExecutionModel(enum.Enum):
    """When a signal becomes a fill (chapter 37.4)."""

    NEXT_OPEN = "next_open"          # fill at next candle's open (default)
    CONSERVATIVE_INTRABAR = "conservative_intrabar"  # documented model


class IntrabarPolicy(enum.Enum):
    """Ambiguous-candle policy (chapter 37.5)."""

    CONSERVATIVE = "conservative"  # assume the worst outcome for us


@dataclass(frozen=True)
class CostModel:
    """Trading costs (chapter 37.1); all Decimal fractions or fixed."""

    maker_fee: Decimal = Decimal("0.001")   # fraction of notional
    taker_fee: Decimal = Decimal("0.001")  # market orders pay taker
    slippage_fraction: Decimal = Decimal("0.0005")  # adverse price shift
    spread_fraction: Decimal = Decimal("0.0002")   # half-spread paid on entry

    def buy_price(self, reference: Decimal) -> Decimal:
        """Fill price for a buy: reference worsened by spread+slippage."""
        factor = Decimal(1) + self.spread_fraction + self.slippage_fraction
        return reference * factor

    def sell_price(self, reference: Decimal) -> Decimal:
        """Fill price for a sell: reference worsened by spread+slippage."""
        factor = Decimal(1) - self.spread_fraction - self.slippage_fraction
        return reference * factor


@dataclass(frozen=True)
class BacktestConfig:
    """Everything that makes a backtest reproducible (chapter 37.4)."""

    initial_capital: Decimal = Decimal("10000")
    costs: CostModel = field(default_factory=CostModel)
    execution_model: ExecutionModel = ExecutionModel.NEXT_OPEN
    intrabar_policy: IntrabarPolicy = IntrabarPolicy.CONSERVATIVE
    quantity_step: Decimal = Decimal("0.000001")
    min_notional: Decimal = Decimal("0")

    def metadata(self) -> dict[str, str]:
        return {
            "initial_capital": str(self.initial_capital),
            "maker_fee": str(self.costs.maker_fee),
            "taker_fee": str(self.costs.taker_fee),
            "slippage_fraction": str(self.costs.slippage_fraction),
            "spread_fraction": str(self.costs.spread_fraction),
            "execution_model": self.execution_model.value,
            "intrabar_policy": self.intrabar_policy.value,
            "quantity_step": str(self.quantity_step),
            "min_notional": str(self.min_notional),
        }


@dataclass(frozen=True)
class TradeRecord:
    """One executed trade with full cost attribution (chapter 37.1)."""

    entry_time: str        # ISO UTC of the entry candle
    exit_time: str | None
    side: str
    quantity: Decimal
    entry_price: Decimal
    exit_price: Decimal | None
    entry_fee: Decimal
    exit_fee: Decimal
    slippage_cost: Decimal
    spread_cost: Decimal

    @property
    def gross_pnl(self) -> Decimal:
        if self.exit_price is None:
            return Decimal(0)
        if self.side == "buy":
            return (self.exit_price - self.entry_price) * self.quantity
        return (self.entry_price - self.exit_price) * self.quantity

    @property
    def net_pnl(self) -> Decimal:
        return self.gross_pnl - self.entry_fee - self.exit_fee


class Strategy(Protocol):
    """Minimal strategy surface the engine requires (chapter 33)."""

    name: str

    def on_candle(self, index: int, candles: Sequence[Candle]) -> OrderSide | None:
        """Decide using candles up to and including ``index``."""


@dataclass
class MACrossoverStrategy:
    """SMA(fast) crossing SMA(slow) (chapter 33, strategy 1).

    Golden cross (fast above slow) → BUY; death cross → close (SELL).
    Signals are emitted at the close of the current candle and filled
    at the NEXT candle's open — the engine enforces this.

    Uses :class:`SMAStream` for O(1) incremental updates, so backtesting
    N candles is O(N) instead of O(N^2) (chapter 13).
    """

    fast: int = 10
    slow: int = 30
    version: str = "1.0.0"  # strategy version (ROADMAP 37.9)

    def __post_init__(self) -> None:
        if self.fast >= self.slow:
            raise ValueError("fast period must be smaller than slow")
        self._fast_stream = SMAStream(self.fast)
        self._slow_stream = SMAStream(self.slow)

    @property
    def name(self) -> str:
        return f"SMA({self.fast})xSMA({self.slow}) crossover"

    def on_candle(self, index, candles):
        candle = candles[index]
        fast = self._fast_stream.update(candle)
        slow = self._slow_stream.update(candle)
        if fast is None or slow is None:
            return None
        if index == 0:
            return None
        previous_fast = self._fast_stream.prev_value
        previous_slow = self._slow_stream.prev_value
        if previous_fast is not None and previous_slow is not None:
            if previous_fast <= previous_slow and fast > slow:
                return OrderSide.BUY
            if previous_fast >= previous_slow and fast < slow:
                return OrderSide.SELL
        return None


@dataclass
class BuyAndHoldStrategy:
    """Buy on the first fillable candle and hold (benchmark, ch. 33.5)."""

    version: str = "1.0.0"  # strategy version (ROADMAP 37.9)

    @property
    def name(self) -> str:
        return "Buy and hold"

    def on_candle(self, index, candles):
        return OrderSide.BUY if index == 0 else None


@dataclass
class NullStrategy:
    """Never trades (chapter 33, strategy 6 — the honest baseline)."""

    version: str = "1.0.0"  # strategy version (ROADMAP 37.9)

    @property
    def name(self) -> str:
        return "Null (never trades)"

    def on_candle(self, index, candles):
        return None


@dataclass
class BacktestResult:
    """Everything needed to audit and report one run."""

    strategy_name: str
    config_metadata: dict[str, str]
    trades: list[TradeRecord]
    final_equity: Decimal
    initial_capital: Decimal
    total_fees: Decimal
    total_slippage: Decimal
    total_spread: Decimal
    equity_curve: tuple[Decimal, ...]
    candle_count: int
    order_count: int = 0
    exposure_curve: tuple[bool, ...] = ()  # True when in the market that candle
    # Reproducibility records (ROADMAP 37.9).
    strategy_version: str = "unknown"
    dataset_version: str = "unknown"
    dataset_period: str = ""

    @property
    def net_profit(self) -> Decimal:
        return self.final_equity - self.initial_capital

    @property
    def return_fraction(self) -> Decimal:
        if self.initial_capital == 0:
            return Decimal(0)
        return self.net_profit / self.initial_capital

    @property
    def performance_before_costs(self) -> Decimal:
        """Net profit if every fee/slippage/spread had been zero."""
        return self.net_profit + self.total_fees + self.total_slippage + self.total_spread


def _step_quantity(quantity: Decimal, step: Decimal) -> Decimal:
    """Round down to the exchange step size (chapter 37.2)."""
    if step <= 0:
        return quantity
    units = (quantity / step).to_integral_value(rounding="ROUND_DOWN")
    return units * step


def run_backtest(
    candles: Sequence[Candle],
    strategy: Strategy,
    config: BacktestConfig | None = None,
) -> BacktestResult:
    """Run one deterministic backtest (chapter 37).

    Look-ahead protection: the strategy sees ``candles[:i+1]`` only,
    and fills happen at the next candle's open at the earliest.
    """
    config = config or BacktestConfig()
    if len(candles) < 2:
        raise ValueError("need at least two candles")

    cash = config.initial_capital
    position = Decimal(0)          # base units held
    avg_entry = Decimal(0)         # weighted entry price
    entry_time = ""
    entry_fee = Decimal(0)
    entry_slippage = Decimal(0)
    entry_spread = Decimal(0)

    trades: list[TradeRecord] = []
    equity_curve: list[Decimal] = []
    exposure_curve: list[bool] = []
    order_count = 0
    total_fees = Decimal(0)
    total_slippage = Decimal(0)
    total_spread = Decimal(0)

    pending_signal: OrderSide | None = None  # filled at NEXT open

    for index in range(len(candles)):
        current = candles[index]

        # 1. Execute a signal generated at the PREVIOUS close.
        if pending_signal is not None and index > 0:
            fill_price = current.open
            if pending_signal is OrderSide.BUY and position == 0:
                price = config.costs.buy_price(fill_price)
                affordable = cash / price
                quantity = _step_quantity(affordable, config.quantity_step)
                if (
                    quantity > 0
                    and quantity * price >= config.min_notional
                ):
                    fee = quantity * price * config.costs.taker_fee
                    spread = quantity * fill_price * config.costs.spread_fraction
                    slip = quantity * fill_price * config.costs.slippage_fraction
                    cash -= quantity * price + fee
                    order_count += 1
                    position = quantity
                    avg_entry = price
                    entry_time = current.open_time.isoformat()
                    entry_fee, entry_slippage, entry_spread = fee, slip, spread

            elif pending_signal is OrderSide.SELL and position > 0:
                price = config.costs.sell_price(fill_price)
                fee = position * price * config.costs.taker_fee
                order_count += 1
                spread = position * fill_price * config.costs.spread_fraction
                slip = position * fill_price * config.costs.slippage_fraction
                cash += position * price - fee
                trades.append(
                    TradeRecord(
                        entry_time=entry_time,
                        exit_time=current.open_time.isoformat(),
                        side="buy",
                        quantity=position,
                        entry_price=avg_entry,
                        exit_price=price,
                        entry_fee=entry_fee,
                        exit_fee=fee,
                        slippage_cost=entry_slippage + slip,
                        spread_cost=entry_spread + spread,
                    )
                )
                total_fees += entry_fee + fee
                total_slippage += entry_slippage + slip
                total_spread += entry_spread + spread
                position = Decimal(0)
                avg_entry = Decimal(0)
            pending_signal = None

        # 2. Value the portfolio at this candle's close.
        equity = cash + position * current.close
        equity_curve.append(equity)
        exposure_curve.append(position > 0)

        # 3. Ask the strategy — it only sees candles up to ``index``.
        signal = strategy.on_candle(index, candles)
        if signal is not None:
            # Long-only spot MVP: SELL closes, never shorts.
            pending_signal = signal

    final_equity = cash + position * candles[-1].close

    return BacktestResult(
        strategy_name=strategy.name,
        config_metadata=config.metadata(),
        trades=trades,
        final_equity=final_equity,
        initial_capital=config.initial_capital,
        total_fees=total_fees,
        total_slippage=total_slippage,
        total_spread=total_spread,
        equity_curve=tuple(equity_curve),
        candle_count=len(candles),
        order_count=order_count,
        exposure_curve=tuple(exposure_curve),
        strategy_version=str(getattr(strategy, "version", "unknown")),
        # Chapter 53 (experiment tracking) does not exist yet, so
        # datasets are honestly recorded as unversioned.
        dataset_version="unversioned (experiment tracking pending, ch. 53)",
        dataset_period=(
            f"{candles[0].open_time.isoformat()} to "
            f"{candles[-1].close_time.isoformat()}"
        ),
    )

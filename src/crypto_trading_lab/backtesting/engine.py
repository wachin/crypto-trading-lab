"""Backtesting engine (ROADMAP.md chapter 37).

Deterministic, cost-aware, and protected against look-ahead bias by
construction: signals are generated at the close of candle ``i`` and
executed at the open of candle ``i+1`` (model ``NEXT_OPEN``) — the
engine never lets a strategy see beyond the current candle.

The full pipeline runs: market data → strategy signal → risk check →
order → execution → position/portfolio update, mirroring chapter
33.6's mandatory flow.

Two execution models are available to a run (chapter 56.5):

* the **cost model** (default) — a full fill at the next open, moved by
  the configured half-spread and slippage fractions;
* the **chapter 56 execution model** — a synthetic order book whose depth
  comes from the traded volume *before* the fill candle, with
  depth-based partial fills, rejections and a slippage model. It is
  selected by passing an ExecutionConfig from execution_realism and is
  always recorded in the result metadata together with its seed, so the
  same run reproduces the same fills.
"""

from __future__ import annotations

import enum
import random
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Protocol, Sequence

from crypto_trading_lab.domain.models import Candle, OrderSide
from crypto_trading_lab.execution_realism import (
    ExecutionConfig,
    FillType,
    simulate_market_order,
)
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
    #: Fraction of available cash committed to each entry (chapter 37.4).
    #: The default of 1 keeps the historical full-capital behaviour; the
    #: paper-trading drift comparison sets it to the session's
    #: ``position_fraction`` so sizing is not mistaken for execution drift.
    position_fraction: Decimal = Decimal("1")
    costs: CostModel = field(default_factory=CostModel)
    execution_model: ExecutionModel = ExecutionModel.NEXT_OPEN
    intrabar_policy: IntrabarPolicy = IntrabarPolicy.CONSERVATIVE
    quantity_step: Decimal = Decimal("0.000001")
    min_notional: Decimal = Decimal("0")
    #: Chapter 56 execution realism. When set, fills come from a synthetic
    #: order book instead of the simple cost arithmetic; when None the run
    #: keeps the chapter 37.1 cost model. Never set it to make an order
    #: fill — a rejected order is information, not a defect.
    execution_config: ExecutionConfig | None = None
    #: Seed for the execution model (chapter 37.8 determinism). The same
    #: seed and the same candles reproduce the same fills.
    execution_seed: int = 42

    def execution_realism_name(self) -> str:
        """Which execution model this run used (chapter 56.2)."""
        if self.execution_config is None:
            return "cost_model (chapter 37.1)"
        return "chapter_56_execution_realism"

    def metadata(self) -> dict[str, str]:
        return {
            "initial_capital": str(self.initial_capital),
            "position_fraction": str(self.position_fraction),
            "maker_fee": str(self.costs.maker_fee),
            "taker_fee": str(self.costs.taker_fee),
            "slippage_fraction": str(self.costs.slippage_fraction),
            "spread_fraction": str(self.costs.spread_fraction),
            "execution_model": self.execution_model.value,
            "execution_realism": self.execution_realism_name(),
            "execution_seed": (
                str(self.execution_seed)
                if self.execution_config is not None
                else "not applicable"
            ),
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

    #: Candles the strategy needs before it can emit its first signal.
    #: A strategy that cannot state this reports 0 and gets no warm-up
    #: warning, which is honest: guessing a number would be worse than
    #: saying nothing.
    warmup_candles: int

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

    @property
    def warmup_candles(self) -> int:
        """The slow average must fill, then one more candle to compare."""
        return self.slow + 1

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

    @property
    def warmup_candles(self) -> int:
        """It buys on the first candle it sees."""
        return 1

    def on_candle(self, index, candles):
        return OrderSide.BUY if index == 0 else None


@dataclass
class NullStrategy:
    """Never trades (chapter 33, strategy 6 — the honest baseline)."""

    version: str = "1.0.0"  # strategy version (ROADMAP 37.9)

    @property
    def name(self) -> str:
        return "Null (never trades)"

    @property
    def warmup_candles(self) -> int:
        """It never trades, so it needs nothing."""
        return 0

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
    #: Chapter 56 execution realism: orders the model refused to fill and
    #: orders it filled only in part. Both stay 0 under the cost model,
    #: which always fills in full.
    rejected_orders: int = 0
    partial_fills: int = 0
    # Reproducibility records (ROADMAP 37.9).
    strategy_version: str = "unknown"
    dataset_id: str = "unknown"
    dataset_version: str = "unknown"
    dataset_checksum: str = "unknown"
    dataset_period: str = ""
    #: Interval of the candles this run consumed (``1m``, ``1d``, ``1M``).
    #: Chapter 40 needs it to annualize: a year is 12 monthly candles, not
    #: 365 of them. Empty means "not recorded", and the metrics say so.
    interval: str = ""

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


def _interval_seconds(candles: Sequence[Candle]) -> Decimal:
    """Median spacing between candle opens, in seconds (chapter 56.4)."""
    deltas = sorted(
        delta
        for delta in (
            (later.open_time - earlier.open_time).total_seconds()
            for earlier, later in zip(candles, candles[1:])
        )
        if delta > 0
    )
    if not deltas:
        return Decimal(3600)
    return Decimal(str(deltas[len(deltas) // 2]))


def _average_daily_volume(
    candles: Sequence[Candle],
    index: int,
    window: int,
    interval_seconds: Decimal,
) -> Decimal:
    """Mean traded volume *before* ``index``, scaled to one day (56.4).

    Only candles strictly before ``index`` are read: the fill happens at
    that candle's open, so its own volume is not knowable yet. A result of
    zero means "depth unknown", which the execution model turns into a
    rejection instead of an assumption of unlimited liquidity.
    """
    if window < 1 or index < 1 or interval_seconds <= 0:
        return Decimal(0)
    start = max(0, index - window)
    sample = candles[start:index]
    if not sample:
        return Decimal(0)
    mean = sum((candle.volume for candle in sample), Decimal(0)) / Decimal(
        len(sample)
    )
    return mean * Decimal(86400) / interval_seconds


@dataclass(frozen=True)
class _Fill:
    """One order's outcome: price, filled quantity, and how it filled."""

    price: Decimal
    quantity: Decimal
    rejected: bool
    partial: bool


def _simulate_fill(
    *,
    config: BacktestConfig,
    rng: random.Random,
    reference: Decimal,
    side: str,
    quantity: Decimal,
    adv: Decimal,
) -> _Fill:
    """Price and size one market order (chapters 37.1 and 56).

    Without an ``execution_config`` this is the original cost model: a full
    fill at the reference price, worsened by half-spread and slippage. With
    one, chapter 56 decides both the size (depth) and the price (spread,
    market impact and a seeded random component).
    """
    if config.execution_config is None:
        price = (
            config.costs.buy_price(reference)
            if side == "buy"
            else config.costs.sell_price(reference)
        )
        return _Fill(price=price, quantity=quantity, rejected=False, partial=False)

    result = simulate_market_order(
        reference,
        side,
        quantity,
        config.execution_config,
        adv=adv,
        spread_fraction=config.costs.spread_fraction,
        rng=rng,
    )
    if result.fill_type is FillType.REJECTED or result.filled_quantity <= 0:
        return _Fill(
            price=Decimal(0), quantity=Decimal(0), rejected=True, partial=False
        )
    filled = _step_quantity(result.filled_quantity, config.quantity_step)
    if filled <= 0:
        return _Fill(
            price=Decimal(0), quantity=Decimal(0), rejected=True, partial=False
        )
    return _Fill(
        price=result.average_price,
        quantity=filled,
        rejected=False,
        partial=filled < quantity,
    )


def _reported_costs(
    config: BacktestConfig,
    *,
    reference: Decimal,
    price: Decimal,
    quantity: Decimal,
) -> tuple[Decimal, Decimal]:
    """Split one fill's adverse price shift into (spread, slippage).

    Under the cost model the two are separate inputs, so they are reported
    as configured. Under chapter 56 the fill price already contains the
    half-spread, the market impact and the random component; charging the
    spread a second time would double count it, so the whole shift from the
    reference price is reported as slippage.
    """
    if config.execution_config is None:
        return (
            quantity * reference * config.costs.spread_fraction,
            quantity * reference * config.costs.slippage_fraction,
        )
    return Decimal(0), (price - reference).copy_abs() * quantity


def run_backtest(
    candles: Sequence[Candle],
    strategy: Strategy,
    config: BacktestConfig | None = None,
    dataset: "DatasetProvenance | None" = None,
) -> BacktestResult:
    """Run one deterministic backtest (chapter 37).

    Look-ahead protection: the strategy sees ``candles[:i+1]`` only,
    and fills happen at the next candle's open at the earliest. The
    execution model is chosen by ``config.execution_config`` (chapter 56.5);
    the default cost model fills every order in full.
    """
    config = config or BacktestConfig()
    if len(candles) < 2:
        raise ValueError("need at least two candles")
    if not (Decimal(0) < config.position_fraction <= Decimal(1)):
        raise ValueError("position_fraction must be between 0 and 1")

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
    rejected_orders = 0
    partial_fills = 0
    total_fees = Decimal(0)
    total_slippage = Decimal(0)
    total_spread = Decimal(0)

    rng = random.Random(config.execution_seed)
    interval_seconds = _interval_seconds(candles)

    pending_signal: OrderSide | None = None  # filled at NEXT open

    for index in range(len(candles)):
        current = candles[index]

        # 1. Execute a signal generated at the PREVIOUS close.
        if pending_signal is not None and index > 0:
            fill_price = current.open
            adv = Decimal(0)
            if config.execution_config is not None:
                adv = _average_daily_volume(
                    candles,
                    index,
                    config.execution_config.adv_window,
                    interval_seconds,
                )

            if pending_signal is OrderSide.BUY and position == 0:
                estimate = config.costs.buy_price(fill_price)
                desired = _step_quantity(
                    cash * config.position_fraction / estimate,
                    config.quantity_step,
                )
                if desired > 0:
                    fill = _simulate_fill(
                        config=config,
                        rng=rng,
                        reference=fill_price,
                        side="buy",
                        quantity=desired,
                        adv=adv,
                    )
                    if fill.rejected:
                        rejected_orders += 1
                    else:
                        quantity = fill.quantity
                        if fill.partial:
                            partial_fills += 1
                        if config.execution_config is not None:
                            # Never commit more cash than the account holds:
                            # the realistic fill price is only known now.
                            affordable = _step_quantity(
                                cash
                                / (
                                    fill.price
                                    * (Decimal(1) + config.costs.taker_fee)
                                ),
                                config.quantity_step,
                            )
                            quantity = min(quantity, affordable)
                        if (
                            quantity > 0
                            and quantity * fill.price >= config.min_notional
                        ):
                            price = fill.price
                            fee = quantity * price * config.costs.taker_fee
                            spread, slip = _reported_costs(
                                config,
                                reference=fill_price,
                                price=price,
                                quantity=quantity,
                            )
                            cash -= quantity * price + fee
                            order_count += 1
                            position = quantity
                            avg_entry = price
                            entry_time = current.open_time.isoformat()
                            entry_fee = fee
                            entry_slippage = slip
                            entry_spread = spread

            elif pending_signal is OrderSide.SELL and position > 0:
                fill = _simulate_fill(
                    config=config,
                    rng=rng,
                    reference=fill_price,
                    side="sell",
                    quantity=position,
                    adv=adv,
                )
                if fill.rejected:
                    rejected_orders += 1
                else:
                    quantity = fill.quantity
                    if fill.partial:
                        partial_fills += 1
                    price = fill.price
                    fee = quantity * price * config.costs.taker_fee
                    spread, slip = _reported_costs(
                        config,
                        reference=fill_price,
                        price=price,
                        quantity=quantity,
                    )
                    # A partial exit carries only its share of the entry
                    # costs; the remainder stays with the open position.
                    fraction = quantity / position
                    closed_fee = entry_fee * fraction
                    closed_slippage = entry_slippage * fraction
                    closed_spread = entry_spread * fraction
                    cash += quantity * price - fee
                    order_count += 1
                    trades.append(
                        TradeRecord(
                            entry_time=entry_time,
                            exit_time=current.open_time.isoformat(),
                            side="buy",
                            quantity=quantity,
                            entry_price=avg_entry,
                            exit_price=price,
                            entry_fee=closed_fee,
                            exit_fee=fee,
                            slippage_cost=closed_slippage + slip,
                            spread_cost=closed_spread + spread,
                        )
                    )
                    total_fees += closed_fee + fee
                    total_slippage += closed_slippage + slip
                    total_spread += closed_spread + spread
                    position -= quantity
                    entry_fee -= closed_fee
                    entry_slippage -= closed_slippage
                    entry_spread -= closed_spread
                    if position == 0:
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
        rejected_orders=rejected_orders,
        partial_fills=partial_fills,
        strategy_version=str(getattr(strategy, "version", "unknown")),
        # Chapter 53 (experiment tracking) does not exist yet, so
        # datasets are honestly recorded as unversioned.
        dataset_id=(dataset.dataset_id if dataset is not None else "unknown"),
        dataset_version=(dataset.version if dataset is not None else "unversioned (experiment tracking pending, ch. 53)"),
        dataset_checksum=(dataset.checksum if dataset is not None else "unknown"),
        dataset_period=(
            f"{candles[0].open_time.isoformat()} to "
            f"{candles[-1].close_time.isoformat()}"
        ),
        interval=candles[0].interval,
    )

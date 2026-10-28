"""Paper trading over real market data, with a mandatory risk gate and a
trading journal (ROADMAP.md chapter 57, analysis §10, §11, §13).

This is a *replay* engine: it walks real candles in chronological order,
lets a strategy decide at each close, passes every intended order through
the chapter-58 risk manager, fills at the next candle's open with fees,
spread and slippage, and writes a journal entry for every decision —
approved or rejected.

It never touches an exchange and never uses real money. Two data sources
feed it: a stored dataset replayed candle by candle (the default), or the
continuous Binance WebSocket feed (chapter 26.2) through
:func:`run_paper_session_live`, which applies the same risk gate, the same
execution model and the same journal to live candles.
"""

from __future__ import annotations

import asyncio
import json
import logging
import random
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Sequence

from crypto_trading_lab.backtesting.engine import CostModel
from crypto_trading_lab.domain.models import (
    Candle,
    ConnectionState,
    OrderSide,
    Symbol,
)
from crypto_trading_lab.execution_realism import (
    ExecutionConfig,
    simulate_market_order,
)
from crypto_trading_lab.market_data.historical import TIMEFRAMES, DatasetVersion
from crypto_trading_lab.risk_manager import (
    LossLimits,
    OperationalLimits,
    OrderRequest as RiskOrderRequest,
    PortfolioState,
    RiskDecision,
    RiskLimits,
    RiskManager,
)

try:
    from crypto_trading_lab.exchanges.binance.websocket_client import (
        BinanceWebSocketClient,
    )
    from crypto_trading_lab.exchanges.binance.config import (
        BinanceEndpoints,
        BINANCE_SPOT_TESTNET_ENDPOINTS,
    )
    WS_AVAILABLE = True
except ImportError:
    WS_AVAILABLE = False
    BinanceWebSocketClient = None
    BinanceEndpoints = None
    BINANCE_SPOT_TESTNET_ENDPOINTS = None

__all__ = [
    "JournalEntry",
    "TradeJournal",
    "PaperSessionConfig",
    "PaperSessionResult",
    "default_risk_manager",
    "run_paper_session",
    "run_paper_session_live",
    "PAPER_TRADING_NOTE",
]

ZERO = Decimal(0)

PAPER_TRADING_NOTE = (
    "Paper trading uses real market prices with simulated money. It "
    "cannot reproduce the fear of losing real money, and its fills are "
    "optimistic compared with a thin order book. A good paper result is "
    "permission to keep researching, never proof of future profit."
)


@dataclass
class JournalEntry:
    """One trade decision with everything needed to explain it later."""

    trade_number: int
    strategy_name: str
    signal: str
    decision_time: str
    reference_price: Decimal
    intended_quantity: Decimal
    risk_decision: str
    risk_reason: str
    fill_time: str = ""
    fill_price: Decimal | None = None
    slippage: Decimal = ZERO
    fee: Decimal = ZERO
    exit_time: str | None = None
    exit_price: Decimal | None = None
    pnl: Decimal | None = None
    reason: str = ""
    follow_up_note: str = ""

    @property
    def filled(self) -> bool:
        return self.fill_price is not None

    def to_dict(self) -> dict:
        return {
            "trade_number": self.trade_number,
            "strategy_name": self.strategy_name,
            "signal": self.signal,
            "decision_time": self.decision_time,
            "reference_price": str(self.reference_price),
            "intended_quantity": str(self.intended_quantity),
            "risk_decision": self.risk_decision,
            "risk_reason": self.risk_reason,
            "fill_time": self.fill_time,
            "fill_price": str(self.fill_price) if self.fill_price is not None else None,
            "slippage": str(self.slippage),
            "fee": str(self.fee),
            "exit_time": self.exit_time,
            "exit_price": str(self.exit_price) if self.exit_price is not None else None,
            "pnl": str(self.pnl) if self.pnl is not None else None,
            "reason": self.reason,
            "follow_up_note": self.follow_up_note,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "JournalEntry":
        def dec(value):
            return Decimal(value) if value is not None else None

        return cls(
            trade_number=int(data["trade_number"]),
            strategy_name=str(data["strategy_name"]),
            signal=str(data["signal"]),
            decision_time=str(data["decision_time"]),
            reference_price=Decimal(data["reference_price"]),
            intended_quantity=Decimal(data["intended_quantity"]),
            risk_decision=str(data["risk_decision"]),
            risk_reason=str(data["risk_reason"]),
            fill_time=str(data.get("fill_time", "")),
            fill_price=dec(data.get("fill_price")),
            slippage=Decimal(data.get("slippage", "0")),
            fee=Decimal(data.get("fee", "0")),
            exit_time=data.get("exit_time"),
            exit_price=dec(data.get("exit_price")),
            pnl=dec(data.get("pnl")),
            reason=str(data.get("reason", "")),
            follow_up_note=str(data.get("follow_up_note", "")),
        )


@dataclass
class TradeJournal:
    """Append-only record of every paper decision (analysis §13)."""

    entries: list[JournalEntry] = field(default_factory=list)
    dataset_id: str = ""
    strategy_name: str = ""

    def add(self, entry: JournalEntry) -> JournalEntry:
        self.entries.append(entry)
        return entry

    @property
    def filled_entries(self) -> list[JournalEntry]:
        return [entry for entry in self.entries if entry.filled]

    @property
    def rejected_entries(self) -> list[JournalEntry]:
        return [entry for entry in self.entries if entry.risk_decision == "reject"]

    def closed_trades(self) -> list[JournalEntry]:
        return [entry for entry in self.entries if entry.pnl is not None]

    def summary(self) -> dict[str, str]:
        closed = self.closed_trades()
        wins = [e for e in closed if (e.pnl or ZERO) > 0]
        losses = [e for e in closed if (e.pnl or ZERO) < 0]
        gross_win = sum((e.pnl or ZERO) for e in wins)
        gross_loss = sum((e.pnl or ZERO) for e in losses)
        return {
            "decisions": str(len(self.entries)),
            "filled": str(len(self.filled_entries)),
            "rejected_by_risk": str(len(self.rejected_entries)),
            "closed_trades": str(len(closed)),
            "wins": str(len(wins)),
            "losses": str(len(losses)),
            "gross_win": str(gross_win),
            "gross_loss": str(gross_loss),
        }

    def to_dict(self) -> dict:
        return {
            "dataset_id": self.dataset_id,
            "strategy_name": self.strategy_name,
            "entries": [entry.to_dict() for entry in self.entries],
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, ensure_ascii=False)

    def save(self, path: Path | str) -> Path:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(self.to_json(), encoding="utf-8")
        return target

    @classmethod
    def from_dict(cls, data: dict) -> "TradeJournal":
        journal = cls(
            dataset_id=str(data.get("dataset_id", "")),
            strategy_name=str(data.get("strategy_name", "")),
        )
        for item in data.get("entries", []):
            journal.entries.append(JournalEntry.from_dict(item))
        return journal

    @classmethod
    def load(cls, path: Path | str) -> "TradeJournal":
        return cls.from_dict(json.loads(Path(path).read_text(encoding="utf-8")))

    @staticmethod
    def render(journal: "TradeJournal") -> str:
        """Plain-text journal for the UI and the CLI."""
        lines = ["== Trading journal =="]
        lines.append(f"Dataset: {journal.dataset_id or 'unversioned'}")
        lines.append(f"Strategy: {journal.strategy_name or 'unknown'}")
        for entry in journal.entries:
            state = "FILLED" if entry.filled else entry.risk_decision.upper()
            lines.append("")
            lines.append(
                f"Trade #{entry.trade_number} [{state}] {entry.signal} "
                f"at {entry.decision_time}"
            )
            lines.append(f"  reference price: {entry.reference_price}")
            lines.append(f"  intended quantity: {entry.intended_quantity}")
            lines.append(
                f"  risk decision: {entry.risk_decision} — {entry.risk_reason}"
            )
            if entry.filled:
                lines.append(
                    f"  fill: {entry.fill_time} at {entry.fill_price} "
                    f"(slippage {entry.slippage}, fee {entry.fee})"
                )
            if entry.exit_price is not None:
                lines.append(
                    f"  exit: {entry.exit_time} at {entry.exit_price}"
                )
            if entry.pnl is not None:
                lines.append(f"  P/L: {entry.pnl}")
            if entry.reason:
                lines.append(f"  reason: {entry.reason}")
            if entry.follow_up_note:
                lines.append(f"  follow-up: {entry.follow_up_note}")
        return "\n".join(lines)


@dataclass(frozen=True)
class PaperSessionConfig:
    """Account, cost and sizing assumptions for one paper session."""

    initial_capital: Decimal = Decimal("10000")
    taker_fee: Decimal = Decimal("0.001")
    slippage_fraction: Decimal = Decimal("0.0005")
    spread_fraction: Decimal = Decimal("0.0002")
    position_fraction: Decimal = Decimal("0.5")
    interval: str = "1h"
    execution_config: ExecutionConfig | None = None
    #: Seed for the chapter-56 execution model. With an ``execution_config``
    #: set, the same seed must reproduce the same fills; without it the
    #: session is fully deterministic anyway.
    seed: int = 42

    def costs(self) -> CostModel:
        return CostModel(
            taker_fee=self.taker_fee,
            slippage_fraction=self.slippage_fraction,
            spread_fraction=self.spread_fraction,
        )

    def to_dict(self) -> dict:
        return {
            "initial_capital": str(self.initial_capital),
            "taker_fee": str(self.taker_fee),
            "slippage_fraction": str(self.slippage_fraction),
            "spread_fraction": str(self.spread_fraction),
            "position_fraction": str(self.position_fraction),
            "interval": self.interval,
            "execution_config": self.execution_config.__dict__ if self.execution_config else None,
            "seed": self.seed,
        }


@dataclass
class PaperSessionResult:
    """Everything a paper session produced (account + journal + curve)."""

    config: PaperSessionConfig
    symbol: str
    strategy_name: str
    dataset_id: str
    journal: TradeJournal
    equity_curve: tuple[Decimal, ...]
    final_equity: Decimal
    realized_pnl: Decimal
    total_fees: Decimal
    total_slippage: Decimal
    max_drawdown: Decimal
    open_position: Decimal
    note: str = PAPER_TRADING_NOTE

    @property
    def net_profit(self) -> Decimal:
        return self.final_equity - self.config.initial_capital

    def summary(self) -> str:
        stats = self.journal.summary()
        lines = [
            "== Paper trading account ==",
            f"Initial capital: {self.config.initial_capital}",
            f"Final equity: {self.final_equity}",
            f"Net profit/loss: {self.net_profit}",
            f"Realized P/L: {self.realized_pnl}",
            f"Open position: {self.open_position}",
            f"Maximum drawdown: {self.max_drawdown}",
            f"Fees paid: {self.total_fees}",
            f"Estimated slippage: {self.total_slippage}",
            "",
            "== Journal ==",
            f"Decisions: {stats['decisions']}",
            f"Filled: {stats['filled']}",
            f"Rejected by risk manager: {stats['rejected_by_risk']}",
            f"Closed trades: {stats['closed_trades']} "
            f"({stats['wins']} wins / {stats['losses']} losses)",
            "",
            self.note,
        ]
        return "\n".join(lines)


def default_risk_manager() -> RiskManager:
    """Conservative chapter-58 limits used when the caller passes none."""
    return RiskManager(
        limits=RiskLimits(
            max_risk_per_trade=Decimal("0.02"),
            max_position_size=Decimal("0.60"),
            max_total_exposure=Decimal("0.90"),
            max_long_exposure=Decimal("0.90"),
            max_short_exposure=Decimal("0"),
        ),
        loss_limits=LossLimits(
            max_daily_loss=Decimal("0.05"),
            max_weekly_loss=Decimal("0.10"),
            max_drawdown=Decimal("0.20"),
            max_consecutive_losses=5,
        ),
        operational_limits=OperationalLimits(
            max_trades_per_day=50,
            max_open_orders=10,
            max_order_frequency_per_minute=10,
        ),
    )


def _step_down(quantity: Decimal, step: Decimal = Decimal("0.000001")) -> Decimal:
    if step <= 0:
        return quantity
    return (quantity / step).to_integral_value(rounding="ROUND_DOWN") * step


def _adv_at(
    candles: Sequence[Candle],
    index: int,
    interval: str,
    window: int,
) -> Decimal:
    """Average daily volume proxy from the candles known at ``index``.

    The mean volume of the last ``window`` candles is scaled to a full day.
    It only looks backwards, so it cannot leak the fill candle's volume into
    the decision.
    """
    step = TIMEFRAMES.get(interval)
    if not step or window < 1:
        return ZERO
    start = max(0, index + 1 - window)
    sample = candles[start:index + 1]
    if not sample:
        return ZERO
    mean = sum((candle.volume for candle in sample), ZERO) / Decimal(len(sample))
    return mean * Decimal(86400) / Decimal(step)


def _reference_fill(
    config: PaperSessionConfig | LivePaperConfig,
    side: str,
    quantity: Decimal,
    reference: Decimal,
    adv: Decimal,
    rng: random.Random,
) -> tuple[Decimal, Decimal]:
    """Return ``(fill_price, filled_quantity)`` for one order.

    Without an ``execution_config`` this is the original chapter-57 model: a
    full fill at the next open, moved by the configured slippage and spread.
    With one, chapter 56 takes over — a synthetic order book, depth-based
    partial fills and a slippage model — driven by ``rng`` so the same
    session seed reproduces the same fills.
    """
    adjustment = config.slippage_fraction + config.spread_fraction
    if config.execution_config is None:
        if side == "buy":
            return reference * (Decimal(1) + adjustment), quantity
        return reference * (Decimal(1) - adjustment), quantity

    execution = simulate_market_order(
        reference,
        side,
        quantity,
        config.execution_config,
        adv=adv,
        spread_fraction=config.spread_fraction,
        rng=rng,
    )
    return execution.average_price, execution.filled_quantity


def _adv_window(config: PaperSessionConfig | LivePaperConfig) -> int:
    return config.execution_config.adv_window if config.execution_config else 20


def run_paper_session(
    candles: Sequence[Candle],
    strategy,
    *,
    config: PaperSessionConfig | None = None,
    risk_manager: RiskManager | None = None,
    dataset: DatasetVersion | None = None,
    symbol: str | None = None,
) -> PaperSessionResult:
    """Replay ``candles`` through ``strategy`` with simulated money.

    Every intended order is evaluated by the risk manager first; a
    rejection is recorded in the journal instead of being executed.
    Fills happen at the *next* candle's open (no look-ahead), with fees,
    spread and slippage applied.
    """
    if not candles:
        raise ValueError("paper trading needs at least one candle")
    config = config or PaperSessionConfig(interval=candles[0].interval)
    manager = risk_manager or default_risk_manager()
    market_symbol = symbol or str(candles[0].symbol)
    dataset_id = dataset.dataset_id if dataset else "unversioned"
    # Chapter 56's model draws latency and slippage; a seeded generator keeps
    # a session reproducible instead of depending on the global RNG.
    rng = random.Random(config.seed)

    cash = config.initial_capital
    position = ZERO
    fees = ZERO
    slippage_total = ZERO
    realized = ZERO
    entry_cost = ZERO  # cash spent on the open position
    entry_fee = ZERO

    journal = TradeJournal(dataset_id=dataset_id, strategy_name=strategy.name)
    equity_curve: list[Decimal] = []
    peak = config.initial_capital
    max_drawdown = ZERO
    trade_number = 0
    open_entry: JournalEntry | None = None
    consecutive_losses = 0
    daily_pnl = ZERO

    def mark_equity(price: Decimal) -> Decimal:
        return cash + position * price

    for index in range(len(candles) - 1):
        candle = candles[index]
        next_candle = candles[index + 1]
        price = candle.close
        equity = mark_equity(price)

        signal = strategy.on_candle(index, candles)

        if signal is OrderSide.BUY and position == 0:
            trade_number += 1
            reference = next_candle.open
            budget = equity * config.position_fraction
            quantity = _step_down(budget / reference)
            order = RiskOrderRequest(
                strategy_name=strategy.name,
                symbol=market_symbol,
                side="buy",
                quantity=quantity,
                price=reference,
                timestamp=candle.close_time.isoformat(),
            )
            risk_portfolio = PortfolioState(
                total_value=equity,
                long_exposure=position * price,
                short_exposure=ZERO,
                daily_pnl=daily_pnl,
                weekly_pnl=daily_pnl,
                current_drawdown=max_drawdown,
                consecutive_losses=consecutive_losses,
            )
            decision = manager.evaluate(order, risk_portfolio)
            entry = JournalEntry(
                trade_number=trade_number,
                strategy_name=strategy.name,
                signal="buy",
                decision_time=candle.close_time.isoformat(),
                reference_price=reference,
                intended_quantity=quantity,
                risk_decision=decision.decision.value,
                risk_reason=decision.reason,
                reason="entry",
            )
            if decision.decision is RiskDecision.APPROVE and quantity > 0:
                adv = _adv_at(candles, index, config.interval, _adv_window(config))
                fill_price, filled_quantity = _reference_fill(
                    config, "buy", quantity, next_candle.open, adv, rng
                )
                
                if filled_quantity > 0:
                    order_value = filled_quantity * fill_price
                    fee = order_value * config.taker_fee
                    cash -= order_value + fee
                    position += filled_quantity
                    fees += fee
                    slippage_total += filled_quantity * (fill_price - next_candle.open)
                    entry_cost = order_value
                    entry_fee = fee
                    entry.fill_time = next_candle.open_time.isoformat()
                    entry.fill_price = fill_price
                    entry.fee = fee
                    entry.slippage = filled_quantity * (fill_price - next_candle.open)
                    open_entry = entry
            journal.add(entry)

        elif signal is OrderSide.SELL and position > 0 and open_entry is not None:
            adv = _adv_at(candles, index, config.interval, _adv_window(config))
            fill_price, filled_quantity = _reference_fill(
                config, "sell", position, next_candle.open, adv, rng
            )
            filled_quantity = min(filled_quantity, position)
            if filled_quantity > 0:
                order_value = filled_quantity * fill_price
                fee = order_value * config.taker_fee
                cash += order_value - fee
                fees += fee
                slippage_total += filled_quantity * (next_candle.open - fill_price)
                # P/L is recognised only for the closed portion, so a partial
                # exit does not book the whole trade at once. On a full fill
                # ``share`` is exactly 1 and the arithmetic is unchanged.
                share = filled_quantity / position
                closed_cost = entry_cost * share
                closed_fee = entry_fee * share
                pnl = order_value - closed_cost - fee - closed_fee
                realized += pnl
                daily_pnl += pnl
                if pnl < 0:
                    consecutive_losses += 1
                else:
                    consecutive_losses = 0
                entry_cost -= closed_cost
                entry_fee -= closed_fee
                position -= filled_quantity
                if position == 0:
                    open_entry.exit_time = next_candle.open_time.isoformat()
                    open_entry.exit_price = fill_price
                    open_entry.pnl = pnl
                    open_entry.reason = "exit on strategy signal"
                    open_entry = None

        equity = mark_equity(candles[index + 1].close)
        peak = max(peak, equity)
        if peak > 0:
            drawdown = (peak - equity) / peak
            max_drawdown = max(max_drawdown, drawdown)
        equity_curve.append(equity)

    final_price = candles[-1].close
    final_equity = mark_equity(final_price)
    return PaperSessionResult(
        config=config,
        symbol=market_symbol,
        strategy_name=strategy.name,
        dataset_id=dataset_id,
        journal=journal,
        equity_curve=tuple(equity_curve),
        final_equity=final_equity,
        realized_pnl=realized,
        total_fees=fees,
        total_slippage=slippage_total,
        max_drawdown=max_drawdown,
        open_position=position,
    )


# ======================================================================
# Live WebSocket-based paper trading (ROADMAP.md chapter 26.2 / 57)
# ======================================================================

@dataclass(frozen=True)
class LivePaperConfig:
    """Configuration for live WebSocket paper trading."""
    endpoints: "BinanceEndpoints" = BINANCE_SPOT_TESTNET_ENDPOINTS
    api_key: str = ""
    api_secret: str = ""
    symbol: str = "BTC/USDT"
    interval: str = "1m"
    max_candles: int = 500
    # Session limits
    max_runtime_seconds: int = 3600  # 1 hour default
    stop_on_disconnect: bool = True
    # Paper trading config (mirrors PaperSessionConfig)
    initial_capital: Decimal = Decimal("10000")
    taker_fee: Decimal = Decimal("0.001")
    slippage_fraction: Decimal = Decimal("0.0005")
    spread_fraction: Decimal = Decimal("0.0002")
    position_fraction: Decimal = Decimal("0.5")
    #: Same chapter-56 execution model and seed as the replay session.
    execution_config: ExecutionConfig | None = None
    seed: int = 42


async def run_paper_session_live(
    strategy,
    config: LivePaperConfig,
    risk_manager: RiskManager | None = None,
    *,
    websocket_factory=None,
    client=None,
) -> PaperSessionResult:
    """Run paper trading against a live Binance WebSocket feed (26.2, 57).

    The session subscribes to the kline stream for one symbol and interval,
    and every **closed** candle is pushed through the same risk gate, the same
    chapter-56 execution model and the same journal as the replay session.
    It runs for at most ``config.max_runtime_seconds`` and then returns, so
    a caller never has to kill it.

    Differences from the replay session, stated because they matter:

    * the fill reference is the closed candle's own close, not the next
      candle's open — in a live feed the next open does not exist yet, and
      waiting for it would mean acting on a candle that has already passed;
    * partial data is possible: a session that receives no closed candle
      returns an empty equity curve rather than a fabricated one;
    * the journal is returned, not written to disk. The caller decides where
      it belongs (the CLI and the UI know their data directory; this function
      does not).

    ``websocket_factory`` lets tests drive a scripted feed instead of the
    network. It is the same seam the client itself exposes. ``client``
    replaces the feed client entirely, for tests that need to control its
    state.
    """
    if not WS_AVAILABLE:
        raise RuntimeError(
            "The WebSocket client is not available. Install the optional "
            "'websockets' package (pip install websockets)."
        )
    if config.endpoints is None:
        raise ValueError("endpoints must be provided")
    if config.max_runtime_seconds <= 0:
        raise ValueError("max_runtime_seconds must be positive")

    manager = risk_manager or default_risk_manager()
    market_symbol = config.symbol
    dataset_id = f"live_{config.symbol}_{config.interval}"
    rng = random.Random(config.seed)

    # The result must describe the session the caller asked for, not a
    # default one: net_profit is computed from this config's capital.
    session_config = PaperSessionConfig(
        initial_capital=config.initial_capital,
        taker_fee=config.taker_fee,
        slippage_fraction=config.slippage_fraction,
        spread_fraction=config.spread_fraction,
        position_fraction=config.position_fraction,
        interval=config.interval,
        execution_config=config.execution_config,
        seed=config.seed,
    )

    cash = config.initial_capital
    position = ZERO
    fees = ZERO
    slippage_total = ZERO
    realized = ZERO
    entry_cost = ZERO
    entry_fee = ZERO

    journal = TradeJournal(dataset_id=dataset_id, strategy_name=strategy.name)
    equity_curve: list[Decimal] = []
    peak = config.initial_capital
    max_drawdown = ZERO
    trade_number = 0
    open_entry: JournalEntry | None = None
    consecutive_losses = 0
    daily_pnl = ZERO

    completed_candles: list[Candle] = []
    feed_warnings: list[str] = []
    stale_candles = 0

    ws_client = client or BinanceWebSocketClient(
        config.endpoints,
        websocket_factory,
    )

    def mark_equity(price: Decimal) -> Decimal:
        return cash + position * price

    def process_closed_candle(candle: Candle) -> None:
        """Decide and fill on one completed candle (runs in arrival order)."""
        nonlocal cash, position, fees, slippage_total, realized, entry_cost
        nonlocal entry_fee, peak, max_drawdown, trade_number, open_entry
        nonlocal consecutive_losses, daily_pnl, stale_candles

        if ws_client.state is ConnectionState.DEGRADED:
            # Chapter 27: never generate a signal from stale data. The
            # candle is still buffered so the strategy keeps its history,
            # but no order is evaluated and no fill can happen.
            stale_candles += 1
            completed_candles.append(candle)
            if len(completed_candles) > config.max_candles:
                completed_candles.pop(0)
            return

        completed_candles.append(candle)
        if len(completed_candles) > config.max_candles:
            completed_candles.pop(0)

        signal = strategy.on_candle(len(completed_candles) - 1, completed_candles)
        reference = candle.close
        equity = mark_equity(reference)

        if equity > peak:
            peak = equity
        if peak > 0:
            max_drawdown = max(max_drawdown, (peak - equity) / peak)
        equity_curve.append(equity)

        if signal is OrderSide.BUY and position == 0:
            trade_number += 1
            budget = equity * config.position_fraction
            quantity = _step_down(budget / reference)
            order = RiskOrderRequest(
                strategy_name=strategy.name,
                symbol=str(market_symbol),
                side="buy",
                quantity=quantity,
                price=reference,
                timestamp=candle.close_time.isoformat(),
            )
            risk_portfolio = PortfolioState(
                total_value=equity,
                long_exposure=position * reference,
                short_exposure=ZERO,
                daily_pnl=daily_pnl,
                weekly_pnl=daily_pnl,
                current_drawdown=max_drawdown,
                consecutive_losses=consecutive_losses,
            )
            decision = manager.evaluate(order, risk_portfolio)
            entry = JournalEntry(
                trade_number=trade_number,
                strategy_name=strategy.name,
                signal="buy",
                decision_time=candle.close_time.isoformat(),
                reference_price=reference,
                intended_quantity=quantity,
                risk_decision=decision.decision.value,
                risk_reason=decision.reason,
                reason="entry",
            )
            if decision.decision is RiskDecision.APPROVE and quantity > 0:
                adv = _adv_at(
                    completed_candles,
                    len(completed_candles) - 1,
                    config.interval,
                    _adv_window(config),
                )
                fill_price, filled_quantity = _reference_fill(
                    config, "buy", quantity, reference, adv, rng
                )
                if filled_quantity > 0:
                    order_value = filled_quantity * fill_price
                    fee = order_value * config.taker_fee
                    cash -= order_value + fee
                    position += filled_quantity
                    fees += fee
                    slippage_total += filled_quantity * (fill_price - reference)
                    entry_cost = order_value
                    entry_fee = fee
                    entry.fill_time = candle.close_time.isoformat()
                    entry.fill_price = fill_price
                    entry.fee = fee
                    entry.slippage = filled_quantity * (fill_price - reference)
                    open_entry = entry
            journal.add(entry)

        elif signal is OrderSide.SELL and position > 0:
            trade_number += 1
            quantity = position
            order = RiskOrderRequest(
                strategy_name=strategy.name,
                symbol=str(market_symbol),
                side="sell",
                quantity=quantity,
                price=reference,
                timestamp=candle.close_time.isoformat(),
            )
            risk_portfolio = PortfolioState(
                total_value=equity,
                long_exposure=position * reference,
                short_exposure=ZERO,
                daily_pnl=daily_pnl,
                weekly_pnl=daily_pnl,
                current_drawdown=max_drawdown,
                consecutive_losses=consecutive_losses,
            )
            decision = manager.evaluate(order, risk_portfolio)
            entry = JournalEntry(
                trade_number=trade_number,
                strategy_name=strategy.name,
                signal="sell",
                decision_time=candle.close_time.isoformat(),
                reference_price=reference,
                intended_quantity=quantity,
                risk_decision=decision.decision.value,
                risk_reason=decision.reason,
                reason="exit",
            )
            if decision.decision is RiskDecision.APPROVE and quantity > 0:
                adv = _adv_at(
                    completed_candles,
                    len(completed_candles) - 1,
                    config.interval,
                    _adv_window(config),
                )
                fill_price, filled_quantity = _reference_fill(
                    config, "sell", quantity, reference, adv, rng
                )
                if filled_quantity > 0:
                    order_value = filled_quantity * fill_price
                    fee = order_value * config.taker_fee
                    share = filled_quantity / position
                    closed_cost = entry_cost * share
                    closed_fee = entry_fee * share
                    pnl = order_value - closed_cost - fee - closed_fee
                    realized += pnl
                    cash += order_value - fee
                    fees += fee
                    slippage_total += filled_quantity * (reference - fill_price)
                    daily_pnl += pnl
                    consecutive_losses = (
                        consecutive_losses + 1 if pnl < 0 else 0
                    )
                    entry_cost -= closed_cost
                    entry_fee -= closed_fee
                    position -= filled_quantity
                    entry.fill_time = candle.close_time.isoformat()
                    entry.fill_price = fill_price
                    entry.fee = fee
                    entry.slippage = filled_quantity * (reference - fill_price)
                    if position == 0 and open_entry is not None:
                        open_entry.exit_time = candle.close_time.isoformat()
                        open_entry.exit_price = fill_price
                        open_entry.pnl = pnl
                        open_entry = None
            journal.add(entry)

    def handle_kline(payload: dict) -> None:
        """Turn a Binance kline payload into one completed candle."""
        kline = payload.get("k") or {}
        if not kline.get("x", False):
            return  # still forming
        try:
            candle = Candle(
                symbol=Symbol(config.symbol),
                interval=config.interval,
                open_time=datetime.fromtimestamp(
                    kline["t"] / 1000, tz=timezone.utc
                ),
                close_time=datetime.fromtimestamp(
                    kline["T"] / 1000, tz=timezone.utc
                ),
                open=Decimal(kline["o"]),
                high=Decimal(kline["h"]),
                low=Decimal(kline["l"]),
                close=Decimal(kline["c"]),
                volume=Decimal(kline["v"]),
            )
        except (KeyError, TypeError, ValueError, InvalidOperation):
            logging.getLogger(__name__).warning(
                "Ignoring a malformed kline payload"
            )
            return
        process_closed_candle(candle)

    ws_client.add_candle_handler(handle_kline)
    ws_client.add_warning_callback(
        lambda state, message: feed_warnings.append(f"{state}: {message}")
    )
    ws_client.subscribe(
        f"{config.symbol.replace('/', '').lower()}@kline_{config.interval}"
    )

    await ws_client.start()
    try:
        await asyncio.wait_for(
            ws_client.wait_stopped(), timeout=config.max_runtime_seconds
        )
    except asyncio.TimeoutError:
        pass
    finally:
        await ws_client.stop()

    final_price = completed_candles[-1].close if completed_candles else ZERO
    final_equity = mark_equity(final_price) if completed_candles else cash

    note_lines = [PAPER_TRADING_NOTE]
    if not completed_candles:
        note_lines.append(
            "The feed produced no closed candle during this session, so there "
            "is nothing to report: an empty session is not a flat one."
        )
    health = ws_client.get_health_metrics()
    note_lines.append(
        f"Feed: {health['state']} after {health['message_count']} messages, "
        f"{health['reconnect_attempts']} reconnect attempts."
    )
    if stale_candles:
        note_lines.append(
            f"{stale_candles} candle(s) arrived while the feed was degraded "
            "and were buffered without generating any signal (chapter 27)."
        )
    if feed_warnings:
        note_lines.append("Feed warnings:")
        note_lines.extend(f"  {warning}" for warning in feed_warnings[-5:])

    return PaperSessionResult(
        config=session_config,
        symbol=str(market_symbol),
        strategy_name=strategy.name,
        dataset_id=dataset_id,
        journal=journal,
        equity_curve=tuple(equity_curve),
        final_equity=final_equity,
        realized_pnl=realized,
        total_fees=fees,
        total_slippage=slippage_total,
        max_drawdown=max_drawdown,
        open_position=position,
        note="\n".join(note_lines),
    )

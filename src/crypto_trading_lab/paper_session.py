"""Paper trading over real market data, with a mandatory risk gate and a
trading journal (ROADMAP.md chapter 57, analysis §10, §11, §13).

This is a *replay* engine: it walks real candles in chronological order,
lets a strategy decide at each close, passes every intended order through
the chapter-58 risk manager, fills at the next candle's open with fees,
spread and slippage, and writes a journal entry for every decision —
approved or rejected.

It never touches an exchange and never uses real money. A continuous
WebSocket feed is still pending (chapter 26.2); today the "real data" is
a dataset downloaded from the exchange and replayed candle by candle.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path
from typing import Sequence

from crypto_trading_lab.backtesting.engine import CostModel
from crypto_trading_lab.domain.models import Candle, OrderSide
from crypto_trading_lab.execution_realism import ExecutionConfig, simulate_execution
from crypto_trading_lab.market_data.historical import DatasetVersion
from crypto_trading_lab.risk_manager import (
    LossLimits,
    OperationalLimits,
    OrderRequest as RiskOrderRequest,
    PortfolioState,
    RiskDecision,
    RiskLimits,
    RiskManager,
)

__all__ = [
    "JournalEntry",
    "TradeJournal",
    "PaperSessionConfig",
    "PaperSessionResult",
    "default_risk_manager",
    "run_paper_session",
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
                # Use realistic execution model if configured
                if config.execution_config:
                    # Simple market impact model: price moves against order
                    # Impact is proportional to order size relative to ADV
                    impact_factor = config.execution_config.impact_factor
                    # Approximate ADV from recent volume (simple proxy)
                    avg_volume = Decimal("1000000")  # placeholder
                    impact_pct = (quantity / avg_volume) * impact_factor
                    price_impact = next_candle.open * impact_pct
                    
                    fill_price = (
                        next_candle.open
                        * (Decimal(1) + config.slippage_fraction + config.spread_fraction)
                        + price_impact
                    )
                    # Partial fill simulation: up to 10% chance of partial fill
                    import random
                    if random.random() < 0.1:
                        filled_quantity = quantity * Decimal("0.8")  # 80% filled
                    else:
                        filled_quantity = quantity
                else:
                    # Basic execution model (backward compatible)
                    fill_price = (
                        next_candle.open
                        * (Decimal(1) + config.slippage_fraction + config.spread_fraction)
                    )
                    filled_quantity = quantity
                
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
            fill_price = (
                next_candle.open
                * (Decimal(1) - config.slippage_fraction - config.spread_fraction)
            )
            order_value = position * fill_price
            fee = order_value * config.taker_fee
            cash += order_value - fee
            fees += fee
            slippage_total += position * (next_candle.open - fill_price)
            pnl = order_value - entry_cost - fee - entry_fee
            realized += pnl
            daily_pnl += pnl
            if pnl < 0:
                consecutive_losses += 1
            else:
                consecutive_losses = 0
            position = ZERO
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

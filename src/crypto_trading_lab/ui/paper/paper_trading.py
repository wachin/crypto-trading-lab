"""Paper-trading screen (ROADMAP.md chapter 57, analysis §10, §13).

Replays a stored dataset through a strategy with simulated money, a
mandatory risk gate and a full trading journal. It is explicit about
what it is *not*: there is no continuous live feed yet (chapter 26.2 is
pending), so the "real data" is a downloaded dataset replayed candle by
candle.
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Sequence

from PyQt6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSplitter,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)
from PyQt6.QtCore import Qt

from crypto_trading_lab.backtesting.engine import (
    BuyAndHoldStrategy,
    MACrossoverStrategy,
    NullStrategy,
)
from crypto_trading_lab.domain.models import Candle
from crypto_trading_lab.market_data.historical import DatasetVersion
from crypto_trading_lab.paper_session import (
    PAPER_TRADING_NOTE,
    PaperSessionResult,
    TradeJournal,
    run_paper_session,
)

STRATEGY_SMA = "sma_crossover"
STRATEGY_BUY_HOLD = "buy_and_hold"
STRATEGY_NULL = "null"


class PaperTradingWidget(QWidget):
    """The paper-trading account, its controls and its journal."""

    def __init__(
        self,
        candles: Sequence[Candle] | None = None,
        dataset: DatasetVersion | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._candles = list(candles or [])
        self._dataset = dataset
        self._last: PaperSessionResult | None = None

        self.setWindowTitle(self.tr("Paper Trading"))
        layout = QVBoxLayout(self)

        header = QLabel(self.tr("Paper trading: real prices, fake money"))
        font = header.font()
        font.setBold(True)
        font.setPointSize(15)
        header.setFont(font)
        layout.addWidget(header)

        self.dataset_label = QLabel(self._dataset_text())
        self.dataset_label.setWordWrap(True)
        layout.addWidget(self.dataset_label)

        form = QFormLayout()
        self.strategy_combo = QComboBox()
        self.strategy_combo.addItem(self.tr("SMA crossover"), STRATEGY_SMA)
        self.strategy_combo.addItem(self.tr("Buy and hold"), STRATEGY_BUY_HOLD)
        self.strategy_combo.addItem(self.tr("Null (never trades)"), STRATEGY_NULL)
        form.addRow(self.tr("Strategy:"), self.strategy_combo)

        self.capital_edit = QLineEdit("10000")
        form.addRow(self.tr("Simulated capital:"), self.capital_edit)

        self.position_edit = QLineEdit("0.5")
        form.addRow(self.tr("Fraction of capital per trade:"), self.position_edit)

        self.fee_edit = QLineEdit("0.001")
        self.slippage_edit = QLineEdit("0.0005")
        self.spread_edit = QLineEdit("0.0002")
        costs = QWidget()
        costs_layout = QHBoxLayout(costs)
        costs_layout.setContentsMargins(0, 0, 0, 0)
        costs_layout.addWidget(self.fee_edit)
        costs_layout.addWidget(self.slippage_edit)
        costs_layout.addWidget(self.spread_edit)
        form.addRow(self.tr("Fee / slippage / spread:"), costs)

        self.fast_spin_edit = QLineEdit("10")
        self.slow_spin_edit = QLineEdit("30")
        sma = QWidget()
        sma_layout = QHBoxLayout(sma)
        sma_layout.setContentsMargins(0, 0, 0, 0)
        sma_layout.addWidget(self.fast_spin_edit)
        sma_layout.addWidget(self.slow_spin_edit)
        form.addRow(self.tr("SMA fast / slow:"), sma)
        layout.addLayout(form)

        buttons = QHBoxLayout()
        self.run_button = QPushButton(self.tr("Run paper session"))
        self.run_button.clicked.connect(self.run_session)
        self.save_button = QPushButton(self.tr("Save journal…"))
        self.save_button.setEnabled(False)
        self.save_button.clicked.connect(self.save_journal)
        buttons.addWidget(self.run_button)
        buttons.addWidget(self.save_button)
        layout.addLayout(buttons)

        self.status_label = QLabel("")
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

        splitter = QSplitter(Qt.Orientation.Vertical)
        self.account_view = QTextBrowser()
        self.account_view.setPlainText(self.tr(PAPER_TRADING_NOTE))
        self.journal_view = QTextBrowser()
        splitter.addWidget(self.account_view)
        splitter.addWidget(self.journal_view)
        layout.addWidget(splitter)

        # Post-trade follow-up view (chapter 79)
        followup_group = QGroupBox(self.tr("Post-Trade Follow-Up"))
        followup_layout = QVBoxLayout(followup_group)
        self.trade_selector = QComboBox()
        self.trade_selector.setEnabled(False)
        self.trade_selector.currentIndexChanged.connect(self._on_trade_selected)
        followup_layout.addWidget(self.trade_selector)
        self.followup_view = QTextBrowser()
        self.followup_view.setPlainText(self.tr(
            "Select a closed trade to see what the strategy knew at the time."
        ))
        followup_layout.addWidget(self.followup_view)
        self.followup_edit = QLineEdit()
        self.followup_edit.setPlaceholderText(
            self.tr("Add a follow-up note for this trade…")
        )
        followup_layout.addWidget(self.followup_edit)
        self.followup_save_button = QPushButton(self.tr("Save follow-up note"))
        self.followup_save_button.clicked.connect(self._save_follow_up)
        self.followup_save_button.setEnabled(False)
        followup_layout.addWidget(self.followup_save_button)
        layout.addWidget(followup_group)

    # -- helpers ----------------------------------------------------------

    def _dataset_text(self) -> str:
        if self._dataset is None:
            return self.tr(
                "Dataset: none. Download historical data first; paper "
                "trading needs real candles to replay."
            )
        return self.tr(
            "Dataset: {id} · {count} candles · strategy decisions are "
            "filled at the next candle's open."
        ).format(id=self._dataset.dataset_id, count=self._dataset.candle_count)

    def set_data(
        self, candles: Sequence[Candle], dataset: DatasetVersion | None
    ) -> None:
        self._candles = list(candles)
        self._dataset = dataset
        self.dataset_label.setText(self._dataset_text())

    def _strategy(self):
        kind = self.strategy_combo.currentData()
        if kind == STRATEGY_BUY_HOLD:
            return BuyAndHoldStrategy()
        if kind == STRATEGY_NULL:
            return NullStrategy()
        fast = int(self.fast_spin_edit.text().strip() or "10")
        slow = int(self.slow_spin_edit.text().strip() or "30")
        return MACrossoverStrategy(fast=fast, slow=slow)

    # -- work -------------------------------------------------------------

    def run_session(self) -> PaperSessionResult | None:
        """Run the replay and render account + journal; returns the result."""
        if not self._candles:
            self.status_label.setText(
                self.tr("No candles available: download historical data first.")
            )
            return None
        try:
            capital = Decimal(self.capital_edit.text().strip())
            position_fraction = Decimal(self.position_edit.text().strip())
            fee = Decimal(self.fee_edit.text().strip() or "0")
            slippage = Decimal(self.slippage_edit.text().strip() or "0")
            spread = Decimal(self.spread_edit.text().strip() or "0")
            if capital <= 0 or not (0 < position_fraction <= 1):
                raise ValueError
        except (InvalidOperation, ValueError):
            self.status_label.setText(
                self.tr(
                    "Capital must be positive and the position fraction "
                    "must be between 0 and 1 (for example 10000 and 0.5)."
                )
            )
            return None

        from crypto_trading_lab.paper_session import PaperSessionConfig

        config = PaperSessionConfig(
            initial_capital=capital,
            taker_fee=fee,
            slippage_fraction=slippage,
            spread_fraction=spread,
            position_fraction=position_fraction,
            interval=self._candles[0].interval,
        )
        try:
            strategy = self._strategy()
        except ValueError as error:
            self.status_label.setText(str(error))
            return None

        result = run_paper_session(
            self._candles,
            strategy,
            config=config,
            dataset=self._dataset,
        )
        self._last = result
        self.save_button.setEnabled(True)
        self.account_view.setPlainText(result.summary())
        self.journal_view.setPlainText(TradeJournal.render(result.journal))
        self.status_label.setText(
            self.tr("Session complete: {trades} closed trades.").format(
                trades=len(result.journal.closed_trades())
            )
        )
        self._update_trade_selector()
        return result

    def save_journal(self) -> str | None:
        """Persist the last journal and return the path."""
        if self._last is None:
            return None
        path, _ = QFileDialog.getSaveFileName(
            self, self.tr("Save trading journal"), "trading_journal.json",
            self.tr("JSON (*.json)"),
        )
        if not path:
            return None
        self._last.journal.save(path)
        return path

    @property
    def last_result(self) -> PaperSessionResult | None:
        return self._last

    # -- follow-up -------------------------------------------------------

    def _on_trade_selected(self) -> None:
        idx = self.trade_selector.currentData()
        if self._last is None or idx is None:
            return
        entry = self._last.journal.entries[idx]
        text = self.tr(
            "Trade #{number} — {signal}\n"
            "Decision time: {time}\n"
            "Reference price: {ref}\n"
            "Risk decision: {risk} — {reason}\n"
            "Fill: {fill_time} at {fill_price}\n"
            "Exit: {exit_time} at {exit_price}\n"
            "P/L: {pnl}"
        ).format(
            number=entry.trade_number,
            signal=entry.signal,
            time=entry.decision_time,
            ref=entry.reference_price,
            risk=entry.risk_decision,
            reason=entry.risk_reason,
            fill_time=entry.fill_time or "—",
            fill_price=entry.fill_price or "—",
            exit_time=entry.exit_time or "—",
            exit_price=entry.exit_price or "—",
            pnl=entry.pnl if entry.pnl is not None else "—",
        )
        self.followup_view.setPlainText(text)
        self.followup_edit.setText(entry.follow_up_note)
        self.followup_save_button.setEnabled(True)

    def _save_follow_up(self) -> None:
        idx = self.trade_selector.currentData()
        if self._last is None or idx is None:
            return
        note = self.followup_edit.text().strip()
        self._last.journal.entries[idx].follow_up_note = note
        self.status_label.setText(
            self.tr("Follow-up note saved for trade #{number}.").format(
                number=self._last.journal.entries[idx].trade_number
            )
        )

    def _update_trade_selector(self) -> None:
        self.trade_selector.clear()
        if self._last is None:
            self.trade_selector.setEnabled(False)
            return
        closed = self._last.journal.closed_trades()
        if not closed:
            self.trade_selector.setEnabled(False)
            return
        for entry in closed:
            self.trade_selector.addItem(
                self.tr("Trade #{number}: {signal} — P/L {pnl}").format(
                    number=entry.trade_number,
                    signal=entry.signal,
                    pnl=entry.pnl if entry.pnl is not None else "—",
                ),
                closed.index(entry),
            )
        self.trade_selector.setEnabled(True)


__all__ = ["PaperTradingWidget"]

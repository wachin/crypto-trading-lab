"""Research Wizard (analysis §15, chapters 37-45 and 66).

A guided path from a hypothesis to a recorded, honestly-labelled
result. The wizard does not *prevent* research; it refuses to skip a
step silently, and explains why each step exists.
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Sequence

from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from crypto_trading_lab.backtesting.engine import (
    BacktestConfig,
    BuyAndHoldStrategy,
    CostModel,
    MACrossoverStrategy,
)
from crypto_trading_lab.backtesting.walk_forward import WalkForwardConfig
from crypto_trading_lab.domain.models import Candle
from crypto_trading_lab.machine_learning.experiment_manager import (
    ExperimentManager,
)
from crypto_trading_lab.market_data.historical import DatasetVersion
from crypto_trading_lab.research import ResearchRun, run_research
from crypto_trading_lab.ui.research.validity import ValidityDashboard

STRATEGY_SMA = "sma_crossover"
STRATEGY_BUY_HOLD = "buy_and_hold"

#: Minimum candles for a walk-forward window to fit meaningfully.
MIN_CANDLES_FOR_WALK_FORWARD = 300


class ResearchWizardDialog(QDialog):
    """Step-by-step research dialog over one dataset."""

    def __init__(
        self,
        candles: Sequence[Candle],
        dataset: DatasetVersion | None,
        manager: ExperimentManager,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._candles = list(candles)
        self._dataset = dataset
        self._manager = manager
        self._last_run: ResearchRun | None = None

        self.setWindowTitle(self.tr("New research"))
        self.resize(860, 720)

        layout = QVBoxLayout(self)

        header = QLabel(self.tr("New research: from hypothesis to verdict"))
        font = header.font()
        font.setBold(True)
        font.setPointSize(14)
        header.setFont(font)
        layout.addWidget(header)

        self.dataset_label = QLabel(self._dataset_summary())
        self.dataset_label.setWordWrap(True)
        layout.addWidget(self.dataset_label)

        form = QFormLayout()

        self.hypothesis_edit = QLineEdit()
        self.hypothesis_edit.setPlaceholderText(
            self.tr(
                "Example: when price is above EMA200 and RSI crosses 50 "
                "upwards, a statistical advantage may exist"
            )
        )
        form.addRow(self.tr("1. Hypothesis:"), self.hypothesis_edit)

        self.strategy_combo = QComboBox()
        self.strategy_combo.addItem(
            self.tr("SMA crossover"), STRATEGY_SMA
        )
        self.strategy_combo.addItem(
            self.tr("Buy and hold (passive)"), STRATEGY_BUY_HOLD
        )
        form.addRow(self.tr("2. Strategy:"), self.strategy_combo)

        self.fast_spin = QSpinBox()
        self.fast_spin.setRange(2, 500)
        self.fast_spin.setValue(10)
        self.slow_spin = QSpinBox()
        self.slow_spin.setRange(3, 1000)
        self.slow_spin.setValue(30)
        params = QWidget()
        params_layout = QHBoxLayout(params)
        params_layout.setContentsMargins(0, 0, 0, 0)
        params_layout.addWidget(self.fast_spin)
        params_layout.addWidget(self.slow_spin)
        form.addRow(self.tr("3. SMA fast / slow:"), params)

        self.capital_edit = QLineEdit("10000")
        form.addRow(self.tr("4. Initial capital:"), self.capital_edit)

        self.fee_edit = QLineEdit("0.001")
        self.slippage_edit = QLineEdit("0.0005")
        self.spread_edit = QLineEdit("0.0002")
        costs = QWidget()
        costs_layout = QHBoxLayout(costs)
        costs_layout.setContentsMargins(0, 0, 0, 0)
        costs_layout.addWidget(self.fee_edit)
        costs_layout.addWidget(self.slippage_edit)
        costs_layout.addWidget(self.spread_edit)
        form.addRow(self.tr("5. Fee / slippage / spread:"), costs)

        self.benchmark_check = QCheckBox(
            self.tr("6. Compare against buy and hold")
        )
        self.benchmark_check.setChecked(True)
        form.addRow(self.tr("Benchmark:"), self.benchmark_check)

        self.robustness_check = QCheckBox(
            self.tr("7. Attempt to refute it (Monte Carlo, costs, OOS)")
        )
        self.robustness_check.setChecked(True)
        form.addRow(self.tr("Robustness:"), self.robustness_check)

        self.walk_forward_check = QCheckBox(
            self.tr("8. Walk-forward analysis")
        )
        self.walk_forward_check.setChecked(
            len(self._candles) >= MIN_CANDLES_FOR_WALK_FORWARD
        )
        self.walk_forward_check.setEnabled(
            len(self._candles) >= MIN_CANDLES_FOR_WALK_FORWARD
        )
        form.addRow(self.tr("Walk-forward:"), self.walk_forward_check)

        self.trials_spin = QSpinBox()
        self.trials_spin.setRange(1, 100000)
        self.trials_spin.setValue(1)
        self.trials_spin.setToolTip(
            self.tr(
                "How many configurations have you tried for this idea? "
                "The more you try, the more likely the best one is luck."
            )
        )
        form.addRow(self.tr("9. Configurations tried so far:"), self.trials_spin)

        layout.addLayout(form)

        buttons = QDialogButtonBox()
        self.run_button = buttons.addButton(
            self.tr("Run research"), QDialogButtonBox.ButtonRole.AcceptRole
        )
        self.close_button = buttons.addButton(
            self.tr("Close"), QDialogButtonBox.ButtonRole.RejectRole
        )
        self.run_button.clicked.connect(self.run)
        self.close_button.clicked.connect(self.reject)
        layout.addWidget(buttons)

        self.results = ValidityDashboard()
        layout.addWidget(self.results)

        if dataset is None or not candles:
            self.run_button.setEnabled(False)
            self.results.view.setPlainText(
                self.tr(
                    "There is no versioned dataset yet. Open “Get "
                    "historical data” first: without a named dataset a "
                    "result cannot be reproduced, so the laboratory "
                    "will not pretend to validate one."
                )
            )

    # -- inputs ----------------------------------------------------------

    def _dataset_summary(self) -> str:
        if self._dataset is None:
            return self.tr(
                "Dataset: none. Download historical data first."
            )
        return self.tr(
            "Dataset: {id} · {count} candles · checksum {checksum}…"
        ).format(
            id=self._dataset.dataset_id,
            count=self._dataset.candle_count,
            checksum=self._dataset.checksum[:12],
        )

    def _cost_model(self) -> CostModel:
        def number(text: str) -> Decimal:
            return Decimal(text.strip() or "0")

        return CostModel(
            taker_fee=number(self.fee_edit.text()),
            slippage_fraction=number(self.slippage_edit.text()),
            spread_fraction=number(self.spread_edit.text()),
        )

    def build_config(self) -> BacktestConfig:
        return BacktestConfig(
            initial_capital=Decimal(self.capital_edit.text().strip()),
            costs=self._cost_model(),
        )

    def _strategy_factory(self):
        if self.strategy_combo.currentData() == STRATEGY_BUY_HOLD:
            return lambda: BuyAndHoldStrategy()
        fast = self.fast_spin.value()
        slow = self.slow_spin.value()
        return lambda: MACrossoverStrategy(fast=fast, slow=slow)

    # -- work ------------------------------------------------------------

    def run(self) -> ResearchRun | None:
        """Execute the research and render it; returns the run."""
        hypothesis = self.hypothesis_edit.text().strip()
        if not hypothesis:
            self.results.view.setPlainText(
                self.tr(
                    "Write the hypothesis first. A research question "
                    "you cannot state is a question you cannot test."
                )
            )
            return None
        if self._dataset is None:
            self.results.view.setPlainText(
                self.tr("Download a dataset before running research.")
            )
            return None
        if self.strategy_combo.currentData() == STRATEGY_SMA and (
            self.fast_spin.value() >= self.slow_spin.value()
        ):
            self.results.view.setPlainText(
                self.tr(
                    "The fast SMA period must be smaller than the slow "
                    "one (for example 10 and 30)."
                )
            )
            return None
        try:
            config = self.build_config()
        except (InvalidOperation, ValueError):
            self.results.view.setPlainText(
                self.tr(
                    "Capital and costs must be numbers, for example "
                    "10000, 0.001, 0.0005, 0.0002."
                )
            )
            return None

        walk_forward_config = None
        if self.walk_forward_check.isChecked():
            n = len(self._candles)
            walk_forward_config = WalkForwardConfig(
                train_size=max(60, n // 4),
                test_size=max(20, n // 8),
                step=max(20, n // 8),
                warmup=max(0, self.slow_spin.value()),
            )

        run = run_research(
            self._candles,
            hypothesis=hypothesis,
            strategy_factory=self._strategy_factory(),
            strategy_name=self.strategy_combo.currentData(),
            parameters={
                "fast": str(self.fast_spin.value()),
                "slow": str(self.slow_spin.value()),
            },
            config=config,
            dataset=self._dataset,
            benchmark_factory=(
                (lambda: BuyAndHoldStrategy())
                if self.benchmark_check.isChecked()
                else None
            ),
            run_robustness=self.robustness_check.isChecked(),
            run_walk_forward_analysis=walk_forward_config is not None,
            walk_forward_config=walk_forward_config,
            trials=self.trials_spin.value(),
            manager=self._manager,
        )
        self._last_run = run
        self.results.set_run(run)
        return run

    @property
    def last_run(self) -> ResearchRun | None:
        return self._last_run


__all__ = ["ResearchWizardDialog", "MIN_CANDLES_FOR_WALK_FORWARD"]

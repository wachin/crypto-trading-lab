"""Backtesting Lab window (ROADMAP.md chapters 37.9, 37.10 and 40).

Runs the chapter 37 engine over imported candles and shows every
result with the chapter 40 metrics, the statistical-validity warnings
and the mandatory beginner-oriented explanation. A profitable backtest
is never presented as proof that a strategy will be profitable.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Sequence

from PyQt6.QtWidgets import (
    QComboBox,
    QLabel,
    QFormLayout,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from crypto_trading_lab.backtesting.engine import (
    BacktestConfig,
    BuyAndHoldStrategy,
    MACrossoverStrategy,
    NullStrategy,
    run_backtest,
)

from crypto_trading_lab.optimization import (
    run_optimization,
    OBJECTIVE_SHARPE_RATIO,
    OptimizationConfig,
    ParameterRange,
)

from crypto_trading_lab.complexity_control import (
    analyze_strategy_complexity,
    COMPLEXITY_CONTROL_WARNING,
)

from crypto_trading_lab.backtesting.metrics import (
    DISCLAIMER,
    compare_reports,
    compute_performance,
)
from crypto_trading_lab.domain.models import Candle

STRATEGY_SMA = "sma_crossover"
STRATEGY_BUY_HOLD = "buy_and_hold"
STRATEGY_NULL = "null"


class BacktestingLabWidget(QWidget):
    """Run a backtest over loaded candles and show honest results."""

    def __init__(
        self,
        candles: Sequence[Candle],
        symbol: str = "BTC/USDT",
        interval: str = "1m",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._candles = list(candles)
        self._symbol = symbol
        self._interval = interval

        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.strategy_combo = QComboBox()
        self.strategy_combo.addItem(
            self.tr("SMA crossover"), STRATEGY_SMA
        )
        self.strategy_combo.addItem(
            self.tr("Buy and hold"), STRATEGY_BUY_HOLD
        )
        self.strategy_combo.addItem(
            self.tr("Null (never trades)"), STRATEGY_NULL
        )
        form.addRow(self.tr("Strategy:"), self.strategy_combo)

        parameters = QHBoxLayout()
        self.fast_spin = QSpinBox()
        self.fast_spin.setRange(2, 500)
        self.fast_spin.setValue(10)
        self.slow_spin = QSpinBox()
        self.slow_spin.setRange(3, 1000)
        self.slow_spin.setValue(30)
        parameters.addWidget(self.fast_spin)
        parameters.addWidget(self.slow_spin)
        form.addRow(self.tr("SMA fast / slow:"), parameters)

        self.capital_edit = QLineEdit("10000")
        form.addRow(self.tr("Initial capital:"), self.capital_edit)

        # Chapter 42.1: benchmark selection must be visible and changeable.
        self.benchmark_combo = QComboBox()
        self.benchmark_combo.addItem(
            self.tr("Buy and hold (default)"), STRATEGY_BUY_HOLD
        )
        self.benchmark_combo.addItem(
            self.tr("Null (never trades)"), STRATEGY_NULL
        )
        self.benchmark_combo.addItem(self.tr("None"), None)
        form.addRow(self.tr("Benchmark:"), self.benchmark_combo)
        layout.addLayout(form)

        self.run_button = QPushButton(self.tr("Run backtest"))
        self.run_button.clicked.connect(self.run_and_display)
        layout.addWidget(self.run_button)

        self.save_button = QPushButton(self.tr("Save report (HTML/CSV/JSON)"))
        self.save_button.setEnabled(False)
        self.save_button.clicked.connect(self._save_dialog)
        layout.addWidget(self.save_button)
        self._last_export: tuple | None = None  # (result, report, warning)

        self.results_view = QTextBrowser()
        self.results_view.setPlainText(
            self.tr(
                "Choose a strategy and press “Run backtest”. Every "
                "result is shown with its risks, costs and statistical "
                "warnings."
            )
        )
        layout.addWidget(self.results_view)

    # -- the actual work (kept side-effect free for tests) ---------------

    def run_and_display(self) -> str:
        """Run the selected backtest, render results, return the text.

        Returns the rendered text so tests can assert on it; on invalid
        input an explanation is shown and returned instead.
        """
        try:
            capital = Decimal(self.capital_edit.text().strip())
            if capital <= 0:
                raise ValueError
        except Exception:
            message = self.tr(
                "Initial capital must be a positive number, "
                "for example 10000."
            )
            self.results_view.setPlainText(message)
            return message

        kind = self.strategy_combo.currentData()
        if kind == STRATEGY_SMA:
            fast, slow = self.fast_spin.value(), self.slow_spin.value()
            if fast >= slow:
                message = self.tr(
                    "The fast SMA period must be smaller than the slow "
                    "one (for example 10 and 30)."
                )
                self.results_view.setPlainText(message)
                return message
            strategy = MACrossoverStrategy(fast=fast, slow=slow)
        elif kind == STRATEGY_BUY_HOLD:
            strategy = BuyAndHoldStrategy()
        else:
            strategy = NullStrategy()

        config = BacktestConfig(initial_capital=capital)
        result = run_backtest(self._candles, strategy, config)

        benchmark_kind = self.benchmark_combo.currentData()
        benchmark_warning: str | None = None
        benchmark_result = None
        benchmark_report = None
        if benchmark_kind is not None:
            benchmark_strategy = (
                BuyAndHoldStrategy()
                if benchmark_kind == STRATEGY_BUY_HOLD
                else NullStrategy()
            )
            benchmark_result = run_backtest(
                self._candles, benchmark_strategy, config
            )
            benchmark_report = compute_performance(benchmark_result)
            if benchmark_kind == kind:
                benchmark_warning = self.tr(
                    "The chosen benchmark is the same strategy you are "
                    "testing: the excess return is 0 by construction. "
                    "Pick a different benchmark for a meaningful "
                    "comparison."
                )
        report = compute_performance(result, benchmark=benchmark_result)

        self._last_export = (result, report, benchmark_warning)
        self.save_button.setEnabled(True)
        text = self._render(result, report, benchmark_warning,
                            benchmark_report)
        self.results_view.setPlainText(text)
        return text

    # -- report export (chapter 41) --------------------------------------

    def save_report(self, base_path: str) -> list[str]:
        """Write the last run as ``.html``, ``.csv`` and ``.json``.

        Returns the written file paths; empty list when nothing has
        been run yet.
        """
        if self._last_export is None:
            return []
        from crypto_trading_lab.reporting.report import (
            build_backtest_report,
            render_csv,
            render_html,
            render_json,
        )

        result, performance = self._last_export[0], self._last_export[1]
        data = build_backtest_report(
            result, performance, self._symbol, self._interval
        )
        written: list[str] = []
        for suffix, render in (
            (".html", render_html),
            (".csv", render_csv),
            (".json", render_json),
        ):
            path = base_path + suffix
            with open(path, "w", encoding="utf-8") as handle:
                handle.write(render(data))
            written.append(path)
        return written

    def _save_dialog(self) -> None:
        from PyQt6.QtWidgets import QFileDialog, QMessageBox

        base, _filter = QFileDialog.getSaveFileName(
            self,
            self.tr("Save report"),
            "backtest_report",
            self.tr("Report base name (*)"),
        )
        if not base:
            return
        for suffix in (".html", ".csv", ".json"):
            if base.endswith(suffix):
                base = base[: -len(suffix)]
        written = self.save_report(base)
        QMessageBox.information(
            self,
            self.tr("Report"),
            self.tr("Saved: {files}").format(files=", ".join(written)),
        )

    def _render(self, result, report, benchmark_warning: str | None = None,
                benchmark_report=None) -> str:
        """Plain-language result report (chapters 37.9, 37.10, 40.8)."""
        r, s, risk, a = report.returns, report.trades, report.risk, report.activity
        lines = [
            self.tr("== What was tested =="),
            self.tr("Strategy: {name} (version {version})").format(
                name=result.strategy_name, version=result.strategy_version
            ),
            self.tr("Asset and timeframe: {symbol}, {interval} candles").format(
                symbol=self._symbol, interval=self._interval
            ),
            self.tr("Historical period: {period} ({n} candles)").format(
                period=result.dataset_period, n=result.candle_count
            ),
            self.tr("Dataset version: {version}").format(
                version=result.dataset_version
            ),
            self.tr("Execution model: {model} (signals at a candle's close "
              "fill at the NEXT candle's open — no look-ahead)").format(
                model=result.config_metadata.get("execution_model")
            ),
            self.tr("Assumptions: long-only spot; every order fills "
              "completely at the modeled price (no rejections, no "
              "partial fills); taker fee {fee}, slippage {slip}, "
              "spread {spread} per trade.").format(
                fee=result.config_metadata.get("taker_fee"),
                slip=result.config_metadata.get("slippage_fraction"),
                spread=result.config_metadata.get("spread_fraction"),
            ),
            "",
            self.tr("== Money (all costs included) =="),
            self.tr("Initial capital: {x}").format(x=r.initial_capital),
            self.tr("Final equity: {x}").format(x=r.final_equity),
            self.tr("Net profit/loss: {x}").format(x=r.net_profit),
            self.tr("Total return: {x}").format(x=r.total_return),
            self.tr("Annualized return: {x}").format(
                x=self._fmt(r.annualized_return, r.annualized_is_valid)
            ),
            "",
            self.tr("== Trades =="),
            self.tr("Number of trades: {x}").format(x=s.number_of_trades),
            self.tr("Win rate: {x}").format(x=self._fmt(s.win_rate)),
            self.tr("Average winning trade: {x}").format(
                x=self._fmt(s.average_winning_trade)
            ),
            self.tr("Average losing trade: {x}").format(
                x=self._fmt(s.average_losing_trade)
            ),
            self.tr("Profit factor: {x}").format(x=self._fmt(s.profit_factor)),
            "",
            self.tr("== Risk =="),
            self.tr("Maximum drawdown: {x} (worst drop from a previous "
              "peak)").format(x=risk.max_drawdown),
            self.tr("Maximum drawdown duration: {x} candles").format(
                x=risk.max_drawdown_duration
            ),
            self.tr("Sharpe ratio: {x}").format(
                x=self._fmt(risk.sharpe_ratio, risk.sharpe_is_valid)
            ),
            self.tr("Sortino ratio: {x}").format(
                x=self._fmt(risk.sortino_ratio, risk.sortino_is_valid)
            ),
            self.tr("Market exposure: {x} of candles in the market").format(
                x=risk.market_exposure
            ),
            "",
            self.tr("== Costs and benchmark =="),
            self.tr("Commissions and fees: {x}").format(x=a.trading_fees),
            self.tr("Estimated slippage: {x}").format(x=a.slippage_cost),
            self.tr("Estimated spread cost: {x}").format(x=a.spread_cost),
            self.tr("Benchmark ({name}) return: {x}").format(
                name=report.benchmark.benchmark_name
                if report.benchmark
                else self.tr("none"),
                x=report.benchmark.benchmark_return
                if report.benchmark
                else "n/a",
            ),
            self.tr("Excess return vs benchmark: {x}").format(
                x=report.benchmark.excess_return
                if report.benchmark
                else "n/a"
            ),
            "",
        ]
        lines.extend(self._comparison_lines(report, benchmark_report))
        lines.append(self.tr("== Warnings =="))
        if benchmark_warning:
            lines.append(f"  • {benchmark_warning}")
        lines.extend(f"  • {w}" for w in report.warnings)
        if not report.warnings:
            lines.append(self.tr("  (none)"))
        lines += [
            "",
            self.tr("== Please read before trusting this =="),
            self.tr(
                "• This test used IN-SAMPLE historical data only; the "
                "strategy may simply have memorized the past."
            ),
            self.tr(
                "• Commissions and fees are what exchanges charge per "
                "trade; spread and slippage are the extra cost of "
                "buying a bit too high and selling a bit too low."
            ),
            self.tr(
                "• Liquidity matters: real orders move the price, so "
                "real fills can be worse than simulated ones."
            ),
            self.tr(
                "• Historical results can be misleading: markets "
                "change, and a past pattern may never repeat."
            ),
            self.tr(
                "• A profitable backtest is NOT proof of future "
                "profitability, and real trading results often differ "
                "from simulations."
            ),
            "",
            DISCLAIMER,
        ]
        return "\n".join(lines)

    def _comparison_lines(self, report, benchmark_report) -> list[str]:
        """Relative benchmark comparison (chapter 42.2)."""
        if report.benchmark is None or benchmark_report is None:
            return [
                self.tr("== Benchmark comparison =="),
                self.tr(
                    "  No benchmark selected — absolute performance "
                    "alone cannot tell you whether the strategy added "
                    "value over doing nothing."
                ),
                "",
            ]
        view = compare_reports(
            report, benchmark_report, report.benchmark.benchmark_name
        )
        lines = [
            self.tr("== Benchmark comparison (vs {name}) ==").format(
                name=view.benchmark_name
            ),
            self.tr("  Excess return (net of costs): {x}").format(
                x=view.excess_return
            ),
            self.tr("  Excess return (before costs): {x}").format(
                x=view.gross_excess_return
            ),
            self.tr("  Cost drag on the comparison: {x}").format(
                x=view.cost_drag
            ),
            self.tr("  Volatility difference: {x}").format(
                x=self._fmt(view.volatility_difference)
            ),
            self.tr("  Max drawdown difference: {x}").format(
                x=self._fmt(view.max_drawdown_difference)
            ),
            self.tr("  Sharpe difference: {x}").format(
                x=self._fmt(view.sharpe_difference)
            ),
        ]
        # Plain-language verdict (chapter 42.2, 40.8).
        if view.beats_benchmark:
            lines.append(
                self.tr(
                    "  The strategy beat the passive alternative by "
                    "{x} after costs — described, not proven."
                ).format(x=view.excess_return)
            )
        else:
            lines.append(
                self.tr(
                    "  The strategy did NOT beat the passive "
                    "alternative after costs ({x}). The honest "
                    "conclusion: this configuration added nothing over "
                    "doing the simple thing."
                ).format(x=view.excess_return)
            )
        lines.append("")
        return lines

    def _fmt(self, value, valid: bool = True) -> str:
        if value is None:
            return self.tr("n/a (insufficient data)")
        if isinstance(value, Decimal):
            text = f"{value:.6f}"
        else:
            text = str(value)
        if not valid:
            text += self.tr("  (descriptive only, not statistically "
                            "supported)")
        return text

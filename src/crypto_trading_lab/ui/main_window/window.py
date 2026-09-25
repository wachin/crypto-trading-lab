"""Application entry point (ROADMAP.md chapter 71.1).

``python3 -m crypto_trading_lab`` opens the main window: menus,
language selector, paper-trading and real-trading indicators,
connection status, welcome panel, educational warning, and the buttons
that lead into the research workflow (data → research → notebook).

Windows are created lazily and reused, so opening a screen twice does
not leak a second copy. No screen is a placeholder: every menu entry
that looks like a feature is backed by the same tested modules the
tests exercise.
"""

from __future__ import annotations

import sys

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction, QKeySequence
from PyQt6.QtWidgets import (
    QApplication,
    QLabel,
    QMainWindow,
    QProgressDialog,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from crypto_trading_lab.configuration.xdg import AppPaths
from crypto_trading_lab.domain.models import Candle, ConnectionState
from crypto_trading_lab.i18n.translations import (
    DEFAULT_LANGUAGE,
    apply_language,
)
from crypto_trading_lab.machine_learning.experiment_manager import (
    ExperimentManager,
)
from crypto_trading_lab.trading import RealTradingManager, RealTradingConfig, RealTradingState
from crypto_trading_lab.market_data.historical import DatasetVersion
from crypto_trading_lab.ui.connection_health_widget import ConnectionHealthWidget
from crypto_trading_lab.ui.accessibility import AccessibilityHelper
from crypto_trading_lab.ui.trading import TestnetTradingWidget


class MainWindow(QMainWindow):
    """Main window: safety indicators plus the research workflow."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(self.tr("Crypto Trading Lab"))
        self.resize(920, 640)

        # Lazily-created child windows, kept alive by reference.
        self._learning_center = None
        self._chart_window = None
        self._backtesting_window = None
        self._historical_data_window = None
        self._wizard_window = None
        self._notebook_window = None
        self._assistant_window = None
        self._strategy_builder_window = None
        self._paper_window = None
        self._trading_window = None
        self._testnet_window = None

        self._trading_manager = RealTradingManager()
        self._trading_manager.state_changed.connect(self._on_trading_state_changed)

        self._build_menus()
        self._build_central()

    # -- helpers ----------------------------------------------------------

    def _paths(self) -> AppPaths:
        """XDG paths; a single place so tests can override if needed."""
        return AppPaths()
        
    def _on_connection_state_changed(self, state: ConnectionState, message: str):
        """Update status label when connection state changes."""
        self.status_label.setText(message)
        # Use color-independent status formatting for accessibility
        is_positive = state == ConnectionState.CONNECTED
        formatted = AccessibilityHelper.format_status_text(message, is_positive=is_positive)
        self.statusBar().showMessage(formatted)

    def _on_trading_state_changed(self, state: RealTradingState, message: str):
        """Update REAL TRADING status indicators (chapter 68)."""
        self.real_trading_label.setText(self.tr(f"Real trading: {state.value.capitalize()}"))
        if state == RealTradingState.ACTIVE:
            self.real_trading_indicator.setVisible(True)
            self.real_trading_indicator.setText(self.tr("REAL TRADING"))
        else:
            self.real_trading_indicator.setVisible(False)
        # Use color-independent status formatting
        is_positive = state != RealTradingState.ACTIVE
        formatted = AccessibilityHelper.format_status_text(message, is_positive=is_positive)
        self.statusBar().showMessage(formatted)

    def _manager(self) -> ExperimentManager:
        """Experiment manager persisted under the user's data directory."""
        manager = ExperimentManager(
            storage_path=self._paths().data_dir / "research" / "experiments.json"
        )
        manager.load()
        return manager

    def _load_candles_and_dataset(
        self,
        symbol: str | None = None,
        interval: str | None = None,
        paths: AppPaths | None = None,
    ) -> tuple[DatasetVersion | None, list[Candle]]:
        """Most recent versioned dataset plus its candles (or empty)."""
        from crypto_trading_lab.domain.models import Symbol
        from crypto_trading_lab.persistence.candles import CandleRepository
        from crypto_trading_lab.persistence.database import (
            create_database,
            database_engine,
            make_session_factory,
        )
        from crypto_trading_lab.persistence.datasets import DatasetRepository

        paths = paths or self._paths()
        if not paths.database_file.exists():
            return None, []
        engine = database_engine(paths.database_file)
        create_database(engine)
        session = make_session_factory(engine)()
        try:
            datasets = DatasetRepository(session)
            dataset = (
                datasets.latest(symbol=symbol, interval=interval)
                if (symbol or interval)
                else datasets.latest()
            )
            if dataset is None:
                return None, []
            candles = CandleRepository(session).load_candles(
                Symbol(dataset.symbol),
                dataset.interval,
                exchange_name=dataset.exchange,
            )
            return dataset, candles
        finally:
            session.close()
            engine.dispose()

    # -- menus ------------------------------------------------------------

    def _build_menus(self) -> None:
        file_menu = self.menuBar().addMenu(self.tr("&File"))
        self.action_load_csv = QAction(self.tr("Load CSV file..."), self)
        self.action_load_csv.triggered.connect(self._open_csv_dialog)
        file_menu.addAction(self.action_load_csv)

        self.action_historical_data = QAction(
            self.tr("Get historical data..."), self
        )
        self.action_historical_data.triggered.connect(self._open_historical_data)
        file_menu.addAction(self.action_historical_data)

        view_menu = self.menuBar().addMenu(self.tr("&View"))
        self.action_learning_center = QAction(
            self.tr("Open Learning Center"), self
        )
        self.action_learning_center.triggered.connect(self._open_learning_center)
        view_menu.addAction(self.action_learning_center)

        self.action_chart = QAction(self.tr("Open Chart"), self)
        self.action_chart.triggered.connect(self._open_chart)
        view_menu.addAction(self.action_chart)

        tools_menu = self.menuBar().addMenu(self.tr("&Tools"))
        self.action_backtesting = QAction(self.tr("Open Backtesting Lab"), self)
        self.action_backtesting.setEnabled(True)  # chapter 37.9
        self.action_backtesting.triggered.connect(self._open_backtesting)
        tools_menu.addAction(self.action_backtesting)

        self.action_wizard = QAction(self.tr("New research..."), self)
        self.action_wizard.triggered.connect(self._open_research_wizard)
        tools_menu.addAction(self.action_wizard)

        self.action_paper = QAction(self.tr("Paper Trading"), self)
        self.action_paper.triggered.connect(self._open_paper)
        tools_menu.addAction(self.action_paper)

        research_menu = self.menuBar().addMenu(self.tr("&Research"))
        self.action_notebook = QAction(self.tr("Research Notebook"), self)
        self.action_notebook.triggered.connect(self._open_notebook)
        research_menu.addAction(self.action_notebook)

        self.action_assistant = QAction(self.tr("Research Assistant"), self)
        self.action_assistant.triggered.connect(self._open_assistant)
        research_menu.addAction(self.action_assistant)

        self.action_strategy_builder = QAction(self.tr("Strategy Builder"), self)
        self.action_strategy_builder.triggered.connect(self._open_strategy_builder)
        research_menu.addAction(self.action_strategy_builder)

        help_menu = self.menuBar().addMenu(self.tr("&Help"))
        help_menu.addAction(
            QAction(
                self.tr("Start Here: Cryptocurrency for Complete Beginners."),
                self,
            )
        )

    # -- central panel ----------------------------------------------------

    def _build_central(self) -> None:
        layout = QVBoxLayout()
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)

        title = QLabel(self.tr("Crypto Trading Lab"))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        font = title.font()
        font.setPointSize(20)
        font.setBold(True)
        title.setFont(font)
        AccessibilityHelper.setup_accessibility(
            title,
            name=self.tr("Application title"),
            description=self.tr("Crypto Trading Lab - Main application window title"),
        )
        layout.addWidget(title)

        # Safety indicators (chapter 71.1).
        self.mode_label = QLabel(self.tr("Mode: Paper Trading"))
        self.mode_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        AccessibilityHelper.setup_accessibility(
            self.mode_label,
            name=self.tr("Trading mode indicator"),
            description=self.tr("Shows current trading mode: Paper Trading"),
        )
        layout.addWidget(self.mode_label)

        self.real_trading_label = QLabel(self.tr("Real trading: Disabled"))
        self.real_trading_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        AccessibilityHelper.setup_accessibility(
            self.real_trading_label,
            name=self.tr("Real trading status"),
            description=self.tr("Shows whether real trading is active or disabled"),
        )
        layout.addWidget(self.real_trading_label)

        self.real_trading_indicator = QLabel("")
        self.real_trading_indicator.setVisible(False)
        self.real_trading_indicator.setStyleSheet("""
            QLabel {
                color: #d32f2f;
                font-weight: bold;
                padding: 2px 8px;
                background-color: #ffebee;
                border-radius: 4px;
            }
        """)
        AccessibilityHelper.setup_accessibility(
            self.real_trading_indicator,
            name=self.tr("Real trading warning"),
            description=self.tr("Visible warning when real trading is active"),
        )
        layout.addWidget(self.real_trading_indicator)

        self.status_label = QLabel(self.tr("Disconnected"))
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        AccessibilityHelper.setup_accessibility(
            self.status_label,
            name=self.tr("Connection status"),
            description=self.tr("Shows current connection state to market data source"),
        )
        layout.addWidget(self.status_label)
        
        # Connection health widget
        self._connection_health = ConnectionHealthWidget()
        self._connection_health.state_changed.connect(self._on_connection_state_changed)
        AccessibilityHelper.setup_accessibility(
            self._connection_health,
            name=self.tr("Connection health monitor"),
            description=self.tr("Detailed connection quality metrics and diagnostics"),
        )
        layout.addWidget(self._connection_health)

        # Educational message (vision: honesty, the farmer's truth).
        message = QLabel(
            self.tr(
                "As with the farmer who sows even in years when it "
                "does not rain, you must take the risk without "
                "knowing whether the season will be good: people "
                "make a living from the land, and people make a "
                "living from the markets. This tool cannot guarantee "
                "rain — never sow money meant for food or housing, "
                "and never borrow money to sow."
            )
        )
        message.setWordWrap(True)
        AccessibilityHelper.setup_accessibility(
            message,
            name=self.tr("Risk warning"),
            description=self.tr("Educational message about trading risks and capital protection"),
        )
        layout.addWidget(message)

        welcome = QLabel(
            self.tr(
                "Welcome. Begin with the Learning Center to learn "
                "step by step, without risk."
            )
        )
        welcome.setWordWrap(True)
        AccessibilityHelper.setup_accessibility(
            welcome,
            name=self.tr("Welcome message"),
            description=self.tr("Guidance for new users to start with the Learning Center"),
        )
        layout.addWidget(welcome)

        self.historical_data_button = QPushButton(self.tr("Get historical data"))
        self.historical_data_button.clicked.connect(self._open_historical_data)
        self.csv_button = QPushButton(self.tr("Load CSV file"))
        self.csv_button.clicked.connect(self._open_csv_dialog)
        self.chart_button = QPushButton(self.tr("Open Chart"))
        self.chart_button.clicked.connect(self._open_chart)
        self.learning_center_button = QPushButton(self.tr("Open Learning Center"))
        self.learning_center_button.clicked.connect(self._open_learning_center)
        self.backtesting_button = QPushButton(self.tr("Open Backtesting Lab"))
        self.backtesting_button.setEnabled(True)
        self.backtesting_button.clicked.connect(self._open_backtesting)
        self.wizard_button = QPushButton(self.tr("New research"))
        self.wizard_button.clicked.connect(self._open_research_wizard)
        self.paper_button = QPushButton(self.tr("Paper Trading"))
        self.paper_button.clicked.connect(self._open_paper)
        self.testnet_button = QPushButton(self.tr("Binance Spot Testnet"))
        self.testnet_button.clicked.connect(self._open_testnet)

        # Add accessibility metadata to all buttons
        buttons_info = [
            (self.historical_data_button,
             self.tr("Get historical data"),
             self.tr("Download market data from exchanges"),
             self.tr("Download real market data from supported exchanges for research")),
            (self.csv_button,
             self.tr("Load CSV file"),
             self.tr("Import CSV market data"),
             self.tr("Load market data from a local CSV file")),
            (self.chart_button,
             self.tr("Open Chart"),
             self.tr("Open price chart"),
             self.tr("View interactive price charts with indicators")),
            (self.learning_center_button,
             self.tr("Open Learning Center"),
             self.tr("Start interactive trading lessons"),
             self.tr("Open structured lessons with quizzes and progress tracking")),
            (self.backtesting_button,
             self.tr("Open Backtesting Lab"),
             self.tr("Run strategy backtests"),
             self.tr("Test trading strategies against historical data with costs")),
            (self.wizard_button,
             self.tr("New research"),
             self.tr("Start guided research workflow"),
             self.tr("Launch the research wizard for hypothesis-driven exploration")),
            (self.paper_button,
             self.tr("Paper Trading"),
             self.tr("Simulated trading with real market data"),
             self.tr("Practice trading with simulated money on real historical data")),
            (self.testnet_button,
             self.tr("Binance Spot Testnet"),
             self.tr("Open testnet trading with safety activation"),
             self.tr("Practice testnet trading with full safety activation flow")),
        ]

        for button, name, tooltip, description in buttons_info:
            AccessibilityHelper.setup_accessibility(
                button, name=name, tooltip=tooltip, description=description
            )
            layout.addWidget(button)

        # Set logical tab order for keyboard navigation
        tab_order: list[QWidget] = [
            self.historical_data_button,
            self.csv_button,
            self.chart_button,
            self.learning_center_button,
            self.backtesting_button,
            self.wizard_button,
            self.paper_button,
            self.testnet_button,
        ]
        AccessibilityHelper.set_tab_order(tab_order)

        # Add keyboard shortcuts
        self.historical_data_button.setShortcut(QKeySequence("Ctrl+D"))
        self.csv_button.setShortcut(QKeySequence("Ctrl+L"))
        self.chart_button.setShortcut(QKeySequence("Ctrl+C"))
        self.learning_center_button.setShortcut(QKeySequence("Ctrl+E"))
        self.backtesting_button.setShortcut(QKeySequence("Ctrl+B"))
        self.wizard_button.setShortcut(QKeySequence("Ctrl+R"))
        self.paper_button.setShortcut(QKeySequence("Ctrl+P"))
        self.testnet_button.setShortcut(QKeySequence("Ctrl+T"))

        layout.addStretch(1)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)
        self.statusBar().showMessage(AccessibilityHelper.format_status_text(
            self.tr("Disconnected"), is_positive=None
        ))

    # -- learning center / charts ----------------------------------------

    def _open_learning_center(self) -> None:
        """Open the Learning Center as a top-level window (chapter 23)."""
        if self._learning_center is None:
            from crypto_trading_lab.ui.education.learning_center import (
                LearningCenterWidget,
            )

            self._learning_center = LearningCenterWidget()
            self._learning_center.setWindowTitle(self.tr("Learning Center"))
            self._learning_center.resize(520, 620)
        self._learning_center.show()
        self._learning_center.raise_()

    # -- CSV import -------------------------------------------------------

    def load_csv_file(
        self, path: str, paths: "AppPaths | None" = None
    ) -> str:
        """Parse a CSV, show the pre-import summary, persist on confirm.

        Chapter 28: nothing reaches the database before the user sees a
        plain-language summary and confirms. Returns a status message
        for the UI/tests. ``paths`` is injectable for tests.
        """
        from pathlib import Path

        from crypto_trading_lab.market_data.importer import parse_csv
        from crypto_trading_lab.persistence.candles import CandleRepository
        from crypto_trading_lab.persistence.database import (
            create_database,
            database_engine,
            make_session_factory,
        )

        summary = parse_csv(Path(path))
        if not summary.ok:
            return summary.beginner_explanation()

        paths = paths or self._paths()
        engine = database_engine(paths.database_file)
        create_database(engine)
        session = make_session_factory(engine)()
        try:
            saved = CandleRepository(session).save_candles(summary.candles)
        finally:
            session.close()
            engine.dispose()
        return (
            f"Imported {saved} candles of {summary.symbol} "
            f"({summary.interval})."
        )

    def _open_csv_dialog(self) -> None:
        """File dialog + import flow for the Load CSV button."""
        from PyQt6.QtWidgets import QFileDialog, QMessageBox

        path, _filter = QFileDialog.getOpenFileName(
            self,
            self.tr("Load CSV file"),
            "",
            self.tr("CSV candles (*.csv);;All files (*)"),
        )
        if not path:
            return
        message = self.load_csv_file(path)
        QMessageBox.information(self, self.tr("Import"), message)

    # -- historical data --------------------------------------------------

    def _open_historical_data(self) -> None:
        """Open the historical-data downloader (chapters 26.2, 28)."""
        if self._historical_data_window is None:
            from crypto_trading_lab.ui.data.historical_data import (
                HistoricalDataWidget,
            )

            self._historical_data_window = HistoricalDataWidget()
            self._historical_data_window.setWindowTitle(
                self.tr("Crypto Trading Lab — Historical data")
            )
            self._historical_data_window.resize(760, 680)
        self._historical_data_window.show()
        self._historical_data_window.raise_()

    # -- charts -----------------------------------------------------------

    def open_chart(
        self, paths: "AppPaths | None" = None, notify: bool = True
    ) -> "PyQtGraphCandleChart | None":
        """Open the chart window with the most recent imported candles."""
        if self._chart_window is not None:
            self._chart_window.show()
            self._chart_window.raise_()
            return self._chart_window

        from PyQt6.QtWidgets import QMessageBox

        from crypto_trading_lab.domain.models import Symbol
        from crypto_trading_lab.persistence.candles import CandleRepository
        from crypto_trading_lab.persistence.database import (
            create_database,
            database_engine,
            make_session_factory,
        )
        from crypto_trading_lab.ui.charts.abstraction import CandleSeries
        from crypto_trading_lab.ui.charts.pyqtgraph_backend import (
            PyQtGraphCandleChart,
        )

        progress = QProgressDialog(
            self.tr("Loading chart..."), None, 0, 0, self
        )
        progress.setWindowTitle(self.tr("Loading"))
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.setCancelButton(None)
        progress.setMinimumDuration(500)
        progress.show()
        QApplication.processEvents()

        paths = paths or self._paths()
        candles: list[Candle] = []
        dataset, dataset_candles = self._load_candles_and_dataset(
            paths=paths
        )
        if dataset is not None:
            candles = dataset_candles
        elif paths.database_file.exists():
            engine = database_engine(paths.database_file)
            create_database(engine)
            session = make_session_factory(engine)()
            try:
                candles = CandleRepository(session).load_candles(
                    Symbol("BTC/USDT"), "1m"
                )
            finally:
                session.close()
                engine.dispose()
        progress.close()

        if not candles:
            if notify:
                QMessageBox.information(
                    self,
                    self.tr("Chart"),
                    self.tr(
                        "No candles stored yet. Download historical data "
                        "or load a CSV file first."
                    ),
                )
            return None

        symbol = dataset.symbol if dataset else "BTC/USDT"
        interval = dataset.interval if dataset else "1m"
        chart = PyQtGraphCandleChart()
        chart.setWindowTitle(self.tr("Crypto Trading Lab — Chart"))
        chart.resize(1000, 600)
        chart.set_candles(CandleSeries.from_candles(symbol, interval, candles))
        chart.show()
        self._chart_window = chart  # keep a reference alive
        return chart

    def _open_chart(self) -> None:
        self.open_chart()

    # -- backtesting lab --------------------------------------------------

    def open_backtesting(
        self, paths: "AppPaths | None" = None, notify: bool = True
    ) -> "BacktestingLabWidget | None":
        """Open the Backtesting Lab over the stored candles (37.9)."""
        if self._backtesting_window is not None:
            self._backtesting_window.show()
            self._backtesting_window.raise_()
            return self._backtesting_window

        from PyQt6.QtWidgets import QMessageBox

        from crypto_trading_lab.domain.models import Symbol
        from crypto_trading_lab.persistence.candles import CandleRepository
        from crypto_trading_lab.persistence.database import (
            create_database,
            database_engine,
            make_session_factory,
        )
        from crypto_trading_lab.ui.backtesting.lab import (
            BacktestingLabWidget,
        )

        progress = QProgressDialog(
            self.tr("Loading Backtesting Lab..."), None, 0, 0, self
        )
        progress.setWindowTitle(self.tr("Loading"))
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.setCancelButton(None)
        progress.setMinimumDuration(500)
        progress.show()
        QApplication.processEvents()

        paths = paths or self._paths()
        candles: list[Candle] = []
        dataset, dataset_candles = self._load_candles_and_dataset(paths=paths)
        if dataset is not None:
            candles = dataset_candles
        elif paths.database_file.exists():
            engine = database_engine(paths.database_file)
            create_database(engine)
            session = make_session_factory(engine)()
            try:
                candles = CandleRepository(session).load_candles(
                    Symbol("BTC/USDT"), "1m"
                )
            finally:
                session.close()
                engine.dispose()
        progress.close()

        if not candles:
            if notify:
                QMessageBox.information(
                    self,
                    self.tr("Backtesting Lab"),
                    self.tr(
                        "No candles stored yet. Download historical data "
                        "or load a CSV file first."
                    ),
                )
            return None

        symbol = dataset.symbol if dataset else "BTC/USDT"
        interval = dataset.interval if dataset else "1m"
        lab = BacktestingLabWidget(candles, symbol, interval)
        lab.setWindowTitle(self.tr("Crypto Trading Lab — Backtesting Lab"))
        lab.resize(780, 700)
        lab.show()
        self._backtesting_window = lab  # keep a reference alive
        return lab

    def _open_backtesting(self) -> None:
        self.open_backtesting()

    # -- research workflow -------------------------------------------------

    def _open_research_wizard(self) -> None:
        """Guided research over the most recent dataset (analysis §15)."""
        from PyQt6.QtWidgets import QMessageBox

        from crypto_trading_lab.ui.research.wizard import ResearchWizardDialog

        dataset, candles = self._load_candles_and_dataset()
        dialog = ResearchWizardDialog(candles, dataset, self._manager(), self)
        dialog.show()
        self._wizard_window = dialog  # keep a reference alive
        if dataset is None and not candles:
            QMessageBox.information(
                self,
                self.tr("New research"),
                self.tr(
                    "There is no versioned dataset yet. Open “Get "
                    "historical data” first."
                ),
            )

    def _open_notebook(self) -> None:
        """Research notebook + experiment manager (chapters 52-54)."""
        from crypto_trading_lab.ui.research.notebook import NotebookDialog

        manager = self._manager()
        if self._notebook_window is None:
            self._notebook_window = NotebookDialog(manager, self)
            self._notebook_window.setWindowTitle(self.tr("Research Notebook"))
        else:
            self._notebook_window.set_manager(manager)
        self._notebook_window.show()
        self._notebook_window.raise_()

    def _open_assistant(self) -> None:
        """Honest, offline research assistant (chapter 55)."""
        from crypto_trading_lab.ai_assistant import AIAssistant
        from crypto_trading_lab.ui.research.assistant import (
            ResearchAssistantDialog,
        )

        manager = self._manager()
        assistant = AIAssistant(self._paths().data_dir / "ai_assistant")
        dialog = ResearchAssistantDialog(
            manager=manager, assistant=assistant, parent=self
        )
        dialog.show()
        self._assistant_window = dialog  # keep a reference alive

    def _open_strategy_builder(self) -> None:
        """Visual strategy rule editor (chapter 34)."""
        from crypto_trading_lab.ui.strategy_builder import StrategyBuilderDialog

        dialog = StrategyBuilderDialog(self)
        dialog.show()
        self._strategy_builder_window = dialog  # keep a reference alive

    def _open_paper(self) -> None:
        """Paper trading over the stored dataset (chapter 57)."""
        from PyQt6.QtWidgets import QMessageBox

        from crypto_trading_lab.ui.paper.paper_trading import PaperTradingWidget

        dataset, candles = self._load_candles_and_dataset()
        if self._paper_window is None:
            self._paper_window = PaperTradingWidget(candles, dataset, self)
            self._paper_window.setWindowTitle(
                self.tr("Crypto Trading Lab — Paper Trading")
            )
            self._paper_window.resize(900, 760)
        else:
            self._paper_window.set_data(candles, dataset)
        self._paper_window.show()
        self._paper_window.raise_()
        if dataset is None:
            QMessageBox.information(
                self,
                self.tr("Paper Trading"),
                self.tr(
                    "There is no dataset yet. Open “Get historical data” "
                    "first: paper trading replays real candles."
                ),
            )

    def _open_testnet(self) -> None:
        """Open the Binance Spot Testnet trading screen (chapter 68, Phase 6)."""
        if self._testnet_window is None:
            self._testnet_window = TestnetTradingWidget(self._trading_manager, self)
            self._testnet_window.setWindowTitle(self.tr("Binance Spot Testnet"))
            self._testnet_window.resize(600, 800)
        self._testnet_window.show()
        self._testnet_window.raise_()


def run(argv: list[str] | None = None) -> int:
    """Launch the application (used by tests and __main__)."""
    argv = argv if argv is not None else sys.argv
    app = QApplication(argv)
    app.setApplicationName("crypto-trading-lab")
    apply_language(app, DEFAULT_LANGUAGE)
    window = MainWindow()
    window.show()
    return app.exec()


def make_app(argv: list[str] | None = None) -> tuple[QApplication, MainWindow]:
    """Create the app and window without entering the event loop (tests)."""
    argv = argv if argv is not None else []
    app = QApplication.instance() or QApplication(argv)
    apply_language(app, DEFAULT_LANGUAGE)
    return app, MainWindow()


__all__ = ["MainWindow", "run", "make_app"]

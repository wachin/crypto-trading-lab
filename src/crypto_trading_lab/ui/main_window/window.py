"""Application entry point (ROADMAP.md chapter 71.1).

``python3 -m crypto_trading_lab`` opens the minimal first-iteration
window: menus, language selector, paper-trading and real-trading
indicators, connection status, welcome panel, educational warning,
and the required buttons.
"""

from __future__ import annotations

import sys

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import (
    QApplication,
    QLabel,
    QMainWindow,
    QProgressDialog,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from crypto_trading_lab.i18n.translations import (
    DEFAULT_LANGUAGE,
    SUPPORTED_LANGUAGES,
    apply_language,
)


class MainWindow(QMainWindow):
    """Minimal first-iteration main window (chapter 71.1)."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(self.tr("Crypto Trading Lab"))
        self.resize(900, 600)

        # Lazy-loaded components (loaded on demand)
        self._learning_center = None
        self._chart_window = None
        self._backtesting_window = None
        self._chart_loaded = False
        self._backtesting_loaded = False
        self._learning_center_loaded = False

        # Lazy-loaded components (loaded on demand)
        self._learning_center = None
        self._chart_window = None
        self._backtesting_window = None
        self._chart_loaded = False
        self._backtesting_loaded = False
        self._learning_center_loaded = False

        self._build_menus()
        self._build_central()

    # -- menus ------------------------------------------------------------

    def _build_menus(self) -> None:
        file_menu = self.menuBar().addMenu(self.tr("&File"))
        self.action_load_csv = QAction(self.tr("Load CSV file..."), self)
        file_menu.addAction(self.action_load_csv)

        view_menu = self.menuBar().addMenu(self.tr("&View"))
        self.action_learning_center = QAction(
            self.tr("Open Learning Center"), self
        )
        view_menu.addAction(self.action_learning_center)

        tools_menu = self.menuBar().addMenu(self.tr("&Tools"))
        self.action_backtesting = QAction(self.tr("Open Backtesting Lab"), self)
        self.action_backtesting.setEnabled(True)  # chapter 37.9
        self.action_backtesting.triggered.connect(self._open_backtesting)
        tools_menu.addAction(self.action_backtesting)
        research_menu = self.menuBar().addMenu(self.tr("&Research"))
        self.action_notebook = QAction(self.tr("Research Notebook"), self)
        self.action_notebook.triggered.connect(self._open_notebook)
        research_menu.addAction(self.action_notebook)

        self.action_assistant = QAction(self.tr("AI Assistant"), self)
        self.action_assistant.triggered.connect(self._open_assistant)
        research_menu.addAction(self.action_assistant)


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
        layout.addWidget(title)

        # Safety indicators (chapter 71.1).
        self.mode_label = QLabel(self.tr("Mode: Paper Trading"))
        self.mode_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.mode_label)

        self.real_trading_label = QLabel(self.tr("Real trading: Disabled"))
        self.real_trading_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.real_trading_label)

        self.status_label = QLabel(self.tr("Disconnected"))
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status_label)

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
        layout.addWidget(message)

        # Welcome panel.
        welcome = QLabel(
            self.tr(
                "Welcome. Begin with the Learning Center to learn "
                "step by step, without risk."
            )
        )
        welcome.setWordWrap(True)
        layout.addWidget(welcome)

        self.csv_button = QPushButton(self.tr("Load CSV file"))
        self.csv_button.clicked.connect(self._open_csv_dialog)
        self.chart_button = QPushButton(self.tr("Open Chart"))
        self.chart_button.clicked.connect(self._open_chart)
        self.learning_center_button = QPushButton(
            self.tr("Open Learning Center")
        )
        self.learning_center_button.clicked.connect(self._open_learning_center)
        self.backtesting_button = QPushButton(self.tr("Open Backtesting Lab"))
        self.backtesting_button.setEnabled(True)  # chapter 37.9
        self.backtesting_button.clicked.connect(self._open_backtesting)
        layout.addWidget(self.csv_button)
        layout.addWidget(self.chart_button)
        layout.addWidget(self.learning_center_button)
        layout.addWidget(self.backtesting_button)

        layout.addStretch(1)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)
        self.statusBar().showMessage(self.tr("Disconnected"))

    def _open_learning_center(self) -> None:
        """Open the Learning Center as a top-level window (chapter 23).
        
        Uses lazy loading - the Learning Center widget is only created
        when first requested.
        """
        if self._learning_center is None:
            from crypto_trading_lab.ui.education.learning_center import (
                LearningCenterWidget,
            )
            self._learning_center = LearningCenterWidget()
            self._learning_center.setWindowTitle(self.tr("Learning Center"))
            self._learning_center.resize(480, 560)
            self._learning_center.show()

    def load_csv_file(
        self, path: str, paths: "AppPaths | None" = None
    ) -> str:
        """Parse a CSV, show the pre-import summary, persist on confirm.

        Chapter 28: nothing reaches the database before the user sees
        a plain-language summary and confirms. Returns a status message
        for the UI/tests. ``paths`` is injectable for tests.
        """
        from pathlib import Path

        from crypto_trading_lab.market_data.importer import parse_csv
        from crypto_trading_lab.configuration.xdg import AppPaths
        from crypto_trading_lab.persistence.database import (
            create_database,
            database_engine,
            make_session_factory,
        )
        from crypto_trading_lab.persistence.candles import CandleRepository

        summary = parse_csv(Path(path))
        if not summary.ok:
            return summary.beginner_explanation()

        paths = paths or AppPaths()
        engine = database_engine(paths.database_file)
        create_database(engine)
        session = make_session_factory(engine)()
        try:
            repo = CandleRepository(session)
            saved = repo.save_candles(summary.candles)
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
            "CSV candles (*.csv);;All files (*)",
        )
        if not path:
            return
        message = self.load_csv_file(path)
        QMessageBox.information(self, self.tr("Import"), message)

    def open_chart(
        self, paths: "AppPaths | None" = None, notify: bool = True
    ) -> "PyQtGraphCandleChart | None":
        """Open the chart window with the most recent imported candles.

        Uses lazy loading - the chart window is created on first access
        and reused on subsequent calls.

        ``notify=False`` skips the message box (used by tests and
        non-interactive callers)."""
        if self._chart_window is None:
            # Show progress dialog for first-time loading
            progress = QProgressDialog(
                self.tr("Loading chart..."), None, 0, 0, self
            )
            progress.setWindowTitle(self.tr("Loading"))
            progress.setWindowModality(Qt.WindowModality.WindowModal)
            progress.setCancelButton(None)
            progress.setMinimumDuration(500)
            progress.show()
            QApplication.processEvents()

            from crypto_trading_lab.configuration.xdg import AppPaths
        from crypto_trading_lab.domain.models import Symbol
        from crypto_trading_lab.persistence.database import (
            create_database,
            database_engine,
            make_session_factory,
        )
        from crypto_trading_lab.persistence.candles import CandleRepository
        from crypto_trading_lab.ui.charts.abstraction import CandleSeries
        from crypto_trading_lab.ui.charts.pyqtgraph_backend import (
            PyQtGraphCandleChart,
        )

        paths = paths or AppPaths()
        candles = []
        if paths.database_file.exists():
            engine = database_engine(paths.database_file)
            create_database(engine)
            session = make_session_factory(engine)()
            try:
                repo = CandleRepository(session)
                candles = repo.load_candles(
                    Symbol("BTC/USDT"), "1m"
                )
            finally:
                session.close()
                engine.dispose()

        if not candles:
            if notify:
                from PyQt6.QtWidgets import QMessageBox

                QMessageBox.information(
                    self,
                    self.tr("Chart"),
                    self.tr(
                        "No candles stored yet. Load a CSV file first "
                        "(File → Load CSV file)."
                    ),
                )
            return None

        chart = PyQtGraphCandleChart()
        chart.setWindowTitle(
            self.tr("Crypto Trading Lab — Chart")
        )
        chart.resize(1000, 600)
        chart.set_candles(
            CandleSeries.from_candles("BTC/USDT", "1m", candles)
        )
        chart.show()
        self._chart_window = chart  # keep a reference alive
        progress.close()
        return chart

        # Already loaded, just show it
        self._chart_window.show()
        self._chart_window.raise_()
        return self._chart_window

    def open_backtesting(
        self, paths: "AppPaths | None" = None, notify: bool = True
    ) -> "BacktestingLabWidget | None":
        """Open the Backtesting Lab over the imported candles (37.9).

        Uses lazy loading - the BacktestingLabWidget is only created
        when first requested.

        The lab always shows chapter 40 metrics, statistical-validity
        warnings and the beginner explanation (37.10): a profitable
        backtest is never presented as proof of future profit.
        ``notify=False`` skips the message box (tests).
        """
        if self._backtesting_window is None:
            # Show progress dialog for first-time loading
            progress = QProgressDialog(
                self.tr("Loading Backtesting Lab..."), None, 0, 0, self
            )
            progress.setWindowTitle(self.tr("Loading"))
            progress.setWindowModality(Qt.WindowModality.WindowModal)
            progress.setCancelButton(None)
            progress.setMinimumDuration(500)
            progress.show()
            QApplication.processEvents()

            from crypto_trading_lab.configuration.xdg import AppPaths
        from crypto_trading_lab.domain.models import Symbol
        from crypto_trading_lab.persistence.database import (
            create_database,
            database_engine,
            make_session_factory,
        )
        from crypto_trading_lab.persistence.candles import CandleRepository
        from crypto_trading_lab.ui.backtesting.lab import (
            BacktestingLabWidget,
        )

        paths = paths or AppPaths()
        candles = []
        if paths.database_file.exists():
            engine = database_engine(paths.database_file)
            create_database(engine)
            session = make_session_factory(engine)()
            try:
                repo = CandleRepository(session)
                candles = repo.load_candles(Symbol("BTC/USDT"), "1m")
            finally:
                session.close()
                engine.dispose()

        if not candles:
            if notify:
                from PyQt6.QtWidgets import QMessageBox

                QMessageBox.information(
                    self,
                    self.tr("Backtesting Lab"),
                    self.tr(
                        "No candles stored yet. Load a CSV file first "
                        "(File → Load CSV file)."
                    ),
                )
            return None

        lab = BacktestingLabWidget(candles, "BTC/USDT", "1m")
        lab.setWindowTitle(self.tr("Crypto Trading Lab — Backtesting Lab"))
        lab.resize(720, 640)
        lab.show()
        self._backtesting_window = lab  # keep a reference alive
        progress.close()
        return lab

        # Already loaded, just show it
        self._backtesting_window.show()
        self._backtesting_window.raise_()
        return self._backtesting_window

    def _open_backtesting(self) -> None:
        self.open_backtesting()

    def _open_chart(self) -> None:
        self.open_chart()



    def _open_notebook(self) -> None:
        """Open the research notebook UI."""
        from crypto_trading_lab.ui.research.notebook import view_notebook
        from crypto_trading_lab.machine_learning.experiment_manager import ExperimentManager
        exp_manager = ExperimentManager()
        entries = exp_manager.list_experiments()
        if not entries:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.information(
                self,
                self.tr("Research Notebook"),
                self.tr("No experiments recorded yet.")
            )
            return
        view_notebook(entries)

    def _open_assistant(self) -> None:
        """Open the AI research assistant UI."""
        from crypto_trading_lab.ui.research.assistant import research_assistant
        from crypto_trading_lab.ai_assistant import AIAssistant
        assistant = AIAssistant()
        research_assistant(assistant)

def run(argv: list[str] | None = None) -> int:
    """Launch the minimal application (used by tests and __main__)."""
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

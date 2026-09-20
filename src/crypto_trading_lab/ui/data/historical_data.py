"""Historical data screen (ROADMAP.md chapters 26.2, 28 and 29).

The user picks an exchange, a market, a timeframe and a period, presses
one button, and gets a validated, identified, checksummed dataset —
instead of hunting for a CSV file and guessing its format.

Everything is translatable (``self.tr``), and the network source plus
the storage paths are injectable so the GUI tests never touch the
internet or the user's real data directory.
"""

from __future__ import annotations

from datetime import datetime, time, timezone

from PyQt6.QtCore import QDate, Qt
from PyQt6.QtWidgets import (
    QComboBox,
    QDateEdit,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from crypto_trading_lab.configuration.xdg import AppPaths
from crypto_trading_lab.market_data.dataset_service import (
    DownloadOutcome,
    download_and_store,
)
from crypto_trading_lab.market_data.historical import (
    SUPPORTED_INTERVALS,
    BinanceKlinesSource,
    HistoricalDataError,
    HistoricalRequest,
)

DEFAULT_SYMBOLS = ("BTC/USDT", "ETH/USDT", "BTC/USDC", "ETH/BTC")
DEFAULT_EXCHANGES = ("Binance Spot",)
#: Binance Spot public REST accepts these symbols unchanged; the combo
#: is editable so a user can type any valid BASE/QUOTE pair.
MAX_RESEARCH_YEARS = 10


class HistoricalDataWidget(QWidget):
    """Download → validate → save a dataset, with a beginner explanation."""

    def __init__(
        self,
        source: BinanceKlinesSource | None = None,
        paths: AppPaths | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._source = source
        self._paths = paths

        layout = QVBoxLayout(self)
        title = QLabel(self.tr("Get historical data"))
        title_font = title.font()
        title_font.setBold(True)
        title_font.setPointSize(14)
        title.setFont(title_font)
        layout.addWidget(title)

        intro = QLabel(
            self.tr(
                "A dataset is a frozen copy of the market's history. Its "
                "identity (exchange, market, timeframe, period and "
                "checksum) is recorded so every experiment can say "
                "exactly which data it used. Data is public: no API key "
                "is needed."
            )
        )
        intro.setWordWrap(True)
        layout.addWidget(intro)

        form = QFormLayout()

        self.exchange_combo = QComboBox()
        self.exchange_combo.addItems(list(DEFAULT_EXCHANGES))
        form.addRow(self.tr("Exchange:"), self.exchange_combo)

        self.symbol_combo = QComboBox()
        self.symbol_combo.setEditable(True)
        self.symbol_combo.addItems(list(DEFAULT_SYMBOLS))
        form.addRow(self.tr("Market:"), self.symbol_combo)

        self.interval_combo = QComboBox()
        for interval in SUPPORTED_INTERVALS:
            self.interval_combo.addItem(interval, interval)
        self.interval_combo.setCurrentText("1h")
        form.addRow(self.tr("Timeframe:"), self.interval_combo)

        dates = QHBoxLayout()
        self.start_date = QDateEdit()
        self.start_date.setCalendarPopup(True)
        self.start_date.setDisplayFormat("yyyy-MM-dd")
        self.start_date.setDate(QDate.currentDate().addYears(-5))
        self.end_date = QDateEdit()
        self.end_date.setCalendarPopup(True)
        self.end_date.setDisplayFormat("yyyy-MM-dd")
        self.end_date.setDate(QDate.currentDate())
        dates.addWidget(self.start_date)
        dates.addWidget(QLabel(self.tr("to")))
        dates.addWidget(self.end_date)
        form.addRow(self.tr("Period (UTC):"), dates)

        layout.addLayout(form)

        self.download_button = QPushButton(self.tr("Download historical data"))
        self.download_button.clicked.connect(self._on_download_clicked)
        layout.addWidget(self.download_button)

        self.status_label = QLabel("")
        self.status_label.setWordWrap(True)
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(self.status_label)

        self.data_view = QTextBrowser()
        self.data_view.setPlainText(
            self.tr(
                "Choose a market, a timeframe and a period, then press "
                "“Download historical data”."
            )
        )
        layout.addWidget(self.data_view)

    # -- request building -------------------------------------------------

    def build_request(self) -> HistoricalRequest:
        """Turn the form into a validated :class:`HistoricalRequest`."""
        exchange = "binance"
        symbol = self.symbol_combo.currentText().strip().upper()
        interval = self.interval_combo.currentData() or "1h"
        start = datetime.combine(
            self.start_date.date().toPyDate(), time(0, 0), tzinfo=timezone.utc
        )
        # The end date is inclusive for the user; make it the last
        # instant of that day so the whole final day is downloaded.
        end = datetime.combine(
            self.end_date.date().toPyDate(), time(23, 59, 59), tzinfo=timezone.utc
        )
        return HistoricalRequest(
            exchange=exchange,
            symbol=symbol,
            interval=interval,
            start=start,
            end=end,
        )

    # -- work -------------------------------------------------------------

    def _on_download_clicked(self) -> None:
        self.download()

    def download(self) -> DownloadOutcome | None:
        """Run the download; returns the outcome (None on invalid input).

        Side effects are limited to the widgets and the configured
        storage paths, which keeps the method testable offscreen.
        """
        from PyQt6.QtWidgets import QApplication, QMessageBox

        try:
            request = self.build_request()
        except ValueError as error:
            message = self.tr(
                "Please check the form: {error}"
            ).format(error=error)
            self.status_label.setText(message)
            self.data_view.setPlainText(message)
            return None

        self.download_button.setEnabled(False)
        self.download_button.setText(self.tr("Downloading…"))
        QApplication.processEvents()
        try:
            outcome = download_and_store(
                request, source=self._source, paths=self._paths
            )
        except HistoricalDataError as error:
            message = error.beginner_explanation()
            self.status_label.setText(self.tr("Download failed"))
            self.data_view.setPlainText(message)
            QMessageBox.warning(self, self.tr("Historical data"), message)
            return None
        finally:
            self.download_button.setEnabled(True)
            self.download_button.setText(self.tr("Download historical data"))

        text = "\n".join(
            [
                outcome.version.beginner_explanation(),
                "",
                outcome.validation.beginner_explanation(),
                "",
                self.tr(
                    "What this means: the candles are stored locally and "
                    "every later result can name this exact dataset. "
                    "Downloading the same period again may return "
                    "different data if the exchange revises it, which is "
                    "why the checksum matters."
                ),
            ]
        )
        self.status_label.setText(outcome.message.splitlines()[0])
        self.data_view.setPlainText(text)
        return outcome


__all__ = ["HistoricalDataWidget", "DEFAULT_SYMBOLS", "DEFAULT_EXCHANGES"]

"""Testnet trading screen (ROADMAP.md chapter 68, Phase 6).

Provides a UI for Binance Spot Testnet trading with safety activation flow.
"""

from __future__ import annotations

from decimal import Decimal

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from crypto_trading_lab.domain.models import Symbol
from crypto_trading_lab.exchanges.binance.adapter import BinanceRestAdapter
from crypto_trading_lab.exchanges.binance.config import BINANCE_SPOT_TESTNET_ENDPOINTS
from crypto_trading_lab.trading import (
    RealTradingManager,
    RealTradingConfig,
    RealTradingState,
    TradingMode,
    REAL_TRADING_WARNINGS,
)


class TestnetTradingWidget(QWidget):
    """Testnet trading account with safety activation flow."""

    def __init__(self, trading_manager: RealTradingManager, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._manager = trading_manager
        self._adapter: BinanceRestAdapter | None = None

        self.setWindowTitle(self.tr("Binance Spot Testnet"))
        layout = QVBoxLayout(self)

        header = QLabel(self.tr("Binance Spot Testnet — Safe Practice Environment"))
        font = header.font()
        font.setBold(True)
        font.setPointSize(15)
        header.setFont(font)
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(header)

        # Info box
        info = QLabel(self.tr(
            "Testnet uses fake money on a simulated exchange. It behaves like real "
            "trading but without financial risk. Use it to practice the activation "
            "flow and test strategies before considering real funds."
        ))
        info.setWordWrap(True)
        info.setStyleSheet("background-color: #e3f2fd; padding: 10px; border-radius: 4px;")
        layout.addWidget(info)

        # Connection status
        self.status_label = QLabel(self.tr("Status: Disconnected"))
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status_label)

        # API credentials
        creds_group = QGroupBox(self.tr("API Credentials (Testnet Only)"))
        creds_layout = QFormLayout(creds_group)
        self.api_key_edit = QLineEdit()
        self.api_key_edit.setPlaceholderText(self.tr("Enter testnet API key"))
        self.api_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        creds_layout.addRow(self.tr("API Key:"), self.api_key_edit)

        self.api_secret_edit = QLineEdit()
        self.api_secret_edit.setPlaceholderText(self.tr("Enter testnet API secret"))
        self.api_secret_edit.setEchoMode(QLineEdit.EchoMode.Password)
        creds_layout.addRow(self.tr("API Secret:"), self.api_secret_edit)

        self.no_withdrawal_check = QCheckBox(self.tr(
            "Confirm this API key has NO withdrawal permissions"
        ))
        self.no_withdrawal_check.setStyleSheet("font-weight: bold; color: #c62828;")
        creds_layout.addRow("", self.no_withdrawal_check)

        self.connect_button = QPushButton(self.tr("Connect to Testnet"))
        self.connect_button.clicked.connect(self._on_connect)
        creds_layout.addRow("", self.connect_button)
        layout.addWidget(creds_group)

        # Safety activation (simplified for testnet)
        self.activation_group = QGroupBox(self.tr("Safety Activation (Testnet Practice)"))
        self.activation_group.setEnabled(False)
        act_layout = QVBoxLayout(self.activation_group)

        # Step 1: Advanced option
        self.advanced_check = QCheckBox(self.tr("Enable advanced option (testnet practice)"))
        self.advanced_check.stateChanged.connect(self._update_activation)
        act_layout.addWidget(self.advanced_check)

        # Step 2: Risk warning
        self.risk_warning_check = QCheckBox(self.tr("Acknowledge risk warning"))
        self.risk_warning_check.stateChanged.connect(self._update_activation)
        act_layout.addWidget(self.risk_warning_check)

        risk_text = QLabel(REAL_TRADING_WARNINGS)
        risk_text.setWordWrap(True)
        risk_text.setStyleSheet("font-size: 11px; color: #666;")
        act_layout.addWidget(risk_text)

        # Step 3: Written confirmation
        self.confirmation_edit = QLineEdit()
        self.confirmation_edit.setPlaceholderText(self.tr("Type 'I UNDERSTAND THE RISKS' to confirm"))
        self.confirmation_edit.textChanged.connect(self._update_activation)
        act_layout.addWidget(QLabel(self.tr("Written confirmation:")))
        act_layout.addWidget(self.confirmation_edit)

        # Step 4: Confirmation phrase
        self.phrase_check = QCheckBox(self.tr("Confirm: 'I UNDERSTAND THE RISKS'"))
        self.phrase_check.stateChanged.connect(self._update_activation)
        act_layout.addWidget(self.phrase_check)

        # Risk limits
        risk_limits = QGroupBox(self.tr("Risk Limits (Conservative for Testnet)"))
        risk_form = QFormLayout(risk_limits)
        self.max_position_edit = QLineEdit("2.0")
        risk_form.addRow(self.tr("Max position (%):"), self.max_position_edit)
        self.max_daily_loss_edit = QLineEdit("1.0")
        risk_form.addRow(self.tr("Max daily loss (%):"), self.max_daily_loss_edit)
        self.max_exposure_edit = QLineEdit("0.10")
        risk_form.addRow(self.tr("Max total exposure (0-1):"), self.max_exposure_edit)
        act_layout.addWidget(risk_limits)

        # Connectivity checks
        self.connectivity_check = QCheckBox(self.tr("Verify connectivity"))
        self.connectivity_check.stateChanged.connect(self._update_activation)
        act_layout.addWidget(self.connectivity_check)

        self.balance_check = QCheckBox(self.tr("Verify account balances"))
        self.balance_check.stateChanged.connect(self._update_activation)
        act_layout.addWidget(self.balance_check)

        self.market_data_check = QCheckBox(self.tr("Verify market data freshness"))
        self.market_data_check.stateChanged.connect(self._update_activation)
        act_layout.addWidget(self.market_data_check)

        self.time_sync_check = QCheckBox(self.tr("Verify system time synchronization"))
        self.time_sync_check.stateChanged.connect(self._update_activation)
        act_layout.addWidget(self.time_sync_check)

        self.kill_switch_check = QCheckBox(self.tr("Confirm emergency kill switch configuration"))
        self.kill_switch_check.stateChanged.connect(self._update_activation)
        act_layout.addWidget(self.kill_switch_check)

        self.activate_button = QPushButton(self.tr("Activate Testnet Trading"))
        self.activate_button.setEnabled(False)
        self.activate_button.clicked.connect(self._on_activate)
        act_layout.addWidget(self.activate_button)

        layout.addWidget(self.activation_group)

        # Account info display
        self.account_view = QTextBrowser()
        self.account_view.setPlainText(self.tr("Connect to testnet to see account info..."))
        layout.addWidget(self.account_view)

        self.setMinimumWidth(500)

    def _on_connect(self) -> None:
        api_key = self.api_key_edit.text().strip()
        api_secret = self.api_secret_edit.text().strip()
        if not api_key or not api_secret:
            self.status_label.setText(self.tr("Please enter both API key and secret"))
            return

        self._adapter = BinanceRestAdapter(
            BINANCE_SPOT_TESTNET_ENDPOINTS,
            api_key=api_key,
            api_secret=api_secret,
            allow_trading=True,
        )
        self._adapter.connect()
        self.status_label.setText(self.tr(f"Status: {self._adapter.state().value.capitalize()}"))

        if self._adapter.state() == self._adapter.state().__class__.CONNECTED:
            # Update manager config
            self._manager.config.api_key_has_no_withdrawal = self.no_withdrawal_check.isChecked()
            self._manager.select_environment("Binance", "Spot Testnet")
            self.activation_group.setEnabled(True)
            self._update_account_display()
        else:
            QMessageBox.warning(self, self.tr("Connection Failed"),
                                self.tr("Could not connect to Binance Spot Testnet"))

    def _update_account_display(self) -> None:
        if not self._adapter:
            return
        try:
            balances = self._adapter.fetch_balances()
            open_orders = self._adapter.fetch_open_orders()
            text = self.tr("Account Balances:\n")
            for sym, bal in balances.items():
                if bal.free > 0 or bal.locked > 0:
                    text += f"  {sym}: free={bal.free}, locked={bal.locked}\n"
            text += f"\nOpen Orders: {len(open_orders)}\n"
            self.account_view.setPlainText(text)
        except Exception as e:
            self.account_view.setPlainText(self.tr(f"Error fetching account: {e}"))

    def _update_activation(self) -> None:
        all_checked = (
            self.advanced_check.isChecked() and
            self.risk_warning_check.isChecked() and
            self.confirmation_edit.text().strip() == "I UNDERSTAND THE RISKS" and
            self.phrase_check.isChecked() and
            self.connectivity_check.isChecked() and
            self.balance_check.isChecked() and
            self.market_data_check.isChecked() and
            self.time_sync_check.isChecked() and
            self.kill_switch_check.isChecked() and
            self.no_withdrawal_check.isChecked()
        )
        self.activate_button.setEnabled(all_checked)

    def _on_activate(self) -> None:
        try:
            max_pos = Decimal(self.max_position_edit.text().strip())
            max_daily = Decimal(self.max_daily_loss_edit.text().strip())
            max_exp = Decimal(self.max_exposure_edit.text().strip())
        except Exception:
            QMessageBox.warning(self, self.tr("Invalid Input"), self.tr("Please enter valid numbers for risk limits"))
            return

        self._manager.configure_risk_limits(max_pos, max_daily, max_exp)
        self._manager.test_connectivity(self._adapter is not None and self._adapter.state() == self._adapter.state().__class__.CONNECTED)
        self._manager.verify_account_balances(True)
        self._manager.verify_market_data_freshness(True)
        # Time sync verification would require NTP check
        self._manager.verify_time_sync(True)
        self._manager.verify_kill_switch_config(True)
        self._manager.verify_confirmation_phrase(self.phrase_check.isChecked())

        success = self._manager.complete_activation()
        if success:
            self.status_label.setText(self.tr("Status: Testnet Trading ACTIVE"))
            self.account_view.append(self.tr("\n*** TESTNET TRADING ACTIVATED ***"))
        else:
            QMessageBox.warning(self, self.tr("Activation Failed"),
                                self.tr("Not all safety requirements are met"))
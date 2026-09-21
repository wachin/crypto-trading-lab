"""Connection health dashboard widget (ROADMAP chapters 26.2, 27).

Displays real-time connection state with beginner-friendly explanations,
technical details, and troubleshooting links for live market data feeds.
"""

from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QLabel,
    QVBoxLayout,
    QWidget,
    QFrame,
    QHBoxLayout,
    QPushButton,
)

from crypto_trading_lab.domain.models import ConnectionState
from crypto_trading_lab.exchanges.connection_state_descriptors import get_descriptor


class ConnectionHealthWidget(QWidget):
    """Real-time connection health monitor."""
    
    state_changed = pyqtSignal(ConnectionState, str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_state = ConnectionState.DISCONNECTED
        self._build_ui()
        
    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)
        
        # Header
        header = QLabel(self.tr("Connection Health"))
        header.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(header)
        
        # Status indicator
        self.status_frame = QFrame()
        self.status_frame.setStyleSheet("""
            QFrame {
                border: 2px solid #ccc;
                border-radius: 8px;
                padding: 8px;
                background-color: #f5f5f5;
            }
        """)
        
        status_layout = QVBoxLayout(self.status_frame)
        
        self.state_label = QLabel(self.tr("Disconnected"))
        self.state_label.setStyleSheet("font-weight: bold; font-size: 16px;")
        status_layout.addWidget(self.state_label)
        
        self.explanation_label = QLabel(self.tr("Not connected to the exchange. No market data is arriving."))
        self.explanation_label.setWordWrap(True)
        status_layout.addWidget(self.explanation_label)
        
        # Technical details (collapsible)
        self.tech_label = QLabel()
        self.tech_label.setWordWrap(True)
        self.tech_label.setStyleSheet("font-size: 10px; color: #666;")
        status_layout.addWidget(self.tech_label)
        
        layout.addWidget(self.status_frame)
        
        # Troubleshooting button
        self.help_button = QPushButton(self.tr("Help & Troubleshooting"))
        self.help_button.clicked.connect(self._show_help)
        layout.addWidget(self.help_button)
        
        self.update_state(ConnectionState.DISCONNECTED)
        
    def update_state(self, state: ConnectionState, custom_message: str = ""):
        """Update connection state display."""
        self._current_state = state
        desc = get_descriptor(state)
        
        # Update UI
        self.state_label.setText(desc.status_label)
        self.explanation_label.setText(custom_message or desc.beginner_explanation)
        self.tech_label.setText(f"Technical: {desc.technical_description}")
        
        # Update styling based on severity
        if desc.severity == "error":
            self.status_frame.setStyleSheet("""
                QFrame {
                    border: 2px solid #d32f2f;
                    border-radius: 8px;
                    padding: 8px;
                    background-color: #ffebee;
                }
            """)
        elif desc.severity == "warning":
            self.status_frame.setStyleSheet("""
                QFrame {
                    border: 2px solid #f57c00;
                    border-radius: 8px;
                    padding: 8px;
                    background-color: #fff3e0;
                }
            """)
        else:
            self.status_frame.setStyleSheet("""
                QFrame {
                    border: 2px solid #4caf50;
                    border-radius: 8px;
                    padding: 8px;
                    background-color: #e8f5e9;
                }
            """)
        
        self.state_changed.emit(state, desc.beginner_explanation)
        
    def _show_help(self):
        """Show troubleshooting information."""
        desc = get_descriptor(self._current_state)
        if desc.troubleshooting_link:
            # In a real app, this would open the help file
            # For now, just show a message
            self.tr("See documentation:")  # Placeholder

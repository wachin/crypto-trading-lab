"""Connection state technical descriptions and troubleshooting (ROADMAP chapter 27).

Every connection state must have:
- technical description
- beginner-friendly explanation (already in ConnectionState)
- visible status label
- troubleshooting link

This module provides the additional metadata required by chapter 27.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from crypto_trading_lab.domain.models import ConnectionState


@dataclass(frozen=True)
class ConnectionStateDescriptor:
    """Complete metadata for a connection state."""
    
    state: ConnectionState
    technical_description: str
    beginner_explanation: str
    status_label: str
    troubleshooting_link: str
    severity: str  # info, warning, error


_STATE_DESCRIPTORS: dict[ConnectionState, ConnectionStateDescriptor] = {
    ConnectionState.DISCONNECTED: ConnectionStateDescriptor(
        state=ConnectionState.DISCONNECTED,
        technical_description="WebSocket connection is closed and no reconnection attempt is active.",
        beginner_explanation="Not connected to the exchange. No market data is arriving.",
        status_label="Disconnected",
        troubleshooting_link="docs/en/user-guide/20-troubleshooting.md#connection-disconnected",
        severity="info",
    ),
    ConnectionState.CONNECTING: ConnectionStateDescriptor(
        state=ConnectionState.CONNECTING,
        technical_description="TCP connection handshake in progress to exchange WebSocket endpoint.",
        beginner_explanation="Trying to reach the exchange. Please wait a moment.",
        status_label="Connecting...",
        troubleshooting_link="docs/en/user-guide/20-troubleshooting.md#connection-timeout",
        severity="info",
    ),
    ConnectionState.AUTHENTICATING: ConnectionStateDescriptor(
        state=ConnectionState.AUTHENTICATING,
        technical_description="API credential verification in progress with exchange.",
        beginner_explanation="Verifying your API credentials with the exchange.",
        status_label="Authenticating...",
        troubleshooting_link="docs/en/user-guide/20-troubleshooting.md#authentication-failed",
        severity="info",
    ),
    ConnectionState.SUBSCRIBING: ConnectionStateDescriptor(
        state=ConnectionState.SUBSCRIBING,
        technical_description="WebSocket SUBSCRIBE message sent, awaiting confirmation from exchange.",
        beginner_explanation="Asking the exchange for the data streams you selected.",
        status_label="Subscribing...",
        troubleshooting_link="docs/en/user-guide/20-troubleshooting.md#subscription-failed",
        severity="info",
    ),
    ConnectionState.CONNECTED: ConnectionStateDescriptor(
        state=ConnectionState.CONNECTED,
        technical_description="WebSocket connection established and receiving data streams normally.",
        beginner_explanation="Connected and receiving live data normally.",
        status_label="Connected",
        troubleshooting_link="",
        severity="info",
    ),
    ConnectionState.DEGRADED: ConnectionStateDescriptor(
        state=ConnectionState.DEGRADED,
        technical_description="Connection active but data latency exceeds threshold or messages are out-of-order.",
        beginner_explanation="Connected, but some data is late or incomplete. Treat recent values with care.",
        status_label="Degraded",
        troubleshooting_link="docs/en/user-guide/20-troubleshooting.md#degraded-data",
        severity="warning",
    ),
    ConnectionState.RECONNECTING: ConnectionStateDescriptor(
        state=ConnectionState.RECONNECTING,
        technical_description="Connection lost, exponential backoff reconnection in progress.",
        beginner_explanation="The connection dropped and the app is trying again on its own.",
        status_label="Reconnecting...",
        troubleshooting_link="docs/en/user-guide/20-troubleshooting.md#reconnection-loop",
        severity="warning",
    ),
    ConnectionState.RATE_LIMITED: ConnectionStateDescriptor(
        state=ConnectionState.RATE_LIMITED,
        technical_description="Exchange rate limit exceeded, requests paused per circuit breaker rules.",
        beginner_explanation="The exchange asked us to slow down. Requests are paused briefly and will resume automatically.",
        status_label="Rate Limited",
        troubleshooting_link="docs/en/user-guide/20-troubleshooting.md#rate-limited",
        severity="warning",
    ),
    ConnectionState.ERROR: ConnectionStateDescriptor(
        state=ConnectionState.ERROR,
        technical_description="Connection failed with unrecoverable error. Circuit breaker is open.",
        beginner_explanation="Something failed while talking to the exchange. Check the message and troubleshooting guide.",
        status_label="Error",
        troubleshooting_link="docs/en/user-guide/20-troubleshooting.md#connection-error",
        severity="error",
    ),
    ConnectionState.STOPPED: ConnectionStateDescriptor(
        state=ConnectionState.STOPPED,
        technical_description="Connection intentionally closed by user or application shutdown.",
        beginner_explanation="The connection was closed on purpose (for example, by you or the kill switch).",
        status_label="Stopped",
        troubleshooting_link="",
        severity="info",
    ),
}


def get_descriptor(state: ConnectionState) -> ConnectionStateDescriptor:
    """Return complete metadata for a connection state."""
    return _STATE_DESCRIPTORS[state]


def get_all_descriptors() -> list[ConnectionStateDescriptor]:
    """Return descriptors for all connection states."""
    return list(_STATE_DESCRIPTORS.values())

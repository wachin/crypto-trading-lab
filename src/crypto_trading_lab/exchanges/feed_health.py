"""Persisted feed health metrics (ROADMAP chapters 26.2, 27).

Stores connection health metrics in SQLite so they persist across
sessions and can be reviewed later. This satisfies the requirement
for "persisted feed health metrics" in the live trading roadmap.

Metrics are stored with timestamps, allowing trend analysis over
time to detect recurring connection issues.
"""

from __future__ import annotations

import json
import logging
import sqlite3
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Optional

from crypto_trading_lab.domain.models import ConnectionState

logger = logging.getLogger(__name__)


class FeedHealthStatus(str, Enum):
    """Overall feed health classification."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    DISCONNECTED = "disconnected"
    ERROR = "error"


class FeedHealthRecord:
    """One health metric record."""
    
    def __init__(
        self,
        timestamp: datetime,
        state: ConnectionState,
        stale: bool,
        age_seconds: Optional[float],
        server_time_offset: float,
        subscriptions: list[str],
        message_count: int,
        reconnect_attempts: int,
        circuit_breaker_state: str,
    ):
        self.timestamp = timestamp
        self.state = state
        self.stale = stale
        self.age_seconds = age_seconds
        self.server_time_offset = server_time_offset
        self.subscriptions = subscriptions
        self.message_count = message_count
        self.reconnect_attempts = reconnect_attempts
        self.circuit_breaker_state = circuit_breaker_state
        
    @property
    def status(self) -> FeedHealthStatus:
        """Classify overall health."""
        if self.state == ConnectionState.CONNECTED and not self.stale:
            return FeedHealthStatus.HEALTHY
        if self.state == ConnectionState.ERROR:
            return FeedHealthStatus.ERROR
        if self.stale or self.state == ConnectionState.DEGRADED:
            return FeedHealthStatus.DEGRADED
        return FeedHealthStatus.DISCONNECTED
        
    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp.isoformat(),
            "state": self.state.value,
            "stale": self.stale,
            "age_seconds": self.age_seconds,
            "server_time_offset": self.server_time_offset,
            "subscriptions": json.dumps(self.subscriptions),
            "message_count": self.message_count,
            "reconnect_attempts": self.reconnect_attempts,
            "circuit_breaker_state": self.circuit_breaker_state,
            "status": self.status.value,
        }


class FeedHealthStore:
    """SQLite-backed store for feed health metrics.
    
    Persists health records so they survive application restarts
    and can be analyzed for recurring connection issues.
    """
    
    def __init__(self, db_path: Path):
        self._db_path = db_path
        self._init_db()
        
    def _init_db(self) -> None:
        """Create health metrics table if not exists."""
        conn = sqlite3.connect(self._db_path)
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS feed_health (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    state TEXT NOT NULL,
                    stale INTEGER NOT NULL,
                    age_seconds REAL,
                    server_time_offset REAL NOT NULL,
                    subscriptions TEXT NOT NULL,
                    message_count INTEGER NOT NULL,
                    reconnect_attempts INTEGER NOT NULL,
                    circuit_breaker_state TEXT NOT NULL,
                    status TEXT NOT NULL
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_feed_health_timestamp
                ON feed_health(timestamp)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_feed_health_state
                ON feed_health(state)
            """)
            conn.commit()
        finally:
            conn.close()
            
    def record(self, record: FeedHealthRecord) -> None:
        """Store a health metric record."""
        conn = sqlite3.connect(self._db_path)
        try:
            conn.execute("""
                INSERT INTO feed_health (
                    timestamp, state, stale, age_seconds,
                    server_time_offset, subscriptions, message_count,
                    reconnect_attempts, circuit_breaker_state, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                record.timestamp.isoformat(),
                record.state.value,
                1 if record.stale else 0,
                record.age_seconds,
                record.server_time_offset,
                json.dumps(record.subscriptions),
                record.message_count,
                record.reconnect_attempts,
                record.circuit_breaker_state,
                record.status.value,
            ))
            conn.commit()
        except Exception as e:
            logger.warning("Failed to store health metric: %s", e)
        finally:
            conn.close()
            
    def get_latest(self) -> Optional[FeedHealthRecord]:
        """Return the most recent health record."""
        conn = sqlite3.connect(self._db_path)
        try:
            cursor = conn.execute("""
                SELECT * FROM feed_health
                ORDER BY timestamp DESC LIMIT 1
            """)
            row = cursor.fetchone()
            if row is None:
                return None
            return self._row_to_record(row)
        finally:
            conn.close()
            
    def get_recent(self, limit: int = 100) -> list[FeedHealthRecord]:
        """Return the most recent health records."""
        conn = sqlite3.connect(self._db_path)
        try:
            cursor = conn.execute("""
                SELECT * FROM feed_health
                ORDER BY timestamp DESC LIMIT ?
            """, (limit,))
            return [self._row_to_record(row) for row in cursor.fetchall()]
        finally:
            conn.close()
            
    def get_health_summary(self) -> dict:
        """Return summary statistics for feed health."""
        conn = sqlite3.connect(self._db_path)
        try:
            cursor = conn.execute("""
                SELECT
                    COUNT(*) as total,
                    SUM(CASE WHEN status = 'healthy' THEN 1 ELSE 0 END) as healthy,
                    SUM(CASE WHEN status = 'degraded' THEN 1 ELSE 0 END) as degraded,
                    SUM(CASE WHEN status = 'error' THEN 1 ELSE 0 END) as errors,
                    SUM(CASE WHEN status = 'disconnected' THEN 1 ELSE 0 END) as disconnected
                FROM feed_health
            """)
            row = cursor.fetchone()
            if row is None or row[0] == 0:
                return {"total": 0}
                
            total, healthy, degraded, errors, disconnected = row
            return {
                "total": total,
                "healthy": healthy,
                "degraded": degraded,
                "errors": errors,
                "disconnected": disconnected,
                "health_percentage": round(healthy / total * 100, 1) if total > 0 else 0,
            }
        finally:
            conn.close()
            
    def _row_to_record(self, row: tuple) -> FeedHealthRecord:
        """Convert database row to FeedHealthRecord."""
        return FeedHealthRecord(
            timestamp=datetime.fromisoformat(row[1]),
            state=ConnectionState(row[2]),
            stale=bool(row[3]),
            age_seconds=row[4],
            server_time_offset=row[5],
            subscriptions=json.loads(row[6]),
            message_count=row[7],
            reconnect_attempts=row[8],
            circuit_breaker_state=row[9],
        )

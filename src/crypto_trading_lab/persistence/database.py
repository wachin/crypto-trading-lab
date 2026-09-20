"""Initial SQLite database via SQLAlchemy (ROADMAP.md chapter 8).

WAL mode, foreign keys, indexes, and a schema-version migration
table are enabled from day one. API keys are never stored here
(chapter 8: "Do not store API keys in SQLite").
"""

from __future__ import annotations

from pathlib import Path

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum as SaEnum,
    ForeignKey,
    Integer,
    MetaData,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    create_engine,
    event,
    func,
    insert,
    select,
    text,
)
from sqlalchemy.engine import Engine
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    Session,
    mapped_column,
    sessionmaker,
)

from crypto_trading_lab.domain.models import OrderSide, OrderStatus

__all__ = [
    "SCHEMA_VERSION",
    "Base",
    "ExchangeRecord",
    "MarketRecord",
    "CandleRecord",
    "DatasetRecord",
    "OrderRecord",
    "BalanceRecord",
    "AuditRecord",
    "create_database",
    "database_engine",
    "naming_convention",
]


#: Current schema version; migrations must bump this (chapter 8).
#: v2 adds the ``datasets`` table (chapters 29 and 53).
SCHEMA_VERSION = 2


class Base(DeclarativeBase):
    """Declarative base with a stable naming convention."""

    metadata = MetaData(
        naming_convention={
            "ix": "ix_%(column_0_label)s",
            "uq": "uq_%(table_name)s_%(column_0_name)s",
            "ck": "ck_%(table_name)s_%(constraint_name)s",
            "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
            "pk": "pk_%(table_name)s",
        }
    )


class ExchangeRecord(Base):
    """A configured exchange (chapter 8: "configured exchanges")."""

    __tablename__ = "exchanges"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(50), unique=True)
    is_testnet: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[str] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class MarketRecord(Base):
    """A tradable market on an exchange (chapter 8: "markets")."""

    __tablename__ = "markets"
    __table_args__ = (
        UniqueConstraint("exchange_id", "symbol", name="uq_market_symbol"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    exchange_id: Mapped[int] = mapped_column(
        ForeignKey("exchanges.id", ondelete="CASCADE"), index=True
    )
    symbol: Mapped[str] = mapped_column(String(30), index=True)
    base: Mapped[str] = mapped_column(String(20))
    quote: Mapped[str] = mapped_column(String(20))
    tick_size: Mapped[str] = mapped_column(Numeric(38, 18))
    step_size: Mapped[str] = mapped_column(Numeric(38, 18))
    min_quantity: Mapped[str] = mapped_column(Numeric(38, 18))
    min_notional: Mapped[str] = mapped_column(Numeric(38, 18))
    maker_fee: Mapped[str] = mapped_column(Numeric(10, 6))
    taker_fee: Mapped[str] = mapped_column(Numeric(10, 6))


class CandleRecord(Base):
    """An OHLCV candle (chapter 8: "candles", indexed for fast range reads)."""

    __tablename__ = "candles"
    __table_args__ = (
        UniqueConstraint(
            "market_id", "interval", "open_time", name="uq_candle_key"
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    market_id: Mapped[int] = mapped_column(
        ForeignKey("markets.id", ondelete="CASCADE"), index=True
    )
    interval: Mapped[str] = mapped_column(String(10), index=True)
    # UTC ISO-8601 strings: SQLite drops tzinfo on DateTime, so the
    # canonical UTC representation is kept explicitly (chapter 7).
    open_time: Mapped[str] = mapped_column(String(40), index=True)
    close_time: Mapped[str] = mapped_column(String(40))
    open: Mapped[float] = mapped_column(Numeric(38, 18))
    high: Mapped[float] = mapped_column(Numeric(38, 18))
    low: Mapped[float] = mapped_column(Numeric(38, 18))
    close: Mapped[float] = mapped_column(Numeric(38, 18))
    volume: Mapped[float] = mapped_column(Numeric(38, 18))


class DatasetRecord(Base):
    """An identified, checksummed slice of history (chapters 29 and 53).

    A dataset is the unit of reproducibility: every backtest and
    experiment references a ``dataset_id``, never just "BTC/USDT".
    """

    __tablename__ = "datasets"

    dataset_id: Mapped[str] = mapped_column(String(120), primary_key=True)
    exchange: Mapped[str] = mapped_column(String(50), index=True)
    symbol: Mapped[str] = mapped_column(String(30), index=True)
    interval: Mapped[str] = mapped_column(String(10), index=True)
    start: Mapped[str] = mapped_column(String(40))
    end: Mapped[str] = mapped_column(String(40))
    candle_count: Mapped[int] = mapped_column(Integer)
    missing: Mapped[int] = mapped_column(Integer, default=0)
    duplicates: Mapped[int] = mapped_column(Integer, default=0)
    invalid: Mapped[int] = mapped_column(Integer, default=0)
    checksum: Mapped[str] = mapped_column(String(64), index=True)
    source: Mapped[str] = mapped_column(String(200), default="")
    timezone_name: Mapped[str] = mapped_column(String(20), default="UTC")
    version: Mapped[int] = mapped_column(Integer, default=1)
    ready: Mapped[bool] = mapped_column(Boolean, default=True)
    downloaded_at: Mapped[str] = mapped_column(String(40))
    created_at: Mapped[str] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class OrderRecord(Base):
    """A simulated order (chapter 8: "simulated orders")."""
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    market_id: Mapped[int] = mapped_column(
        ForeignKey("markets.id", ondelete="CASCADE"), index=True
    )
    adapter_order_id: Mapped[str] = mapped_column(String(64), unique=True)
    side: Mapped[OrderSide] = mapped_column(SaEnum(OrderSide))
    order_type: Mapped[str] = mapped_column(String(20))
    status: Mapped[OrderStatus] = mapped_column(SaEnum(OrderStatus), index=True)
    price: Mapped[float | None] = mapped_column(Numeric(38, 18), nullable=True)
    quantity: Mapped[float] = mapped_column(Numeric(38, 18))
    filled_quantity: Mapped[float] = mapped_column(Numeric(38, 18), default=0)
    created_at: Mapped[str] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )


class BalanceRecord(Base):
    """Simulated per-asset balance (chapter 8: "simulated balances")."""

    __tablename__ = "balances"
    __table_args__ = (
        UniqueConstraint("account", "asset", name="uq_balance_asset"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    account: Mapped[str] = mapped_column(String(50), default="paper")
    asset: Mapped[str] = mapped_column(String(20))
    amount: Mapped[float] = mapped_column(Numeric(38, 18))


class AuditRecord(Base):
    """Append-only audit trail (chapter 8: "audit records")."""

    __tablename__ = "audit"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    event: Mapped[str] = mapped_column(String(50), index=True)
    detail: Mapped[str] = mapped_column(Text, default="{}")
    correlation_id: Mapped[str] = mapped_column(
        String(64), nullable=True, index=True
    )
    recorded_at: Mapped[str] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )


def _enable_sqlite_features(engine: Engine) -> None:
    """Enable WAL mode and foreign keys on each connection (chapter 8)."""

    @event.listens_for(engine, "connect")
    def _on_connect(dbapi_connection, _record):  # noqa: ANN001
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.close()


def database_engine(path: str | Path) -> Engine:
    """Create a configured SQLite engine with WAL and foreign keys."""
    if str(path) != ":memory:":
        Path(path).parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(
        f"sqlite:///{path}",
        # Detect disconnects; SQLite needs it for cross-thread tests.
        connect_args={"check_same_thread": False} if str(path) != ":memory:" else {},
    )
    if str(path) != ":memory:":
        _enable_sqlite_features(engine)
    else:

        @event.listens_for(engine, "connect")
        def _memory_fk(dbapi_connection, _record):  # noqa: ANN001
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    return engine


def create_database(engine: Engine) -> None:
    """Create all tables and stamp the schema version."""
    Base.metadata.create_all(engine)
    with engine.begin() as connection:
        connection.execute(
            insert(ExchangeRecord.__table__).values(
                id=1, name="mock", is_testnet=False
            ).prefix_with("OR IGNORE")
        )
        connection.execute(
            text(
                "CREATE TABLE IF NOT EXISTS schema_migrations ("
                "version INTEGER PRIMARY KEY, applied_at TEXT)"
            )
        )
        connection.execute(
            text(
                "INSERT OR IGNORE INTO schema_migrations (version, applied_at) "
                "VALUES (:version, CURRENT_TIMESTAMP)"
            ),
            {"version": SCHEMA_VERSION},
        )


def make_session_factory(engine: Engine):
    """Session factory bound to an engine."""
    return sessionmaker(bind=engine, expire_on_commit=False)

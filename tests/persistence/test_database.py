"""Tests for the initial SQLite persistence layer (ROADMAP.md chapter 8)."""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy import select, text

from crypto_trading_lab.domain.models import (
    Candle,
    Market,
    OrderSide,
    OrderStatus,
    Symbol,
    Ticker,
    utc_now,
)
from crypto_trading_lab.persistence.database import (
    SCHEMA_VERSION,
    BalanceRecord,
    CandleRecord,
    ExchangeRecord,
    MarketRecord,
    OrderRecord,
    create_database,
    database_engine,
    make_session_factory,
)

MARKET = Market(
    exchange="mock",
    symbol=Symbol("BTC/USDT"),
    base="BTC",
    quote="USDT",
    price_precision=2,
    quantity_precision=6,
    min_quantity=Decimal("0.00001"),
    min_notional=Decimal("10"),
    maker_fee=Decimal("0.001"),
    taker_fee=Decimal("0.001"),
)


def _engine():
    engine = database_engine(":memory:")
    create_database(engine)
    return engine


def _seed_market(session) -> MarketRecord:
    exchange = session.scalar(select(ExchangeRecord).limit(1))
    record = MarketRecord(
        exchange_id=exchange.id,
        symbol=str(MARKET.symbol),
        base=MARKET.symbol.base,
        quote=MARKET.symbol.quote,
        tick_size=Decimal("0.01"),
        step_size=Decimal("0.000001"),
        min_quantity=MARKET.min_quantity,
        min_notional=MARKET.min_notional,
        maker_fee=MARKET.maker_fee,
        taker_fee=MARKET.taker_fee,
    )
    session.add(record)
    session.flush()
    return record


def test_schema_version_is_stamped():
    engine = _engine()
    with engine.begin() as connection:
        rows = connection.execute(
            text("SELECT version FROM schema_migrations")
        ).fetchall()
    assert SCHEMA_VERSION in {row[0] for row in rows}


def test_foreign_keys_are_enforced():
    engine = _engine()
    session = make_session_factory(engine)()
    record = MarketRecord(
        exchange_id=999,  # no such exchange
        symbol="BTC/USDT",
        base="BTC",
        quote="USDT",
        tick_size=Decimal("0.01"),
        step_size=Decimal("0.000001"),
        min_quantity=MARKET.min_quantity,
        min_notional=MARKET.min_notional,
        maker_fee=MARKET.maker_fee,
        taker_fee=MARKET.taker_fee,
    )
    session.add(record)
    try:
        session.flush()
    except Exception:
        session.rollback()
    else:
        raise AssertionError("foreign key must reject orphan market")
    finally:
        session.close()


def test_candle_unique_constraint_prevents_duplicates():
    engine = _engine()
    factory = make_session_factory(engine)
    now = utc_now()
    with factory() as session:
        market = _seed_market(session)
        session.add(
            CandleRecord(
                market_id=market.id,
                interval="1m",
                open_time=now,
                close_time=now,
                open=Decimal(1),
                high=Decimal(2),
                low=Decimal(0.5),
                close=Decimal(1.5),
                volume=Decimal(10),
            )
        )
        session.commit()
    with factory() as session:
        market_id = session.scalar(
            select(MarketRecord.id).where(MarketRecord.symbol == "BTC/USDT")
        )
        session.add(
            CandleRecord(
                market_id=market_id,
                interval="1m",
                open_time=now,
                close_time=now,
                open=Decimal(1),
                high=Decimal(2),
                low=Decimal(0.5),
                close=Decimal(1.5),
                volume=Decimal(10),
            )
        )
        try:
            session.commit()
        except Exception:
            session.rollback()
        else:
            raise AssertionError("duplicate candle must be rejected")


def test_wal_mode_enabled_for_file_databases(tmp_path):
    engine = database_engine(tmp_path / "lab.db")
    create_database(engine)
    with engine.connect() as connection:
        mode = connection.execute(
            text("PRAGMA journal_mode")
        ).scalar_one()
    assert str(mode).lower() == "wal"


def test_order_and_balance_roundtrip():
    engine = _engine()
    factory = make_session_factory(engine)
    with factory() as session:
        market = _seed_market(session)
        session.add(
            OrderRecord(
                market_id=market.id,
                adapter_order_id="ord-1",
                side=OrderSide.BUY,
                order_type="market",
                status=OrderStatus.FILLED,
                price=Decimal("42000.10"),
                quantity=Decimal("0.5"),
                filled_quantity=Decimal("0.5"),
            )
        )
        session.add(
            BalanceRecord(account="paper", asset="USDT", amount=Decimal("1000"))
        )
        session.commit()

        order = session.scalar(select(OrderRecord))
        balance = session.scalar(select(BalanceRecord))
        assert order.side is OrderSide.BUY
        assert order.status is OrderStatus.FILLED
        assert Decimal(str(balance.amount)) == Decimal("1000")


def test_default_mock_exchange_is_seeded():
    engine = _engine()
    with engine.connect() as connection:
        name = connection.execute(
            text("SELECT name FROM exchanges WHERE id = 1")
        ).scalar_one()
    assert name == "mock"

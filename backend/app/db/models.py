from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Venue(str, enum.Enum):
    kalshi = "kalshi"
    polymarket = "polymarket"


VenueColumn = Enum(Venue, name="venue_enum")


class ArbType(str, enum.Enum):
    cross_venue_yes = "cross_venue_yes"
    round_trip = "round_trip"


class PaperStatus(str, enum.Enum):
    open = "open"
    closed = "closed"


class KalshiMarket(Base):
    __tablename__ = "kalshi_markets"

    ticker: Mapped[str] = mapped_column(String(64), primary_key=True)
    title: Mapped[str] = mapped_column(Text, default="")
    event_ticker: Mapped[str] = mapped_column(String(64), default="")
    status: Mapped[str] = mapped_column(String(32), default="")
    yes_bid: Mapped[float | None] = mapped_column(Numeric(14, 8), nullable=True)
    yes_ask: Mapped[float | None] = mapped_column(Numeric(14, 8), nullable=True)
    volume: Mapped[float | None] = mapped_column(Numeric(24, 8), nullable=True)
    close_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class PolyMarket(Base):
    __tablename__ = "poly_markets"

    condition_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    question: Mapped[str] = mapped_column(Text, default="")
    slug: Mapped[str] = mapped_column(String(256), default="")
    token_yes: Mapped[str] = mapped_column(String(128), default="")
    volume_24h: Mapped[float | None] = mapped_column(Numeric(24, 8), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class MarketPair(Base):
    __tablename__ = "market_pairs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    kalshi_ticker: Mapped[str] = mapped_column(String(64), ForeignKey("kalshi_markets.ticker"))
    poly_condition_id: Mapped[str] = mapped_column(String(128), ForeignKey("poly_markets.condition_id"))
    match_score: Mapped[float] = mapped_column(Float, default=0.0)
    manual: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    kalshi: Mapped[KalshiMarket] = relationship()
    poly: Mapped[PolyMarket] = relationship()


class PriceTick(Base):
    __tablename__ = "price_ticks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    pair_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("market_pairs.id"), index=True)
    venue: Mapped[Venue] = mapped_column(VenueColumn)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    yes_bid: Mapped[float | None] = mapped_column(Numeric(14, 8), nullable=True)
    yes_ask: Mapped[float | None] = mapped_column(Numeric(14, 8), nullable=True)
    volume: Mapped[float | None] = mapped_column(Numeric(24, 8), nullable=True)


class Spread(Base):
    __tablename__ = "spreads"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    pair_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("market_pairs.id"), index=True)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    spread_pct: Mapped[float] = mapped_column(Float)
    arb_type: Mapped[ArbType] = mapped_column(Enum(ArbType, name="arb_type_enum"))
    best_edge: Mapped[float | None] = mapped_column(Float, nullable=True)
    meta: Mapped[dict | None] = mapped_column(JSON, nullable=True)


class PaperTrade(Base):
    __tablename__ = "paper_trades"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    pair_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("market_pairs.id"))
    status: Mapped[PaperStatus] = mapped_column(Enum(PaperStatus, name="paper_status_enum"), default=PaperStatus.open)
    legs: Mapped[dict] = mapped_column(JSON, default=dict)
    quantity: Mapped[float] = mapped_column(Numeric(20, 8), default=1)
    entry_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    mark_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    realized_pnl: Mapped[float | None] = mapped_column(Float, nullable=True)
    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class WhaleTrade(Base):
    __tablename__ = "whale_trades"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    venue: Mapped[Venue] = mapped_column(VenueColumn)
    external_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    market_ref: Mapped[str] = mapped_column(String(256))
    side: Mapped[str] = mapped_column(String(16), default="")
    size_usd: Mapped[float] = mapped_column(Float)
    price: Mapped[float | None] = mapped_column(Float, nullable=True)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    raw: Mapped[dict | None] = mapped_column(JSON, nullable=True)

"""Portable test mappings; production persistence is PostgreSQL with migrations."""

from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.engine import Dialect
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.types import TypeDecorator


class UTCDateTime(TypeDecorator[datetime]):
    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, value: datetime | None, dialect: Dialect) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("Timezone-aware timestamps required")
        return value.astimezone(UTC)

    def process_result_value(self, value: datetime | None, dialect: Dialect) -> datetime | None:
        if value is None:
            return None
        return value.astimezone(UTC) if value.tzinfo is not None else value.replace(tzinfo=UTC)


class Base(DeclarativeBase):
    pass


class Security(Base):
    __tablename__ = "research_securities"
    __table_args__ = (
        UniqueConstraint("exchange", "ticker", name="uq_security_listing"),
        CheckConstraint("asset_type = 'equity'", name="ck_security_equity"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    ticker: Mapped[str] = mapped_column(String(32))
    exchange: Mapped[str] = mapped_column(String(32))
    name: Mapped[str] = mapped_column(String(200))
    currency: Mapped[str] = mapped_column(String(3))
    country: Mapped[str] = mapped_column(String(2))
    sector: Mapped[str | None] = mapped_column(String(200))
    industry: Mapped[str | None] = mapped_column(String(200))
    asset_type: Mapped[str] = mapped_column(String(20), default="equity")
    isin: Mapped[str | None] = mapped_column(String(12))
    figi: Mapped[str | None] = mapped_column(String(12))
    created_at: Mapped[datetime] = mapped_column(UTCDateTime())
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime())


class Observation(Base):
    __tablename__ = "research_observations"
    __table_args__ = (
        UniqueConstraint("source", "source_record_id", name="uq_observation_source_record"),
        UniqueConstraint("version_sha256", name="uq_observation_publication"),
        CheckConstraint(
            "reported_at <= fetched_at AND fetched_at <= recorded_at",
            name="ck_observation_availability",
        ),
        CheckConstraint(
            "period_start IS NULL OR period_start <= period_end", name="ck_observation_period"
        ),
        CheckConstraint("unit IN ('currency','ratio','fraction')", name="ck_observation_unit"),
        CheckConstraint(
            "period_kind IN ('instant','quarter','annual','ttm','estimate')",
            name="ck_observation_period_kind",
        ),
        CheckConstraint(
            "(unit = 'currency' AND currency IS NOT NULL) OR "
            "(unit <> 'currency' AND currency IS NULL)",
            name="ck_observation_currency",
        ),
        Index("ix_observation_as_of", "security_id", "reported_at", "recorded_at"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    security_id: Mapped[UUID] = mapped_column(ForeignKey("research_securities.id"))
    metric: Mapped[str] = mapped_column(String(200))
    value: Mapped[Decimal] = mapped_column(Numeric(30, 10))
    unit: Mapped[str] = mapped_column(String(20))
    currency: Mapped[str | None] = mapped_column(String(3))
    period_start: Mapped[date | None] = mapped_column(Date)
    period_end: Mapped[date] = mapped_column(Date)
    period_kind: Mapped[str] = mapped_column(String(20))
    reported_at: Mapped[datetime] = mapped_column(UTCDateTime())
    fetched_at: Mapped[datetime] = mapped_column(UTCDateTime())
    recorded_at: Mapped[datetime] = mapped_column(UTCDateTime())
    source: Mapped[str] = mapped_column(String(200))
    source_record_id: Mapped[str] = mapped_column(String(200))
    source_document: Mapped[str] = mapped_column(String(1000))
    basis: Mapped[str] = mapped_column(String(200))
    content_sha256: Mapped[str] = mapped_column(String(64))
    version_sha256: Mapped[str] = mapped_column(String(64))

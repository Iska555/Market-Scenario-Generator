"""Immutable ledger storage; portable tests preserve decimal values exactly."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import CheckConstraint, ForeignKey, Index, Numeric, String, UniqueConstraint
from sqlalchemy.engine import Dialect
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import TypeDecorator, TypeEngine

from src.research.tables import Base, UTCDateTime


class ExactDecimal(TypeDecorator[Decimal]):
    impl = Numeric(30, 10)
    cache_ok = True

    def load_dialect_impl(self, dialect: Dialect) -> TypeEngine:
        return dialect.type_descriptor(String(64) if dialect.name == "sqlite" else Numeric(30, 10))

    def process_bind_param(self, value: Decimal | None, dialect: Dialect) -> Decimal | str | None:
        return str(value) if value is not None and dialect.name == "sqlite" else value

    def process_result_value(self, value: Decimal | str | None, dialect: Dialect) -> Decimal | None:
        return Decimal(value) if value is not None else None


class Portfolio(Base):
    __tablename__ = "accounting_portfolios"
    id: Mapped[UUID] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    base_currency: Mapped[str] = mapped_column(String(3))
    broker: Mapped[str] = mapped_column(String(200))
    account_label: Mapped[str] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(UTCDateTime())


class Transaction(Base):
    __tablename__ = "accounting_transactions"
    __table_args__ = (
        UniqueConstraint("portfolio_id", "sequence", name="uq_ledger_sequence"),
        UniqueConstraint(
            "portfolio_id", "source", "external_reference", name="uq_ledger_reference"
        ),
        UniqueConstraint("reverses_id", name="uq_ledger_reversal"),
        CheckConstraint("sequence > 0", name="ck_ledger_sequence"),
        CheckConstraint(
            "type IN ('BUY','SELL','DIVIDEND','FEE','DEPOSIT','WITHDRAWAL',"
            "'FX_CONVERSION','REVERSAL')",
            name="ck_ledger_type",
        ),
        Index("ix_ledger_replay", "portfolio_id", "effective_at", "recorded_at"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True)
    portfolio_id: Mapped[UUID] = mapped_column(ForeignKey("accounting_portfolios.id"))
    sequence: Mapped[int]
    type: Mapped[str] = mapped_column(String(20))
    effective_at: Mapped[datetime] = mapped_column(UTCDateTime())
    recorded_at: Mapped[datetime] = mapped_column(UTCDateTime())
    currency: Mapped[str] = mapped_column(String(3))
    security_id: Mapped[UUID | None] = mapped_column(ForeignKey("research_securities.id"))
    quantity: Mapped[Decimal | None] = mapped_column(ExactDecimal())
    price: Mapped[Decimal | None] = mapped_column(ExactDecimal())
    amount: Mapped[Decimal | None] = mapped_column(ExactDecimal())
    fees: Mapped[Decimal] = mapped_column(ExactDecimal())
    to_currency: Mapped[str | None] = mapped_column(String(3))
    to_amount: Mapped[Decimal | None] = mapped_column(ExactDecimal())
    fx_rate: Mapped[Decimal | None] = mapped_column(ExactDecimal())
    reverses_id: Mapped[UUID | None] = mapped_column(ForeignKey("accounting_transactions.id"))
    source: Mapped[str] = mapped_column(String(200))
    external_reference: Mapped[str] = mapped_column(String(200))
    note: Mapped[str] = mapped_column(String(2000))
    content_sha256: Mapped[str] = mapped_column(String(64))

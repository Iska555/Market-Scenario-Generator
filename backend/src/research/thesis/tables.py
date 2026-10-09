"""Append-only thesis records; PostgreSQL migration enforces immutability."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from src.research.tables import Base, UTCDateTime


class Thesis(Base):
    __tablename__ = "research_theses"
    __table_args__ = (
        UniqueConstraint("id", "security_id", name="uq_thesis_security"),
        Index("ix_thesis_security", "security_id", "created_at"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    security_id: Mapped[UUID] = mapped_column(ForeignKey("research_securities.id"))
    created_at: Mapped[datetime] = mapped_column(UTCDateTime())


class ThesisRevision(Base):
    __tablename__ = "research_thesis_revisions"
    __table_args__ = (
        ForeignKeyConstraint(
            ["thesis_id", "security_id"],
            ["research_theses.id", "research_theses.security_id"],
            name="fk_revision_thesis_security",
        ),
        UniqueConstraint("thesis_id", "revision", name="uq_thesis_revision_number"),
        UniqueConstraint("thesis_id", "id", name="uq_thesis_revision_identity"),
        CheckConstraint("revision >= 1", name="ck_thesis_revision_number"),
        CheckConstraint(
            "status IN ('draft','active','invalidated','closed')", name="ck_thesis_status"
        ),
        CheckConstraint("conviction IN ('low','medium','high')", name="ck_thesis_conviction"),
        CheckConstraint("horizon_months > 0 AND horizon_months <= 1200", name="ck_thesis_horizon"),
        CheckConstraint(
            "(target_low IS NULL AND target_high IS NULL) OR "
            "(target_low IS NOT NULL AND target_high IS NOT NULL "
            "AND target_low > 0 AND target_high >= target_low)",
            name="ck_thesis_target_range",
        ),
        CheckConstraint(
            "required_return IS NULL OR required_return > -1", name="ck_thesis_required_return"
        ),
        Index("ix_thesis_revision_as_of", "thesis_id", "created_at"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    thesis_id: Mapped[UUID] = mapped_column()
    security_id: Mapped[UUID] = mapped_column()
    revision: Mapped[int] = mapped_column()
    created_at: Mapped[datetime] = mapped_column(UTCDateTime())
    ticker: Mapped[str] = mapped_column(String(32))
    exchange: Mapped[str] = mapped_column(String(32))
    status: Mapped[str] = mapped_column(String(20))
    horizon_months: Mapped[int] = mapped_column()
    conviction: Mapped[str] = mapped_column(String(10))
    valuation_currency: Mapped[str] = mapped_column(String(3))
    target_low: Mapped[Decimal | None] = mapped_column(Numeric(30, 10))
    target_high: Mapped[Decimal | None] = mapped_column(Numeric(30, 10))
    required_return: Mapped[Decimal | None] = mapped_column(Numeric(20, 10))
    variant_perception: Mapped[str] = mapped_column(String(10000))
    business_quality: Mapped[str] = mapped_column(String(10000))
    earnings_drivers: Mapped[str] = mapped_column(String(10000))
    catalysts: Mapped[str] = mapped_column(String(10000))
    risks: Mapped[str] = mapped_column(String(10000))
    bear_case: Mapped[str] = mapped_column(String(10000))
    base_case: Mapped[str] = mapped_column(String(10000))
    bull_case: Mapped[str] = mapped_column(String(10000))
    invalidation_conditions: Mapped[str] = mapped_column(String(10000))
    notes: Mapped[str] = mapped_column(String(10000))


class ThesisReview(Base):
    __tablename__ = "research_thesis_reviews"
    __table_args__ = (
        ForeignKeyConstraint(
            ["thesis_id", "revision_id"],
            ["research_thesis_revisions.thesis_id", "research_thesis_revisions.id"],
            name="fk_review_thesis_revision",
        ),
        CheckConstraint(
            "decision IN ('BUY_MORE','HOLD','REDUCE','EXIT','WATCH')",
            name="ck_thesis_review_decision",
        ),
        CheckConstraint(
            "current_price IS NULL OR current_price > 0", name="ck_thesis_review_price"
        ),
        CheckConstraint(
            "updated_expected_return IS NULL OR updated_expected_return > -1",
            name="ck_thesis_review_return",
        ),
        Index("ix_thesis_review_history", "thesis_id", "reviewed_at"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    thesis_id: Mapped[UUID] = mapped_column()
    revision_id: Mapped[UUID] = mapped_column()
    reviewed_at: Mapped[datetime] = mapped_column(UTCDateTime())
    decision: Mapped[str] = mapped_column(String(10))
    current_price: Mapped[Decimal | None] = mapped_column(Numeric(30, 10))
    valuation_currency: Mapped[str] = mapped_column(String(3))
    what_changed: Mapped[str] = mapped_column(String(10000))
    what_was_correct: Mapped[str] = mapped_column(String(10000))
    what_was_wrong: Mapped[str] = mapped_column(String(10000))
    new_information: Mapped[str] = mapped_column(String(10000))
    thesis_still_valid: Mapped[bool] = mapped_column()
    updated_expected_return: Mapped[Decimal | None] = mapped_column(Numeric(20, 10))
    notes: Mapped[str] = mapped_column(String(10000))

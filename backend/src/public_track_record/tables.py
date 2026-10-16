"""One immutable identity per newly created portfolio; absence means unclassified."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import CheckConstraint, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from src.research.tables import Base, UTCDateTime


class PortfolioIdentityRow(Base):
    __tablename__ = "portfolio_identities"
    __table_args__ = (CheckConstraint("mode IN ('demo','paper','real')", name="ck_portfolio_mode"),)
    portfolio_id: Mapped[UUID] = mapped_column(
        ForeignKey("accounting_portfolios.id"), primary_key=True
    )
    mode: Mapped[str] = mapped_column(String(10))
    recorded_at: Mapped[datetime] = mapped_column(UTCDateTime())

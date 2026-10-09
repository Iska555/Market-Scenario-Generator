"""Atomic append and replay; source references provide idempotency."""

import hashlib
import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.accounting.contracts import (
    Batch,
    BatchResult,
    History,
    LedgerState,
    PortfolioCreate,
    PortfolioRead,
    TransactionCreate,
    TransactionRead,
)
from src.accounting.ledger import replay
from src.accounting.tables import Portfolio, Transaction
from src.research.repository import ResearchConflict, ResearchNotFound
from src.research.tables import Security

MAX_ROWS = 20_000


def fingerprint(data: TransactionCreate) -> str:
    payload = data.model_dump(mode="json")
    payload["effective_at"] = data.effective_at.astimezone(UTC).isoformat()
    for name in ("quantity", "price", "amount", "fees", "to_amount", "fx_rate"):
        value = getattr(data, name)
        if isinstance(value, Decimal):
            text = format(value, "f")
            payload[name] = text.rstrip("0").rstrip(".") if "." in text else text
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


class LedgerRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def portfolio(self, portfolio_id: UUID) -> Portfolio:
        # All ledger reads/writes take this lock for a coherent snapshot across queries.
        row = self.session.scalar(
            select(Portfolio).where(Portfolio.id == portfolio_id).with_for_update()
        )
        if row is None:
            raise ResearchNotFound("Portfolio not found")
        return row

    def rows(self, portfolio_id: UUID) -> list[TransactionRead]:
        rows = self.session.scalars(
            select(Transaction)
            .where(Transaction.portfolio_id == portfolio_id)
            .order_by(Transaction.sequence)
            .limit(MAX_ROWS + 1)
        ).all()
        if len(rows) > MAX_ROWS:
            raise ValueError("Portfolio exceeds supported ledger capacity")
        return [TransactionRead.model_validate(row) for row in rows]

    def read_portfolio(self, row: Portfolio) -> PortfolioRead:
        version = self.session.scalar(
            select(Transaction.sequence)
            .where(Transaction.portfolio_id == row.id)
            .order_by(Transaction.sequence.desc())
            .limit(1)
        )
        return PortfolioRead(
            id=row.id,
            name=row.name,
            base_currency=row.base_currency,
            broker=row.broker,
            account_label=row.account_label,
            created_at=row.created_at,
            version=version or 0,
        )

    def portfolios(self) -> list[PortfolioRead]:
        rows = self.session.scalars(
            select(Portfolio).order_by(Portfolio.created_at, Portfolio.id)
        ).all()
        return [self.read_portfolio(row) for row in rows]

    def create_portfolio(self, data: PortfolioCreate) -> PortfolioRead:
        existing = self.session.get(Portfolio, data.id)
        if existing is not None:
            if any(getattr(existing, key) != value for key, value in data.model_dump().items()):
                raise ResearchConflict("Portfolio ID already has different attributes")
            return self.read_portfolio(existing)
        try:
            with self.session.begin_nested():
                row = Portfolio(**data.model_dump(), created_at=datetime.now(UTC))
                self.session.add(row)
                self.session.flush()
        except IntegrityError as exc:
            raise ResearchConflict("Concurrent portfolio creation; retry the same ID") from exc
        return self.read_portfolio(row)

    def state(
        self, portfolio_id: UUID, as_of: datetime | None = None, known_at: datetime | None = None
    ) -> LedgerState:
        portfolio = self.portfolio(portfolio_id)
        now = datetime.now(UTC)
        as_of, known_at = as_of or now, known_at or now
        if as_of > now or known_at > now:
            raise ValueError("Future ledger cutoffs are unsupported")
        return replay(
            portfolio_id, portfolio.base_currency, self.rows(portfolio_id), as_of, known_at
        )

    def history(self, portfolio_id: UUID, limit: int, offset: int) -> History:
        self.portfolio(portfolio_id)
        rows = self.rows(portfolio_id)
        return History(
            transactions=list(reversed(rows))[offset : offset + limit],
            version=rows[-1].sequence if rows else 0,
            total=len(rows),
        )

    def evaluate(self, portfolio_id: UUID, batch: Batch, *, save: bool) -> BatchResult:
        portfolio = self.portfolio(portfolio_id)
        original = self.rows(portfolio_id)
        rows = list(original)
        by_reference = {(r.source, r.external_reference): r for r in rows}
        by_id = {r.id: r for r in rows}
        canceled = {r.reverses_id for r in rows if r.type == "REVERSAL"}
        version = rows[-1].sequence if rows else 0
        now = datetime.now(UTC)
        if rows:
            now = max(now, rows[-1].recorded_at + timedelta(microseconds=1))
        new: list[TransactionRead] = []
        resolved: list[TransactionRead] = []
        duplicates = 0
        for data in batch.transactions:
            content_hash = fingerprint(data)
            old = by_reference.get((data.source, data.external_reference))
            if old is not None:
                if old.content_sha256 != content_hash:
                    raise ResearchConflict(
                        "Source/reference reused with different transaction content"
                    )
                duplicates += 1
                resolved.append(old)
                continue
            if data.effective_at > now:
                raise ValueError("Future-effective transactions are unsupported")
            if data.security_id is not None:
                security = self.session.get(Security, data.security_id, populate_existing=True)
                if security is None:
                    raise ResearchNotFound("Security not found")
                if security.asset_type != "equity":
                    raise ValueError("Only registered equities are supported")
                if data.type in ("BUY", "SELL") and security.currency != data.currency:
                    raise ValueError("Trade currency must match registered security currency")
            if data.type == "REVERSAL":
                target = by_id.get(data.reverses_id)  # type: ignore[arg-type]
                if target is None or target.type == "REVERSAL" or target.id in canceled:
                    raise ValueError("Reversal requires an active original in this portfolio")
                if target.effective_at != data.effective_at or target.currency != data.currency:
                    raise ValueError(
                        "Reversal must match original effective timestamp and currency"
                    )
                canceled.add(target.id)
            item = TransactionRead(
                **data.model_dump(),
                id=uuid4(),
                portfolio_id=portfolio_id,
                sequence=version + len(new) + 1,
                recorded_at=now,
                content_sha256=content_hash,
            )
            new.append(item)
            rows.append(item)
            resolved.append(item)
            by_reference[(data.source, data.external_reference)] = item
            by_id[item.id] = item
        if new and batch.expected_version != version:
            raise ResearchConflict("Ledger changed; reload and preview the batch again")
        if len(rows) > MAX_ROWS:
            raise ValueError("Portfolio exceeds supported ledger capacity")
        result_state = replay(portfolio_id, portfolio.base_currency, rows, now, now)
        if save and new:
            try:
                with self.session.begin_nested():
                    for item in new:
                        self.session.add(Transaction(**item.model_dump()))
                        self.session.flush()
            except IntegrityError as exc:
                raise ResearchConflict("Concurrent ledger append; reload and retry") from exc
        return BatchResult(
            version=version + len(new),
            inserted=len(new),
            duplicates=duplicates,
            transactions=resolved,
            state=result_state,
        )

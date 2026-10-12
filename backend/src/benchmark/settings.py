"""Append-only identity choices, independent of ledger versions and market levels."""

from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import JSON, CheckConstraint, ForeignKey, String, UniqueConstraint, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Mapped, mapped_column

from src.accounting.repository import LedgerRepository
from src.benchmark.contracts import BenchmarkIdentity, Selection, SettingCreate, SettingsHistory
from src.performance.identity import digest
from src.research.repository import ResearchConflict
from src.research.tables import Base, UTCDateTime


class BenchmarkSetting(Base):
    __tablename__ = "portfolio_benchmark_settings"
    __table_args__ = (
        UniqueConstraint("portfolio_id", "revision", name="uq_benchmark_setting_revision"),
        CheckConstraint("revision > 0", name="ck_benchmark_setting_revision"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True)
    portfolio_id: Mapped[UUID] = mapped_column(ForeignKey("accounting_portfolios.id"))
    revision: Mapped[int]
    recorded_at: Mapped[datetime] = mapped_column(UTCDateTime())
    identity: Mapped[dict | None] = mapped_column(JSON(none_as_null=True))
    reason: Mapped[str] = mapped_column(String(2000))
    content_sha256: Mapped[str] = mapped_column(String(64))


def selection_hash(selection: Selection) -> str:
    data = selection.model_dump(mode="json", exclude={"content_sha256"})
    data["recorded_at"] = selection.recorded_at.astimezone(UTC).isoformat()
    return digest(data)


def latest(repository: LedgerRepository, portfolio_id: UUID) -> Selection | None:
    row = repository.session.scalar(
        select(BenchmarkSetting)
        .where(BenchmarkSetting.portfolio_id == portfolio_id)
        .order_by(BenchmarkSetting.revision.desc())
        .limit(1)
    )
    return Selection.model_validate(row) if row else None


def history(
    repository: LedgerRepository, portfolio_id: UUID, limit: int, offset: int
) -> SettingsHistory:
    repository.portfolio(portfolio_id)
    current = latest(repository, portfolio_id)
    rows = repository.session.scalars(
        select(BenchmarkSetting)
        .where(BenchmarkSetting.portfolio_id == portfolio_id)
        .order_by(BenchmarkSetting.revision.desc())
        .limit(limit)
        .offset(offset)
    )
    revision = current.revision if current else 0
    return SettingsHistory(
        revision=revision,
        total=revision,
        latest=current,
        records=[Selection.model_validate(row) for row in rows],
    )


def append(repository: LedgerRepository, portfolio_id: UUID, data: SettingCreate) -> Selection:
    portfolio = repository.portfolio(portfolio_id)
    existing = repository.session.get(BenchmarkSetting, data.id)
    if existing:
        old = Selection.model_validate(existing)
        if (
            old.portfolio_id != portfolio_id
            or old.identity != data.identity
            or old.reason != data.reason
        ):
            raise ResearchConflict("Setting ID already has different content")
        return old
    current = latest(repository, portfolio_id)
    revision = current.revision if current else 0
    if revision != data.expected_revision:
        raise ResearchConflict("Benchmark setting changed; reload and review again")
    now = datetime.now(UTC)
    if current:
        now = max(now, current.recorded_at + timedelta(microseconds=1))
    if data.identity:
        if data.identity.currency != portfolio.base_currency:
            raise ValueError("Benchmark setting currency must match the portfolio")
        if data.identity.retrieved_at > now:
            raise ValueError("Benchmark setting provenance cannot be in the future")
    record = Selection(
        id=data.id,
        portfolio_id=portfolio_id,
        revision=revision + 1,
        recorded_at=now,
        identity=data.identity,
        reason=data.reason,
        content_sha256="0" * 64,
    )
    record.content_sha256 = selection_hash(record)
    try:
        with repository.session.begin_nested():
            repository.session.add(
                BenchmarkSetting(
                    **record.model_dump(mode="python", exclude={"identity"}),
                    identity=data.identity.model_dump(mode="json") if data.identity else None,
                )
            )
            repository.session.flush()
    except IntegrityError as exc:
        raise ResearchConflict("Concurrent benchmark setting write; reload and retry") from exc
    return record


def selected(
    repository: LedgerRepository,
    portfolio_id: UUID,
    revision: int | None,
    identity: BenchmarkIdentity,
    known_at: datetime,
) -> Selection | None:
    if revision is None:
        return None
    current = latest(repository, portfolio_id)
    if current is None or current.revision != revision or current.identity is None:
        raise ResearchConflict(
            "Saved benchmark setting changed or cleared; reload and review again"
        )
    if current.identity != identity:
        raise ValueError("Supplied benchmark identity differs from the selected setting")
    if current.recorded_at > known_at:
        raise ValueError("Saved benchmark setting exceeds the knowledge cutoff")
    return current

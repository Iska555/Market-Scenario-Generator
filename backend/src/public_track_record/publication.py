"""Explicit owner publication; immutable content and append-only public lifecycle."""

from datetime import UTC, datetime
from typing import Literal
from uuid import UUID

from pydantic import Field
from sqlalchemy import JSON, CheckConstraint, ForeignKey, Integer, String, select, text
from sqlalchemy.orm import Mapped, mapped_column

from src.accounting.contracts import Contract
from src.accounting.repository import LedgerRepository
from src.performance.identity import digest
from src.public_track_record.snapshot import PublicSnapshot, SnapshotEnvelope, project_demo
from src.research.repository import ResearchConflict, ResearchNotFound
from src.research.tables import Base, UTCDateTime


class ChannelRow(Base):
    __tablename__ = "publication_channels"
    id: Mapped[str] = mapped_column(String(20), primary_key=True)


class PreviewRow(Base):
    __tablename__ = "publication_previews"
    id: Mapped[UUID] = mapped_column(primary_key=True)
    portfolio_id: Mapped[UUID] = mapped_column(ForeignKey("portfolio_identities.portfolio_id"))
    request: Mapped[dict] = mapped_column(JSON())
    head: Mapped[int] = mapped_column(Integer())
    snapshot: Mapped[dict] = mapped_column(JSON())
    content_sha256: Mapped[str] = mapped_column(String(64))


class EventRow(Base):
    __tablename__ = "publication_events"
    __table_args__ = (
        CheckConstraint("action IN ('publish','withdraw')", name="ck_publication_action"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True)
    sequence: Mapped[int] = mapped_column(Integer(), unique=True)
    action: Mapped[str] = mapped_column(String(10))
    request: Mapped[dict] = mapped_column(JSON())
    preview_id: Mapped[UUID | None] = mapped_column(ForeignKey("publication_previews.id"))
    recorded_at: Mapped[datetime] = mapped_column(UTCDateTime())


class PreviewIntent(Contract):
    id: UUID
    portfolio_id: UUID
    selected_research: list[Literal["harbor", "orchard"]] = Field(min_length=0, max_length=2)


class PublishIntent(Contract):
    id: UUID
    preview_id: UUID
    correction_of: UUID | None = None
    public_reason: str | None = Field(default=None, min_length=1, max_length=500)


class WithdrawIntent(Contract):
    id: UUID
    expected_sequence: int = Field(ge=0)
    public_reason: str = Field(min_length=1, max_length=500)


class OwnerPreview(Contract):
    id: UUID
    expected_sequence: int
    envelope: SnapshotEnvelope


def lock_channel(repository: LedgerRepository) -> None:
    row = repository.session.scalar(
        select(ChannelRow).where(ChannelRow.id == "demo").with_for_update()
    )
    if row is None:
        raise ResearchConflict("Publication channel migration is required")


def events(repository: LedgerRepository) -> list[EventRow]:
    return list(repository.session.scalars(select(EventRow).order_by(EventRow.sequence)))


def lock_sources(repository: LedgerRepository) -> None:
    # A small owner-only fixture: SHARE blocks source writes across all read tables
    # for this transaction. No mixed statement snapshots or concurrent thesis edits.
    if repository.session.get_bind().dialect.name == "postgresql":
        repository.session.execute(
            text("""LOCK TABLE accounting_portfolios,
            accounting_transactions, portfolio_identities, demo_load_receipts,
            research_securities, research_theses, research_thesis_revisions,
            research_thesis_reviews IN SHARE MODE""")
        )


def preview(repository: LedgerRepository, intent: PreviewIntent) -> OwnerPreview:
    lock_channel(repository)
    saved = repository.session.get(PreviewRow, intent.id)
    body = intent.model_dump(mode="json")
    if saved is not None:
        if saved.request != body:
            raise ResearchConflict("Preview identity was already used for another request")
    else:
        repository.portfolio(intent.portfolio_id)
        lock_sources(repository)
        snapshot = project_demo(repository, intent.portfolio_id, list(intent.selected_research))
        saved = PreviewRow(
            id=intent.id,
            portfolio_id=intent.portfolio_id,
            request=body,
            head=len(events(repository)),
            snapshot=snapshot.model_dump(mode="json"),
            content_sha256=digest(snapshot.model_dump(mode="json")),
        )
        repository.session.add(saved)
        repository.session.flush()
    return OwnerPreview(
        id=saved.id,
        expected_sequence=saved.head,
        envelope=SnapshotEnvelope(
            status="local_preview",
            version=str(saved.id),
            content_sha256=saved.content_sha256,
            published_at=None,
            snapshot=PublicSnapshot.model_validate(saved.snapshot),
        ),
    )


def as_envelope(repository: LedgerRepository, event: EventRow) -> SnapshotEnvelope:
    row = repository.session.get(PreviewRow, event.preview_id)
    if row is None:
        raise ResearchNotFound("Published snapshot is unavailable")
    snapshot = PublicSnapshot.model_validate(row.snapshot)
    if digest(snapshot.model_dump(mode="json")) != row.content_sha256:
        raise ResearchConflict("Published snapshot integrity check failed")
    return SnapshotEnvelope(
        status="published",
        version=str(event.id),
        content_sha256=row.content_sha256,
        published_at=event.recorded_at,
        correction_of=event.request.get("correction_of"),
        correction_reason=event.request.get("public_reason"),
        snapshot=snapshot,
    )


def publish(repository: LedgerRepository, intent: PublishIntent) -> SnapshotEnvelope:
    lock_channel(repository)
    body = intent.model_dump(mode="json")
    existing = repository.session.get(EventRow, intent.id)
    if existing is not None:
        if existing.action != "publish" or existing.request != body:
            raise ResearchConflict("Publication identity was already used for another request")
        return as_envelope(repository, existing)
    saved = repository.session.get(PreviewRow, intent.preview_id)
    if saved is None:
        raise ResearchNotFound("Owner preview not found")
    history = events(repository)
    if len(history) != saved.head:
        raise ResearchConflict("Publication history changed; create and review a fresh preview")
    previous = next((event for event in reversed(history) if event.action == "publish"), None)
    if previous is None:
        if intent.correction_of is not None or intent.public_reason is not None:
            raise ValueError("First publication cannot correct a prior version")
    else:
        if intent.correction_of != previous.id or not (intent.public_reason or "").strip():
            raise ValueError(
                "A new version must identify the previous version and disclose a public reason"
            )
        previous_preview = repository.session.get(PreviewRow, previous.preview_id)
        if previous_preview is None or previous_preview.portfolio_id != saved.portfolio_id:
            raise ResearchConflict("Public versions must retain the same isolated demo identity")
    repository.portfolio(saved.portfolio_id)
    lock_sources(repository)
    try:
        current = project_demo(repository, saved.portfolio_id, saved.request["selected_research"])
    except (ValueError, ResearchConflict) as exc:
        raise ResearchConflict("Demo source changed; create and review a fresh preview") from exc
    current = current.model_copy(
        update={"snapshot_at": PublicSnapshot.model_validate(saved.snapshot).snapshot_at}
    )
    if digest(current.model_dump(mode="json")) != saved.content_sha256:
        raise ResearchConflict("Demo source or calculation code changed; create a fresh preview")
    event = EventRow(
        id=intent.id,
        sequence=len(history) + 1,
        action="publish",
        request=body,
        preview_id=saved.id,
        recorded_at=datetime.now(UTC),
    )
    repository.session.add(event)
    repository.session.flush()
    return as_envelope(repository, event)


def withdraw(repository: LedgerRepository, intent: WithdrawIntent) -> dict:
    lock_channel(repository)
    body = intent.model_dump(mode="json")
    existing = repository.session.get(EventRow, intent.id)
    if existing is not None:
        if existing.action != "withdraw" or existing.request != body:
            raise ResearchConflict("Withdrawal identity was already used for another request")
        return public_history(repository)
    history = events(repository)
    if len(history) != intent.expected_sequence:
        raise ResearchConflict("Publication history changed; reload before withdrawal")
    if not history or history[-1].action != "publish":
        raise ResearchConflict("There is no currently available public version to withdraw")
    if not intent.public_reason.strip():
        raise ValueError("A public withdrawal reason is required")
    repository.session.add(
        EventRow(
            id=intent.id,
            sequence=len(history) + 1,
            action="withdraw",
            request=body,
            preview_id=None,
            recorded_at=datetime.now(UTC),
        )
    )
    repository.session.flush()
    return public_history(repository)


def public_history(repository: LedgerRepository) -> dict:
    history = events(repository)
    withdrawn_through = max((e.sequence for e in history if e.action == "withdraw"), default=0)
    return {
        "mode": "demo",
        "sequence": len(history),
        "events": [
            {
                "version": str(e.id) if e.action == "publish" else None,
                "action": e.action,
                "sequence": e.sequence,
                "recorded_at": e.recorded_at,
                "correction_of": e.request.get("correction_of"),
                "public_reason": e.request.get("public_reason"),
                "withdrawn": e.sequence <= withdrawn_through,
            }
            for e in history
        ],
    }


class PublicWithdrawn(Exception):
    pass


def read_public(repository: LedgerRepository, version: UUID | None = None) -> SnapshotEnvelope:
    history = events(repository)
    if not history:
        raise ResearchNotFound("No demonstration has been published")
    event = (
        history[-1]
        if version is None
        else next((e for e in history if e.id == version and e.action == "publish"), None)
    )
    if event is None:
        raise ResearchNotFound("Public version not found")
    boundary = max((e.sequence for e in history if e.action == "withdraw"), default=0)
    if event.action == "withdraw" or event.sequence <= boundary:
        raise PublicWithdrawn("Demonstration withdrawn from public availability")
    return as_envelope(repository, event)

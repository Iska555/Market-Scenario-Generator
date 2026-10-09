"""Serialized append operations preserve complete server-authored history."""

from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.research.repository import ResearchConflict, ResearchNotFound, aware
from src.research.tables import Security
from src.research.thesis.schemas import (
    ReviewCreate,
    ReviewRead,
    RevisionCreate,
    RevisionRead,
    ThesisCreate,
    ThesisRead,
)
from src.research.thesis.tables import Thesis, ThesisReview, ThesisRevision


class ThesisRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def _thesis(self, thesis_id: UUID, *, lock: bool = False) -> Thesis:
        query = select(Thesis).where(Thesis.id == thesis_id)
        if lock:
            query = query.with_for_update()
        row = self.session.scalar(query)
        if row is None:
            raise ResearchNotFound("Thesis not found")
        return row

    def _security(self, security_id: UUID) -> Security:
        row = self.session.get(Security, security_id, populate_existing=True)
        if row is None:
            raise ResearchNotFound("Security not found")
        return row

    def create_thesis(self, data: ThesisCreate) -> ThesisRead:
        security = self._security(data.security_id)
        now = datetime.now(UTC)
        row = Thesis(security_id=data.security_id, created_at=now)
        self.session.add(row)
        self.session.flush()
        revision = ThesisRevision(
            **data.model_dump(exclude={"security_id"}),
            thesis_id=row.id,
            security_id=row.security_id,
            revision=1,
            created_at=now,
            ticker=security.ticker,
            exchange=security.exchange,
        )
        self.session.add(revision)
        self.session.flush()
        self.session.refresh(revision)
        return self.get_thesis(row.id)

    def get_thesis(self, thesis_id: UUID, as_of: datetime | None = None) -> ThesisRead:
        row = self._thesis(thesis_id)
        query = select(ThesisRevision).where(ThesisRevision.thesis_id == thesis_id)
        if as_of is not None:
            query = query.where(ThesisRevision.created_at <= aware(as_of))
        latest = self.session.scalar(query.order_by(ThesisRevision.revision.desc()).limit(1))
        if latest is None:
            raise ResearchNotFound("Thesis not found at this cutoff")
        return ThesisRead(
            id=row.id,
            security_id=row.security_id,
            created_at=row.created_at,
            latest=RevisionRead.model_validate(latest),
        )

    def theses(
        self, security_id: UUID | None = None, limit: int = 100, offset: int = 0
    ) -> list[ThesisRead]:
        query = select(Thesis.id)
        if security_id is not None:
            query = query.where(Thesis.security_id == security_id)
        ids = self.session.scalars(
            query.order_by(Thesis.created_at.desc(), Thesis.id).limit(limit).offset(offset)
        ).all()
        return [self.get_thesis(thesis_id) for thesis_id in ids]

    def append_revision(self, thesis_id: UUID, data: RevisionCreate) -> RevisionRead:
        # The identity is immutable but its row lock serializes version allocation.
        row = self._thesis(thesis_id, lock=True)
        latest = self.get_thesis(thesis_id).latest
        if data.expected_revision != latest.revision:
            raise ResearchConflict("Thesis changed; reload the latest revision before saving")
        security = self._security(row.security_id)
        # Strict monotonicity even if server clock resolution repeats or moves backwards.
        now = max(datetime.now(UTC), latest.created_at + timedelta(microseconds=1))
        revision = ThesisRevision(
            **data.model_dump(exclude={"expected_revision"}),
            thesis_id=thesis_id,
            security_id=row.security_id,
            revision=latest.revision + 1,
            created_at=now,
            ticker=security.ticker,
            exchange=security.exchange,
        )
        try:
            with self.session.begin_nested():
                self.session.add(revision)
                self.session.flush()
        except IntegrityError as exc:
            raise ResearchConflict(
                "Thesis changed; reload the latest revision before saving"
            ) from exc
        self.session.refresh(revision)
        return RevisionRead.model_validate(revision)

    def revisions(self, thesis_id: UUID, limit: int = 100, offset: int = 0) -> list[RevisionRead]:
        self._thesis(thesis_id)
        rows = self.session.scalars(
            select(ThesisRevision)
            .where(ThesisRevision.thesis_id == thesis_id)
            .order_by(ThesisRevision.revision.desc())
            .limit(limit)
            .offset(offset)
        )
        return [RevisionRead.model_validate(row) for row in rows]

    def create_review(self, thesis_id: UUID, data: ReviewCreate) -> ReviewRead:
        self._thesis(thesis_id, lock=True)
        revision = self.session.get(ThesisRevision, data.revision_id)
        if revision is None or revision.thesis_id != thesis_id:
            raise ValueError("Review revision must belong to this thesis")
        previous = self.session.scalar(
            select(ThesisReview.reviewed_at)
            .where(ThesisReview.thesis_id == thesis_id)
            .order_by(ThesisReview.reviewed_at.desc())
            .limit(1)
        )
        now = max(datetime.now(UTC), revision.created_at)
        if previous is not None:
            now = max(now, previous + timedelta(microseconds=1))
        row = ThesisReview(**data.model_dump(), thesis_id=thesis_id, reviewed_at=now)
        self.session.add(row)
        self.session.flush()
        self.session.refresh(row)
        return ReviewRead.model_validate(row)

    def reviews(self, thesis_id: UUID, limit: int = 100, offset: int = 0) -> list[ReviewRead]:
        self._thesis(thesis_id)
        rows = self.session.scalars(
            select(ThesisReview)
            .where(ThesisReview.thesis_id == thesis_id)
            .order_by(ThesisReview.reviewed_at.desc(), ThesisReview.id)
            .limit(limit)
            .offset(offset)
        )
        return [ReviewRead.model_validate(row) for row in rows]

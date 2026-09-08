"""Transactional research persistence; no update/delete operation for published facts."""

import hashlib
import json
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.research.schemas import ObservationCreate, ObservationRead, SecurityCreate, SecurityRead
from src.research.tables import Observation, Security


class ResearchNotFound(ValueError):
    pass


class ResearchConflict(ValueError):
    pass


def aware(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("Timezone-aware cutoff required")
    return value.astimezone(UTC)


def fingerprint(security_id: UUID, fact: ObservationCreate) -> str:
    content = fact.model_dump(mode="json", exclude={"fetched_at"})
    # Equivalent decimal spellings must have identical import identity.
    content["value"] = (
        format(fact.value, "f").rstrip("0").rstrip(".")
        if "." in format(fact.value, "f")
        else format(fact.value, "f")
    )
    if fact.value == 0:
        content["value"] = "0"
    content["security_id"] = str(security_id)
    return hashlib.sha256(json.dumps(content, sort_keys=True).encode()).hexdigest()


def version_fingerprint(security_id: UUID, fact: ObservationCreate) -> str:
    fields = {
        "metric",
        "period_start",
        "period_end",
        "period_kind",
        "basis",
        "currency",
        "source",
        "reported_at",
    }
    content = fact.model_dump(mode="json", include=fields)
    content["security_id"] = str(security_id)
    return hashlib.sha256(json.dumps(content, sort_keys=True).encode()).hexdigest()


class ResearchRepository:
    """Callers own commit/rollback; batch savepoints also guarantee atomic rejection."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def create_security(self, data: SecurityCreate) -> SecurityRead:
        now = datetime.now(UTC)
        row = Security(**data.model_dump(), created_at=now, updated_at=now)
        try:
            with self.session.begin_nested():
                self.session.add(row)
                self.session.flush()
        except IntegrityError as exc:
            raise ResearchConflict("A security already uses this exchange/ticker") from exc
        return SecurityRead.model_validate(row)

    def _security(self, security_id: UUID) -> Security:
        row = self.session.get(Security, security_id)
        if row is None:
            raise ResearchNotFound("Security not found")
        return row

    def get_security(self, security_id: UUID) -> SecurityRead:
        return SecurityRead.model_validate(self._security(security_id))

    def securities(self, limit: int = 100, offset: int = 0) -> list[SecurityRead]:
        rows = self.session.scalars(
            select(Security)
            .order_by(Security.exchange, Security.ticker)
            .limit(limit)
            .offset(offset)
        )
        return [SecurityRead.model_validate(row) for row in rows]

    def update_security(self, security_id: UUID, data: SecurityCreate) -> SecurityRead:
        row = self._security(security_id)
        try:
            with self.session.begin_nested():
                for key, value in data.model_dump().items():
                    setattr(row, key, value)
                row.updated_at = datetime.now(UTC)
                self.session.flush()
        except IntegrityError as exc:
            raise ResearchConflict("A security already uses this exchange/ticker") from exc
        return SecurityRead.model_validate(row)

    def import_observations(
        self, security_id: UUID, facts: list[ObservationCreate]
    ) -> list[ObservationRead]:
        self._security(security_id)
        result = []
        now = datetime.now(UTC)
        try:
            with self.session.begin_nested():
                for fact in facts:
                    if fact.fetched_at > now:
                        raise ValueError("Fetched time cannot be in the future")
                    digest = fingerprint(security_id, fact)
                    row = self.session.scalar(
                        select(Observation).where(
                            Observation.source == fact.source,
                            Observation.source_record_id == fact.source_record_id,
                        )
                    )
                    if row is not None:
                        if row.content_sha256 != digest:
                            raise ResearchConflict(
                                "Source record ID already identifies different content"
                            )
                    else:
                        row = Observation(
                            **fact.model_dump(),
                            security_id=security_id,
                            recorded_at=now,
                            content_sha256=digest,
                            version_sha256=version_fingerprint(security_id, fact),
                        )
                        self.session.add(row)
                        self.session.flush()
                    result.append(ObservationRead.model_validate(row))
        except IntegrityError as exc:
            raise ResearchConflict("Conflicting source record; retry the immutable import") from exc
        return result

    def observations(
        self,
        security_id: UUID,
        as_of: datetime,
        *,
        known_at: datetime | None = None,
        source: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[ObservationRead]:
        self._security(security_id)
        conditions = [
            Observation.security_id == security_id,
            Observation.reported_at <= aware(as_of),
            Observation.recorded_at <= aware(known_at or datetime.now(UTC)),
        ]
        if source is not None:
            conditions.append(Observation.source == source)
        # Rank only eligible facts, so later restatements cannot leak backward.
        rank = (
            func.row_number()
            .over(
                partition_by=[
                    Observation.metric,
                    Observation.period_start,
                    Observation.period_end,
                    Observation.period_kind,
                    Observation.basis,
                    Observation.currency,
                    Observation.source,
                ],
                order_by=[
                    Observation.reported_at.desc(),
                    Observation.recorded_at.desc(),
                    Observation.id.desc(),
                ],
            )
            .label("revision_rank")
        )
        eligible = select(Observation.id, rank).where(*conditions).subquery()
        rows = self.session.scalars(
            select(Observation)
            .join(eligible, Observation.id == eligible.c.id)
            .where(eligible.c.revision_rank == 1)
            .order_by(
                Observation.period_end.desc(),
                Observation.metric,
                Observation.source,
                Observation.basis,
                Observation.id,
            )
            .limit(limit)
            .offset(offset)
        )
        return [ObservationRead.model_validate(row) for row in rows]

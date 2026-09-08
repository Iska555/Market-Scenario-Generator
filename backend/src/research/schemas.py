"""Immutable fact inputs: publication, observation period and system knowledge differ."""

from datetime import UTC, date
from decimal import Decimal
from typing import Annotated, Literal, Self
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, field_validator, model_validator

from src.research.metrics import METRICS

Text = Annotated[str, Field(min_length=1, max_length=200)]
Currency = Annotated[str, Field(pattern=r"^[A-Z]{3}$")]
PeriodKind = Literal["instant", "quarter", "annual", "ttm", "estimate"]
Unit = Literal["currency", "ratio", "fraction"]


class ResearchModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True, from_attributes=True)


class SecurityCreate(ResearchModel):
    ticker: Annotated[str, Field(min_length=1, max_length=32)]
    name: Text
    exchange: Annotated[str, Field(min_length=1, max_length=32)]
    currency: Currency
    country: Annotated[str, Field(pattern=r"^[A-Z]{2}$")]
    sector: Text | None = None
    industry: Text | None = None
    asset_type: Literal["equity"] = "equity"
    isin: Annotated[str, Field(pattern=r"^[A-Z]{2}[A-Z0-9]{9}[0-9]$")] | None = None
    figi: Annotated[str, Field(pattern=r"^[A-Z0-9]{12}$")] | None = None

    @field_validator("ticker", "exchange")
    @classmethod
    def normalize_label(cls, value: str) -> str:
        if any(c.isspace() for c in value):
            raise ValueError("Labels cannot contain whitespace")
        return value.upper()


class SecurityRead(SecurityCreate):
    id: UUID
    created_at: AwareDatetime
    updated_at: AwareDatetime


class ObservationCreate(ResearchModel):
    metric: Text
    value: Annotated[Decimal, Field(max_digits=30, decimal_places=10, allow_inf_nan=False)]
    unit: Unit
    currency: Currency | None = None
    period_start: date | None = None
    period_end: date
    period_kind: PeriodKind
    reported_at: AwareDatetime
    fetched_at: AwareDatetime
    source: Text
    source_record_id: Annotated[str, Field(min_length=1, max_length=200)]
    source_document: Annotated[str, Field(min_length=1, max_length=1000)]
    basis: Text

    @model_validator(mode="after")
    def coherent_fact(self) -> Self:
        definition = METRICS.get(self.metric)
        if definition is None or self.unit != definition.unit:
            raise ValueError("Unknown metric or unit does not match the metric catalogue")
        if (self.unit == "currency") != (self.currency is not None):
            raise ValueError("Currency is required only for monetary observations")
        self.reported_at = self.reported_at.astimezone(UTC)
        self.fetched_at = self.fetched_at.astimezone(UTC)
        if self.reported_at > self.fetched_at:
            raise ValueError("A fact cannot be fetched before it was published")
        if self.period_kind != "estimate" and self.period_end > self.reported_at.date():
            raise ValueError("Historical periods cannot end after publication")
        if self.period_start is not None and self.period_start > self.period_end:
            raise ValueError("Period start must not follow period end")
        if self.period_kind in ("quarter", "annual", "ttm") and self.period_start is None:
            raise ValueError("Duration observations require a period start")
        if self.period_kind == "instant" and self.period_start is not None:
            raise ValueError("Instant observations have no duration period start")
        if self.metric == "forward_pe" and self.period_kind != "estimate":
            raise ValueError("Forward P/E must be explicitly labeled an estimate")
        return self


class ObservationRead(ObservationCreate):
    id: UUID
    security_id: UUID
    recorded_at: AwareDatetime


class ObservationBatch(ResearchModel):
    observations: Annotated[list[ObservationCreate], Field(min_length=1, max_length=500)]


class ObservationPage(ResearchModel):
    items: list[ObservationRead]
    as_of: AwareDatetime
    known_at: AwareDatetime
    limit: int
    offset: int

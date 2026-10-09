"""Explicit owner judgments; rates are annual effective decimal fractions."""

from decimal import Decimal
from typing import Annotated, Literal, Self
from uuid import UUID

from pydantic import AwareDatetime, Field, StrictBool, model_validator

from src.research.schemas import Currency, ResearchModel

Narrative = Annotated[str, Field(max_length=10000)]
Price = Annotated[Decimal, Field(gt=0, max_digits=30, decimal_places=10, allow_inf_nan=False)]
AnnualRate = Annotated[Decimal, Field(gt=-1, max_digits=20, decimal_places=10, allow_inf_nan=False)]
SUBSTANTIVE_FIELDS = (
    "variant_perception",
    "business_quality",
    "earnings_drivers",
    "catalysts",
    "risks",
    "bear_case",
    "base_case",
    "bull_case",
    "invalidation_conditions",
)


class ThesisContent(ResearchModel):
    status: Literal["draft", "active", "invalidated", "closed"]
    horizon_months: Annotated[int, Field(gt=0, le=1200, strict=True)]
    conviction: Literal["low", "medium", "high"]
    valuation_currency: Currency
    target_low: Price | None = None
    target_high: Price | None = None
    required_return: AnnualRate | None = None
    variant_perception: Narrative = ""
    business_quality: Narrative = ""
    earnings_drivers: Narrative = ""
    catalysts: Narrative = ""
    risks: Narrative = ""
    bear_case: Narrative = ""
    base_case: Narrative = ""
    bull_case: Narrative = ""
    invalidation_conditions: Narrative = ""
    notes: Narrative = ""

    @model_validator(mode="after")
    def coherent_thesis(self) -> Self:
        if (self.target_low is None) != (self.target_high is None):
            raise ValueError("Target range requires both low and high values")
        if self.target_low is not None and self.target_high is not None:
            if self.target_low > self.target_high:
                raise ValueError("Target low must not exceed target high")
        if self.status == "active" and any(
            not getattr(self, field) for field in SUBSTANTIVE_FIELDS
        ):
            raise ValueError("Active theses require every substantive narrative section")
        return self


class ThesisCreate(ThesisContent):
    security_id: UUID


class RevisionCreate(ThesisContent):
    expected_revision: Annotated[int, Field(ge=1, le=2147483646, strict=True)]


class RevisionRead(ThesisContent):
    id: UUID
    thesis_id: UUID
    security_id: UUID
    revision: int
    created_at: AwareDatetime
    ticker: str
    exchange: str


class ThesisRead(ResearchModel):
    id: UUID
    security_id: UUID
    created_at: AwareDatetime
    latest: RevisionRead


class ReviewCreate(ResearchModel):
    revision_id: UUID
    decision: Literal["BUY_MORE", "HOLD", "REDUCE", "EXIT", "WATCH"]
    current_price: Price | None = None
    valuation_currency: Currency
    what_changed: Narrative = ""
    what_was_correct: Narrative = ""
    what_was_wrong: Narrative = ""
    new_information: Narrative = ""
    thesis_still_valid: StrictBool
    updated_expected_return: AnnualRate | None = None
    notes: Narrative = ""


class ReviewRead(ReviewCreate):
    id: UUID
    thesis_id: UUID
    reviewed_at: AwareDatetime

"""Additive identity contract; never embedded into historical replay reports."""

from typing import Literal, Self
from uuid import UUID

from pydantic import AwareDatetime, model_validator

from src.accounting.contracts import Contract, Currency, PortfolioRead, Text

PortfolioMode = Literal["demo", "paper", "real"]


class DemoCreate(Contract):
    id: UUID
    name: Text
    base_currency: Currency
    mode: Literal["demo"]


class PortfolioIdentity(Contract):
    mode: PortfolioMode | Literal["unclassified"]
    recorded_at: AwareDatetime | None
    publication_eligible: bool
    visibility: Literal["private"] = "private"
    broker_verified: Literal[False] = False

    @model_validator(mode="after")
    def consistent(self) -> Self:
        if self.publication_eligible != (self.mode == "demo"):
            raise ValueError("Only demo identities are publication candidates")
        if (self.recorded_at is None) != (self.mode == "unclassified"):
            raise ValueError("Classified identities require their actual recording timestamp")
        return self


class PortfolioContext(PortfolioRead):
    identity: PortfolioIdentity

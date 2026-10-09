"""Strict economic contracts; money and quantities serialize as decimal strings."""

from datetime import datetime
from decimal import Decimal, localcontext
from typing import Annotated, Literal, Self
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, BeforeValidator, ConfigDict, Field, model_validator

from src.accounting.precision import accounting_context


def exact_decimal(value: object) -> object:
    if isinstance(value, (float, bool)):
        raise ValueError("Supply an exact decimal string, not a float or boolean")
    return value


Currency = Annotated[str, Field(pattern=r"^[A-Z]{3}$")]
Positive = Annotated[
    Decimal, Field(gt=0, max_digits=30, decimal_places=10), BeforeValidator(exact_decimal)
]
Nonnegative = Annotated[
    Decimal, Field(ge=0, max_digits=30, decimal_places=10), BeforeValidator(exact_decimal)
]
Text = Annotated[str, Field(min_length=1, max_length=200)]
Kind = Literal[
    "BUY", "SELL", "DIVIDEND", "FEE", "DEPOSIT", "WITHDRAWAL", "FX_CONVERSION", "REVERSAL"
]


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True, str_strip_whitespace=True)


class PortfolioCreate(Contract):
    id: UUID
    name: Text
    base_currency: Currency
    broker: Text
    account_label: Text


class PortfolioRead(PortfolioCreate):
    created_at: datetime
    version: int


class TransactionCreate(Contract):
    type: Kind
    effective_at: AwareDatetime
    currency: Currency
    security_id: UUID | None = None
    quantity: Positive | None = None
    price: Nonnegative | None = None
    amount: Positive | None = None
    fees: Nonnegative = Decimal(0)
    to_currency: Currency | None = None
    to_amount: Positive | None = None
    fx_rate: Positive | None = None
    reverses_id: UUID | None = None
    source: Text
    external_reference: Text
    note: str = Field(default="", max_length=2000)

    @model_validator(mode="after")
    def coherent(self) -> Self:
        fields = {
            "security_id",
            "quantity",
            "price",
            "amount",
            "to_currency",
            "to_amount",
            "fx_rate",
            "reverses_id",
        }
        required: set[str]
        if self.type in ("BUY", "SELL"):
            required = {"security_id", "quantity", "price"}
        elif self.type == "FX_CONVERSION":
            required = {"amount", "to_currency", "to_amount", "fx_rate"}
        elif self.type == "REVERSAL":
            required = {"reverses_id"}
        elif self.type == "DIVIDEND":
            required = {"amount", "security_id"}
        else:
            required = {"amount"}
        present = {field for field in fields if getattr(self, field) is not None}
        if present != required:
            raise ValueError(f"{self.type} requires only {', '.join(sorted(required))}")
        if self.type not in ("BUY", "SELL", "FX_CONVERSION") and self.fees != 0:
            raise ValueError("Separate fees are allowed only for trades and FX")
        if self.type == "BUY" and self.price == 0:
            raise ValueError("BUY price must be positive")
        if self.type == "FX_CONVERSION":
            assert self.amount is not None and self.fx_rate is not None
            with localcontext(accounting_context()):
                if (
                    self.currency == self.to_currency
                    or self.amount * self.fx_rate != self.to_amount
                ):
                    raise ValueError(
                        "FX currencies must differ and amount * fx_rate equal to_amount"
                    )
        return self


class TransactionRead(TransactionCreate):
    id: UUID
    portfolio_id: UUID
    sequence: int
    recorded_at: AwareDatetime
    content_sha256: str


class Batch(Contract):
    expected_version: int = Field(ge=0)
    transactions: list[TransactionCreate] = Field(min_length=1, max_length=1000)


class Cash(Contract):
    currency: str
    amount: Decimal


class Position(Contract):
    security_id: UUID
    currency: str
    quantity: Decimal
    cost_basis: Decimal
    average_cost: Decimal


class LedgerState(Contract):
    portfolio_id: UUID
    base_currency: str
    version: int
    as_of: AwareDatetime
    known_at: AwareDatetime
    cash: list[Cash]
    positions: list[Position]
    active_transaction_ids: list[UUID]
    convention: str = "trade_date_cash; moving_average_local_cost; corrected_history_at_known_at"


class BatchResult(Contract):
    version: int
    inserted: int
    duplicates: int
    transactions: list[TransactionRead]
    state: LedgerState


class History(Contract):
    transactions: list[TransactionRead]
    version: int
    total: int


class CsvImport(Contract):
    expected_version: int = Field(ge=0)
    source: Text
    csv_text: str = Field(min_length=1, max_length=2_000_000)


class ImportResult(BatchResult):
    normalized_request: Batch


class Price(Contract):
    security_id: UUID
    currency: Currency
    price: Nonnegative
    observed_at: AwareDatetime
    source: Text


class FX(Contract):
    currency: Currency
    rate: Positive
    observed_at: AwareDatetime
    source: Text


class ValuationRequest(Contract):
    as_of: AwareDatetime
    known_at: AwareDatetime | None = None
    prices: list[Price] = Field(default_factory=list, max_length=1000)
    fx: list[FX] = Field(default_factory=list, max_length=100)


class PositionValue(Position):
    market_value_local: Decimal | None
    unrealized_pnl_local: Decimal | None
    market_value_base: Decimal | None
    translated_unrealized_pnl_base: Decimal | None
    weight: Decimal | None
    reason: str | None


class CashValue(Cash):
    value_base: Decimal | None
    weight: Decimal | None
    reason: str | None


class ValuationResult(Contract):
    state: LedgerState
    positions: list[PositionValue]
    cash: list[CashValue]
    nav: Decimal | None
    reason: str | None
    inputs: ValuationRequest

"""Strict native-source review; deliberately does not produce FactorEvidence."""

import csv
import hashlib
import re
from datetime import UTC, date, datetime
from decimal import Decimal, localcontext
from itertools import pairwise
from typing import Annotated, Final, Literal, Self
from uuid import UUID

from pydantic import AwareDatetime, ConfigDict, Field, model_validator

from src.accounting.contracts import Contract, Currency, Text
from src.factors.contracts import Return
from src.performance.identity import digest, source_sha256

SOURCE_URL: Final = (
    "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/Developed_5_Factors_Daily_CSV.zip"
)
MAX_BYTES = 2_000_000
MAX_ROWS = 25_000
COLUMNS = ["Mkt-RF", "SMB", "HML", "RMW", "CMA", "RF"]
Hash = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]


class SourceMetadata(Contract):
    source_url: Literal[
        "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/"
        "Developed_5_Factors_Daily_CSV.zip"
    ] = SOURCE_URL
    retrieved_at: AwareDatetime
    published_at: AwareDatetime | None = None
    publication_note: str = Field(default="", max_length=2000)
    review_note: Text

    @model_validator(mode="after")
    def chronology(self) -> Self:
        if self.published_at is not None and (
            self.published_at > self.retrieved_at or not self.publication_note
        ):
            raise ValueError(
                "A publication time needs supporting evidence and must precede retrieval"
            )
        return self


class SourceRequest(Contract):
    # Preserve submitted whitespace/line endings for the UTF-8 content identity.
    model_config = ConfigDict(str_strip_whitespace=False)
    csv_text: str = Field(min_length=1, max_length=MAX_BYTES)
    metadata: SourceMetadata
    start: date
    end: date

    @model_validator(mode="after")
    def bounded(self) -> Self:
        if self.end < self.start or (self.end - self.start).days > 3660:
            raise ValueError("Select an ordered source-date window of at most 3660 days")
        try:
            size = len(self.csv_text.encode("utf-8"))
        except UnicodeEncodeError as exc:
            raise ValueError("CSV text must be valid UTF-8") from exc
        if size > MAX_BYTES:
            raise ValueError("CSV text exceeds the two-million-byte limit")
        return self


class SourceRow(Contract):
    date: date
    returns: dict[str, Return | None]


class SourceGap(Contract):
    previous: date
    next: date
    absent_calendar_dates: int


class SourceReview(Contract):
    methodology: Literal["french_developed_daily_source_review_v1"] = (
        "french_developed_daily_source_review_v1"
    )
    portfolio_id: UUID
    account_currency: Currency
    native_currency: Literal["USD"] = "USD"
    native_calendar: Literal["provider_daily_date_labels"] = "provider_daily_date_labels"
    input_units: Literal["percent"] = "percent"
    output_units: Literal["decimal_simple_return"] = "decimal_simple_return"
    regression_ready: Literal[False] = False
    origin_status: Literal["user_declared_not_authenticated"] = "user_declared_not_authenticated"
    imported_at: AwareDatetime
    inputs: SourceRequest
    submitted_text_sha256: Hash
    code_sha256: Hash
    database_vintage: str
    total_source_rows: int
    source_first: date
    source_last: date
    rows: list[SourceRow]
    selected_rows: int
    missing_cells: int
    calendar_gaps: list[SourceGap]
    blockers: list[str]
    warnings: list[str]
    receipt_sha256: Hash


def parse_source(text: str) -> tuple[str, list[SourceRow]]:
    lines = [line.strip() for line in text.removeprefix("\ufeff").splitlines() if line.strip()]
    if len(lines) < 4 or len(lines) > MAX_ROWS + 3:
        raise ValueError("CSV needs the supported preamble/header and 1 to 25000 rows")
    match = re.fullmatch(r"This file was created using the (\d{6}) Bloomberg database\.", lines[0])
    if not match or lines[1] != "Missing data are indicated by -99.99.":
        raise ValueError("Unsupported source preamble or missing-value convention")
    vintage = match[1]
    try:
        date(int(vintage[:4]), int(vintage[4:]), 1)
    except ValueError as exc:
        raise ValueError("Invalid database vintage") from exc
    if lines[2].split(",") != ["", *COLUMNS]:
        raise ValueError("Expected the developed daily Mkt-RF,SMB,HML,RMW,CMA,RF header")
    rows: list[SourceRow] = []
    for index, fields in enumerate(csv.reader(lines[3:], strict=True), start=1):
        if len(fields) != 7 or not re.fullmatch(r"\d{8}", fields[0].strip()):
            raise ValueError(f"Invalid daily date or column count at data row {index}")
        label = fields[0].strip()
        try:
            day = date(int(label[:4]), int(label[4:6]), int(label[6:]))
        except ValueError as exc:
            raise ValueError(f"Invalid source date at data row {index}") from exc
        if rows and day <= rows[-1].date:
            raise ValueError("Source dates must be strictly increasing and unique")
        values: dict[str, Decimal | None] = {}
        for name, raw in zip(COLUMNS, fields[1:], strict=True):
            token = raw.strip()
            if not re.fullmatch(r"[+-]?\d{1,10}(?:\.\d{1,8})?", token):
                raise ValueError(f"Invalid numeric value at data row {index}, column {name}")
            with localcontext() as ctx:
                ctx.prec = 40
                percent = Decimal(token)
                values[name] = None if percent == Decimal("-99.99") else percent / 100
            value = values[name]
            if name == "RF" and value is not None and value <= -1:
                raise ValueError(f"Risk-free return must exceed -100% at data row {index}")
        rows.append(SourceRow(date=day, returns=values))
    return vintage, rows


def review_source(
    data: SourceRequest, portfolio_id: UUID, account_currency: str, imported_at: datetime
) -> SourceReview:
    if imported_at.tzinfo is None or data.metadata.retrieved_at > imported_at:
        raise ValueError("Retrieval must not exceed the timezone-aware import time")
    try:
        vintage, all_rows = parse_source(data.csv_text)
    except csv.Error as exc:
        raise ValueError("Malformed CSV quoting") from exc
    if all_rows[-1].date > data.metadata.retrieved_at.astimezone(UTC).date():
        raise ValueError("Source dates cannot follow the retrieval date")
    rows = [row for row in all_rows if data.start <= row.date <= data.end]
    blockers = ["source_dates_have_no_verified_utc_valuation_boundaries"]
    if account_currency != "USD":
        blockers.append("source_currency_differs_from_account_currency")
    if data.metadata.published_at is None:
        blockers.append("historical_publication_availability_unknown")
    else:
        blockers.append("declared_publication_requires_independent_review")
    blockers.append("risk_free_and_spread_funding_alignment_not_accepted")
    if not rows:
        blockers.append("no_rows_in_selected_window")
    if data.start < all_rows[0].date or data.end > all_rows[-1].date:
        blockers.append("selected_window_exceeds_source_range")
    missing = sum(value is None for row in rows for value in row.returns.values())
    if missing:
        blockers.append("missing_source_values")
    gaps = [
        SourceGap(previous=a.date, next=b.date, absent_calendar_dates=(b.date - a.date).days - 1)
        for a, b in pairwise(rows)
        if (b.date - a.date).days > 1
    ]
    report = SourceReview(
        portfolio_id=portfolio_id,
        account_currency=account_currency,
        imported_at=imported_at,
        inputs=data,
        submitted_text_sha256=hashlib.sha256(data.csv_text.encode("utf-8")).hexdigest(),
        code_sha256=source_sha256(),
        database_vintage=vintage,
        total_source_rows=len(all_rows),
        source_first=all_rows[0].date,
        source_last=all_rows[-1].date,
        rows=rows,
        selected_rows=len(rows),
        missing_cells=missing,
        calendar_gaps=gaps,
        blockers=blockers,
        warnings=[
            "Native source review only. No portfolio returns, regression or currency conversion.",
            "Dates are provider labels, not observed/published UTC timestamps. Retrieval does not "
            "prove historical availability; database vintage is not a publication timestamp.",
            "Percentages divided by 100; only the declared -99.99 sentinel becomes null. "
            "No clipping, filling, resampling or dropping malformed rows.",
            "Mkt-RF is an excess market factor; SMB/HML/RMW/CMA are spreads. RF retains "
            "the provider's USD trading-day construction; no second RF subtraction or compounding.",
            "Gaps count absent calendar labels, not confirmed missing trading observations. "
            "A truncated file can pass structural checks; source completeness is not certified.",
            "URL/origin and publication metadata are user declarations, not authentication. "
            "Retain source rights/provenance before wider redistribution or real-account use.",
        ],
        receipt_sha256="0" * 64,
    )
    report.receipt_sha256 = digest(report.model_dump(mode="json", exclude={"receipt_sha256"}))
    return report


def verify_source_review(saved: SourceReview) -> None:
    rebuilt = review_source(
        saved.inputs, saved.portfolio_id, saved.account_currency, saved.imported_at
    )
    if saved.model_dump(mode="json") != rebuilt.model_dump(mode="json"):
        raise ValueError("Source review differs from retained inputs, source code or methodology")

"""Explicit allowlisted demo projection; all public financial values are backend-derived."""

from datetime import UTC, date, datetime
from decimal import Decimal, localcontext
from typing import Annotated, Literal
from uuid import UUID

from pydantic import AwareDatetime, Field

from src.accounting.contracts import Contract, ValuationRequest
from src.accounting.precision import accounting_context
from src.accounting.repository import LedgerRepository
from src.accounting.valuation import value_state
from src.attribution.engine import build_contribution
from src.benchmark.engine import build_comparison
from src.performance.engine import build_report, close
from src.performance.identity import digest
from src.performance.metrics import Metric
from src.public_track_record.demo import DemoEvidence, demo_evidence
from src.research.thesis.repository import ThesisRepository

DEMO_LABEL: Literal["Demonstration portfolio — synthetic data; no real money invested"] = (
    "Demonstration portfolio — synthetic data; no real money invested"
)
Hash = Annotated[str, Field(pattern=r"^[a-f0-9]{64}$")]
Number = Annotated[float, Field(allow_inf_nan=False)]
Key = Annotated[str, Field(pattern=r"^[a-z][a-z0-9_-]{0,50}$")]


class PublicPoint(Contract):
    date: date
    growth_index: Number | None
    comparison_index: Number | None
    drawdown_return: Number | None
    daily_return: Metric


class PublicPeriod(Contract):
    label: str
    start: date
    end: date
    partial: bool
    return_value: Metric


class PublicHolding(Contract):
    key: Key
    name: str
    local_currency: str
    quantity: Decimal
    value_base: Decimal
    weight: Decimal
    entry_date: date
    risk_contribution: Metric
    thesis_key: Key | None


class PublicClosed(Contract):
    key: Key
    name: str
    entry_date: date
    exit_date: date
    local_currency: str
    net_local_pnl: Decimal
    linked_portfolio_return: Decimal
    thesis_key: Key | None


class PublicRevision(Contract):
    version: int
    actual_recorded_at: AwareDatetime
    status: str
    bear_case: str
    base_case: str
    bull_case: str
    invalidation_conditions: str


class PublicResearch(Contract):
    key: Key
    title: str
    example_date: date
    actual_created_at: AwareDatetime
    versions: list[PublicRevision]
    review_example_date: date
    actual_reviewed_at: AwareDatetime
    review: str


class PublicJournal(Contract):
    key: Key
    example_date: date
    actual_recorded_at: AwareDatetime
    text: str


class PublicSnapshot(Contract):
    schema_version: Literal["demo_snapshot_v1"] = "demo_snapshot_v1"
    mode: Literal["demo"]
    label: Literal["Demonstration portfolio — synthetic data; no real money invested"]
    title: Literal["Original synthetic portfolio research"] = (
        "Original synthetic portfolio research"
    )
    fixture_id: Literal["original-synthetic-launch-v1"]
    fixture_sha256: Hash
    calculation_source_sha256: Hash
    actual_created_at: AwareDatetime
    snapshot_at: AwareDatetime
    data_start: date
    data_end: date
    base_currency: Literal["GBP"] = "GBP"
    measurement_scope: Literal["selected_period"] = "selected_period"
    valuation_convention: str
    entry_date_convention: str
    comparison_name: Literal["Synthetic comparison — original illustration"]
    twr: Metric
    comparison_return: Metric
    max_drawdown: Metric
    nav: Decimal
    holdings: list[PublicHolding]
    cash_value_base: Decimal
    closed_positions: list[PublicClosed]
    research: list[PublicResearch]
    journal: list[PublicJournal]
    series: list[PublicPoint]
    monthly: list[PublicPeriod]
    annual: list[PublicPeriod]
    contribution_residual: Decimal
    contribution_tolerance: Decimal
    methodology: list[str]
    disclosures: list[str]


class SnapshotEnvelope(Contract):
    status: Literal["local_preview", "published"]
    version: str
    content_sha256: Hash
    published_at: AwareDatetime | None
    correction_of: str | None = None
    correction_reason: str | None = None
    snapshot: PublicSnapshot


def growth_and_drawdown(values: list[Decimal | None]) -> list[tuple[float | None, float | None]]:
    """A missing value breaks continuity; never bridge gaps with chart samples."""
    peak: Decimal | None = None
    broken = False
    result: list[tuple[float | None, float | None]] = []
    with localcontext(accounting_context()):
        for value in values:
            if value is None or value < 0 or (peak is None and value == 0):
                broken = True
            if broken:
                result.append((None, None))
                continue
            assert value is not None
            peak = value if peak is None else max(peak, value)
            result.append((float(value * 100), float(value / peak - 1)))
    return result


def project_demo(
    repository: LedgerRepository, portfolio_id: UUID, selected_research: list[str] | None = None
) -> PublicSnapshot:
    evidence = DemoEvidence.model_validate(demo_evidence(repository, portfolio_id))
    receipt = evidence.receipt
    spec = evidence.fixture
    selected = (
        [r["security_key"] for r in spec["research"]]
        if selected_research is None
        else selected_research
    )
    if len(set(selected)) != len(selected) or set(selected) - set(receipt.securities):
        raise ValueError("Select only original fictional research keys")
    rows = repository.rows(portfolio_id)
    report = build_report(portfolio_id, "GBP", rows, evidence.performance)
    contribution = build_contribution(report)
    comparison = build_comparison(report, evidence.benchmark, contribution)
    if report.twr.value is None or comparison.paired_intervals != comparison.expected_intervals:
        raise ValueError("Public demo requires complete performance and comparison coverage")
    reconciliation = contribution.reconciliation
    if reconciliation.within_tolerance is not True:
        raise ValueError("Public demo contribution did not reconcile")
    assert reconciliation.residual.value is not None and reconciliation.tolerance is not None
    final_marks = evidence.performance.daily_marks[-1]
    state = repository.state(portfolio_id, close(receipt.end), receipt.loaded_at)
    valuation = value_state(
        state,
        ValuationRequest(
            as_of=state.as_of,
            known_at=state.known_at,
            prices=final_marks.prices,
            fx=final_marks.fx,
        ),
    )
    if valuation.nav is None:
        raise ValueError("Public demo holdings require complete final valuation")
    canceled = {r.reverses_id for r in rows if r.type == "REVERSAL"}
    active = [r for r in rows if r.type != "REVERSAL" and r.id not in canceled]
    holdings: list[PublicHolding] = []
    closed_positions: list[PublicClosed] = []
    for item in spec["securities"]:
        key = item["key"]
        security_id = receipt.securities[key]
        transactions = [r for r in active if r.security_id == security_id]
        buys = [r for r in transactions if r.type == "BUY"]
        sells = [r for r in transactions if r.type == "SELL"]
        entry_date = min(r.effective_at.date() for r in buys)
        position = next((p for p in valuation.positions if p.security_id == security_id), None)
        if position is not None:
            assert position.market_value_base is not None and position.weight is not None
            holdings.append(
                PublicHolding(
                    key=key,
                    name=item["name"],
                    local_currency=item["currency"],
                    quantity=position.quantity,
                    value_base=position.market_value_base,
                    weight=position.weight,
                    entry_date=entry_date,
                    thesis_key=key if key in selected else None,
                    risk_contribution=Metric(
                        value=None,
                        reason="matching_ex_ante_covariance_inputs_not_supplied",
                        observations=0,
                    ),
                )
            )
        elif sells:
            pnl = Decimal(0)
            with localcontext(accounting_context()):
                for row in transactions:
                    if row.type in ("BUY", "SELL"):
                        assert row.quantity is not None and row.price is not None
                        pnl += (
                            row.quantity * row.price * (1 if row.type == "SELL" else -1) - row.fees
                        )
                    elif row.type == "DIVIDEND":
                        assert row.amount is not None
                        pnl += row.amount
            component = next(c for c in contribution.components if c.security_id == security_id)
            assert component.total.value is not None
            closed_positions.append(
                PublicClosed(
                    key=key,
                    name=item["name"],
                    entry_date=entry_date,
                    exit_date=max(r.effective_at.date() for r in sells),
                    local_currency=item["currency"],
                    net_local_pnl=pnl,
                    linked_portfolio_return=component.total.value,
                    thesis_key=key if key in selected else None,
                )
            )
    research = []
    thesis_repo = ThesisRepository(repository.session)
    for item in spec["research"]:
        key = item["security_key"]
        if key not in selected:
            continue
        thesis = thesis_repo.get_thesis(receipt.theses[key])
        versions = thesis_repo.revisions(thesis.id)
        reviews = thesis_repo.reviews(thesis.id)
        research.append(
            PublicResearch(
                key=key,
                title=item["title"],
                example_date=item["example_date"],
                actual_created_at=thesis.created_at,
                versions=[
                    PublicRevision(
                        version=r.revision,
                        actual_recorded_at=r.created_at,
                        status=r.status,
                        bear_case=r.bear_case,
                        base_case=r.base_case,
                        bull_case=r.bull_case,
                        invalidation_conditions=r.invalidation_conditions,
                    )
                    for r in reversed(versions)
                ],
                review_example_date=item["review_example_date"],
                actual_reviewed_at=reviews[0].reviewed_at,
                review=item["review"],
            )
        )
    indexes = growth_and_drawdown([r.unit_value for r in report.daily])
    comparison_base = evidence.benchmark.levels[0].level
    assert comparison_base is not None and comparison_base > 0
    with localcontext(accounting_context()):
        series = [
            PublicPoint(
                date=day.date,
                growth_index=index[0],
                drawdown_return=index[1],
                daily_return=day.daily_return,
                comparison_index=float(level.level / comparison_base * 100)
                if level.level is not None
                else None,
            )
            for day, level, index in zip(
                report.daily, evidence.benchmark.levels, indexes, strict=True
            )
        ]
        cash_value = Decimal(0)
        for cash in valuation.cash:
            assert cash.value_base is not None
            cash_value += cash.value_base
    original_fee = next(r for r in rows if r.external_reference == "mistaken-fee")
    correction = next(r for r in rows if r.external_reference == "fee-reversal")
    assert report.manifest.code_sha256 is not None
    return PublicSnapshot(
        mode=evidence.mode,
        label=DEMO_LABEL,
        fixture_id=receipt.fixture_id,
        fixture_sha256=receipt.fixture_sha256,
        calculation_source_sha256=report.manifest.code_sha256,
        actual_created_at=receipt.loaded_at,
        snapshot_at=datetime.now(UTC),
        data_start=receipt.start,
        data_end=receipt.end,
        valuation_convention=(
            "UTC calendar-day closes; unadjusted synthetic prices; booked net "
            "dividends/fees; explicit FX and pre-flow marks"
        ),
        entry_date_convention=(
            "Earliest active synthetic BUY date within this fixture; not broker "
            "execution or tax-lot inception"
        ),
        comparison_name="Synthetic comparison — original illustration",
        twr=report.twr,
        comparison_return=comparison.benchmark_return,
        max_drawdown=report.statistics["max_drawdown"],
        nav=valuation.nav,
        cash_value_base=cash_value,
        holdings=holdings,
        closed_positions=closed_positions,
        research=research,
        series=series,
        monthly=[PublicPeriod.model_validate(p.model_dump()) for p in report.linked["monthly"]],
        annual=[PublicPeriod.model_validate(p.model_dump()) for p in report.linked["annual"]],
        journal=[
            PublicJournal(
                key="original-fee",
                example_date=original_fee.effective_at.date(),
                actual_recorded_at=original_fee.recorded_at,
                text="Fictional original GBP 9 fee retained in the immutable history.",
            ),
            PublicJournal(
                key="fee-correction",
                example_date=correction.effective_at.date(),
                actual_recorded_at=correction.recorded_at,
                text=(
                    "Fictional GBP 9 fee reversed and replaced with GBP 2. Correction is "
                    "retained; it does not silently rewrite history."
                ),
            ),
        ],
        contribution_residual=reconciliation.residual.value,
        contribution_tolerance=reconciliation.tolerance,
        methodology=[
            (
                "TWR uses the accepted unitized ledger method; deposits and withdrawals"
                " are neutralized at explicit flow boundaries."
            ),
            (
                "Growth index starts at the funded opening UTC close (100). The opening"
                " point is a baseline, not a zero-filled daily return."
            ),
            (
                "Drawdown is unit-value / previous running peak minus one. Public "
                "charts display backend-derived values, not statistics recomputed from "
                "sampled points."
            ),
            (
                "Calendar period returns are geometrically linked by the backend; "
                "partial months/years stay labelled and are never extrapolated."
            ),
            (
                "Synthetic anchors and flat within-day quotes are original fixture "
                "inputs, not real-market gap filling. Comparison levels are wholly "
                "synthetic."
            ),
            (
                "Local closed-position P&L includes trades, booked dividends and fees; "
                "linked return contribution includes portfolio weighting/FX and is a "
                "different measure."
            ),
            (
                "Actual recording, example dates, snapshot time and later publication "
                "time are distinct. Content hashes prove consistency, not external "
                "attestation."
            ),
        ],
        disclosures=[
            DEMO_LABEL,
            (
                "Personal portfolio-management research; not investment advice; no "
                "solicitation or management of external capital."
            ),
            (
                "Past performance does not indicate future results. This synthetic "
                "illustration is not a verified personal track record."
            ),
            (
                "Short 47-interval example; no expected-return, factor-alpha, "
                "persistent-skill or real-broker claim. Unsupported risk contributions "
                "remain unavailable."
            ),
            (
                "Fictional research and journal examples were created at the displayed "
                "actual timestamps; they are not the owner's contemporaneous historical"
                " beliefs."
            ),
        ],
    )


def envelope(snapshot: PublicSnapshot, version: str = "original-v1") -> SnapshotEnvelope:
    return SnapshotEnvelope(
        status="local_preview",
        version=version,
        content_sha256=digest(snapshot.model_dump(mode="json")),
        published_at=None,
        snapshot=snapshot,
    )

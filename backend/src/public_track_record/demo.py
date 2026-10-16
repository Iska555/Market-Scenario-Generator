"""Explicit original synthetic loader and evidence; accepted engines do all reporting."""

import json
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal, localcontext
from itertools import pairwise
from pathlib import Path
from typing import Any, Literal
from uuid import UUID

from pydantic import AwareDatetime
from sqlalchemy import JSON, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from src.accounting.contracts import Batch, Contract, TransactionCreate, TransactionRead
from src.accounting.ledger import replay
from src.accounting.precision import accounting_context
from src.accounting.repository import LedgerRepository, fingerprint
from src.benchmark.contracts import BenchmarkEvidence
from src.performance.contracts import PerformanceRequest
from src.performance.engine import close
from src.performance.identity import digest
from src.public_track_record.tables import PortfolioIdentityRow
from src.research.repository import ResearchConflict, ResearchRepository
from src.research.schemas import SecurityCreate
from src.research.tables import Base
from src.research.thesis.repository import ThesisRepository
from src.research.thesis.schemas import ReviewCreate, RevisionCreate, ThesisCreate

FIXTURE_PATH = Path(__file__).resolve().parents[2] / "demo" / "launch_v1.json"


class DemoReceipt(Contract):
    fixture_id: Literal["original-synthetic-launch-v1"]
    fixture_sha256: str
    mode: Literal["demo"] = "demo"
    portfolio_id: UUID
    loaded_at: AwareDatetime
    start: date
    end: date
    ledger_version: int
    securities: dict[str, UUID]
    theses: dict[str, UUID]
    transactions: dict[str, UUID]
    ledger_sha256: str
    research_sha256: str


class DemoLoadRow(Base):
    __tablename__ = "demo_load_receipts"
    portfolio_id: Mapped[UUID] = mapped_column(
        ForeignKey("portfolio_identities.portfolio_id"), primary_key=True
    )
    receipt: Mapped[dict] = mapped_column(JSON())


class DemoEvidence(Contract):
    mode: Literal["demo"]
    label: str
    receipt: DemoReceipt
    fixture: dict[str, Any]
    performance: PerformanceRequest
    benchmark: BenchmarkEvidence


def fixture() -> dict[str, Any]:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))  # type: ignore[no-any-return]


def ledger_hash(rows: list[TransactionRead]) -> str:
    return digest([row.model_dump(mode="json") for row in rows])


def research_hash(repository: LedgerRepository, receipt: DemoReceipt) -> str:
    repo = ThesisRepository(repository.session)
    return digest(
        [
            dict(
                revisions=[r.model_dump(mode="json") for r in repo.revisions(thesis_id)],
                reviews=[r.model_dump(mode="json") for r in repo.reviews(thesis_id)],
            )
            for thesis_id in receipt.theses.values()
        ]
    )


def require_demo(repository: LedgerRepository, portfolio_id: UUID) -> None:
    portfolio = repository.portfolio(portfolio_id)
    identity = repository.session.get(PortfolioIdentityRow, portfolio_id)
    if identity is None or identity.mode != "demo" or portfolio.base_currency != "GBP":
        raise ValueError("This original GBP fixture requires an explicit demo identity")


def checked_receipt(repository: LedgerRepository, portfolio_id: UUID) -> DemoReceipt:
    require_demo(repository, portfolio_id)
    stored = repository.session.get(DemoLoadRow, portfolio_id)
    if stored is None:
        raise ValueError("Load the deliberate synthetic example first")
    receipt = DemoReceipt.model_validate(stored.receipt)
    if receipt.fixture_sha256 != digest(fixture()):
        raise ResearchConflict("Fixture changed; use a separate demo identity for a new version")
    if ledger_hash(repository.rows(portfolio_id)) != receipt.ledger_sha256:
        raise ResearchConflict("Demo ledger changed; original fixture evidence cannot be reused")
    if research_hash(repository, receipt) != receipt.research_sha256:
        raise ResearchConflict("Demo research changed; review it independently")
    # Synthetic registry identities are isolated by portfolio, and must not drift
    # into real equity labels/currencies through the existing mutable registry.
    research = ResearchRepository(repository.session)
    for spec in fixture()["securities"]:
        security = research.get_security(receipt.securities[spec["key"]])
        expected = security_spec(portfolio_id, spec)
        if security.model_dump(include=set(SecurityCreate.model_fields)) != expected.model_dump():
            raise ResearchConflict("Demo equity identity changed; original evidence is unavailable")
    return receipt


def security_spec(portfolio_id: UUID, spec: dict[str, Any]) -> SecurityCreate:
    return SecurityCreate.model_validate(
        {k: v for k, v in spec.items() if k != "key"}
        | {
            "exchange": "DEMO-" + portfolio_id.hex[:20],
        }
    )


def load_demo(repository: LedgerRepository, portfolio_id: UUID) -> DemoReceipt:
    require_demo(repository, portfolio_id)
    if repository.session.get(DemoLoadRow, portfolio_id) is not None:
        return checked_receipt(repository, portfolio_id)
    if repository.rows(portfolio_id):
        raise ResearchConflict("Fixture requires an empty demo; existing history is never reset")
    spec = fixture()
    # A single savepoint also rolls back equities/theses on any loader failure.
    with repository.session.begin_nested():
        research = ResearchRepository(repository.session)
        securities = {
            item["key"]: research.create_security(security_spec(portfolio_id, item)).id
            for item in spec["securities"]
        }
        references: dict[str, TransactionRead] = {}
        for item in spec["transactions"]:
            data = {
                k: v for k, v in item.items() if k not in ("security_key", "reverses_reference")
            }
            if "security_key" in item:
                data["security_id"] = securities[item["security_key"]]
            if "reverses_reference" in item:
                data["reverses_id"] = references[item["reverses_reference"]].id
            data["source"] = spec["fixture_id"]
            data["note"] = "Synthetic example; no broker execution. Effective date is fictional."
            transaction = TransactionCreate.model_validate(data)
            result = repository.evaluate(
                portfolio_id,
                Batch(expected_version=len(references), transactions=[transaction]),
                save=True,
            )
            references[item["external_reference"]] = result.transactions[0]
            assert result.transactions[0].content_sha256 == fingerprint(transaction)
        theses: dict[str, UUID] = {}
        thesis_repo = ThesisRepository(repository.session)
        for item in spec["research"]:
            key = item["security_key"]
            currency = next(s["currency"] for s in spec["securities"] if s["key"] == key)
            content = dict(
                status="active",
                horizon_months=12,
                conviction="low",
                valuation_currency=currency,
                variant_perception=item["title"],
                business_quality="Original fictional example.",
                earnings_drivers="Illustrative renewals.",
                catalysts="Illustrative results review.",
                risks=item["risk"],
                bear_case=item["bear_case"],
                base_case=item["base_case"],
                bull_case=item["bull_case"],
                invalidation_conditions="Fictional churn undermines renewals.",
                notes=(
                    f"Synthetic research; example date {item['example_date']}; "
                    "recorded now, not a historical personal belief."
                ),
            )
            thesis = thesis_repo.create_thesis(
                ThesisCreate.model_validate(content | {"security_id": securities[key]})
            )
            thesis_repo.create_review(
                thesis.id,
                ReviewCreate(
                    revision_id=thesis.latest.id,
                    decision="EXIT" if key == "orchard" else "REDUCE",
                    valuation_currency=currency,
                    thesis_still_valid=key != "orchard",
                    what_was_wrong=item["review"],
                    notes=(
                        f"Synthetic journal example date {item['review_example_date']}; "
                        "actual review recorded now."
                    ),
                ),
            )
            thesis_repo.append_revision(
                thesis.id,
                RevisionCreate.model_validate(
                    content
                    | {
                        "expected_revision": 1,
                        "status": "closed" if key == "orchard" else "active",
                        "notes": "Fictional review revision: " + item["review"],
                    }
                ),
            )
            theses[key] = thesis.id
        rows = repository.rows(portfolio_id)
        receipt = DemoReceipt(
            fixture_id=spec["fixture_id"],
            fixture_sha256=digest(spec),
            portfolio_id=portfolio_id,
            loaded_at=datetime.now(UTC),
            start=spec["start"],
            end=spec["end"],
            ledger_version=len(rows),
            securities=securities,
            theses=theses,
            transactions={key: row.id for key, row in references.items()},
            ledger_sha256=ledger_hash(rows),
            research_sha256="pending",
        )
        receipt.research_sha256 = research_hash(repository, receipt)
        repository.session.add(
            DemoLoadRow(portfolio_id=portfolio_id, receipt=receipt.model_dump(mode="json"))
        )
        repository.session.flush()
    return receipt


def interpolate(points: list[list[str]], day: date) -> Decimal:
    """Generate explicitly synthetic inputs, never a market-data gap-fill policy."""
    for (first, left), (last, right) in pairwise(points):
        start, end = date.fromisoformat(first), date.fromisoformat(last)
        if start <= day <= end:
            with localcontext(accounting_context()):
                return (
                    Decimal(left)
                    + (Decimal(right) - Decimal(left))
                    * Decimal((day - start).days)
                    / Decimal((end - start).days)
                ).quantize(Decimal("0.000001"))
    raise ValueError("Synthetic anchor coverage is incomplete")


def demo_evidence(repository: LedgerRepository, portfolio_id: UUID) -> dict[str, Any]:
    receipt = checked_receipt(repository, portfolio_id)
    spec, rows = fixture(), repository.rows(portfolio_id)
    known_at = receipt.loaded_at
    reverse = {value: key for key, value in receipt.securities.items()}

    def marks(at: datetime, selected: list[TransactionRead]) -> dict[str, Any]:
        state = replay(portfolio_id, "GBP", selected, at, known_at)
        return dict(
            prices=[
                dict(
                    security_id=str(p.security_id),
                    currency=p.currency,
                    price=str(interpolate(spec["price_points"][reverse[p.security_id]], at.date())),
                    observed_at=at.isoformat(),
                    source=spec["fixture_id"],
                )
                for p in state.positions
            ],
            fx=[
                dict(
                    currency="USD",
                    rate=str(interpolate(spec["fx_points"], at.date())),
                    observed_at=at.isoformat(),
                    source=spec["fixture_id"],
                )
            ]
            if any(c.currency == "USD" for c in state.cash)
            else [],
        )

    days = [
        receipt.start + timedelta(days=i) for i in range((receipt.end - receipt.start).days + 1)
    ]
    canceled = {r.reverses_id for r in rows if r.type == "REVERSAL"}
    active = [r for r in rows if r.type != "REVERSAL" and r.id not in canceled]
    flows = [
        r
        for r in active
        if r.type in ("DEPOSIT", "WITHDRAWAL")
        and close(receipt.start) < r.effective_at <= close(receipt.end)
    ]
    request = PerformanceRequest.model_validate(
        dict(
            expected_version=receipt.ledger_version,
            known_at=known_at,
            daily_marks=[dict(date=day, **marks(close(day), rows)) for day in days],
            flow_marks=[
                dict(
                    transaction_id=r.id,
                    **marks(
                        r.effective_at,
                        [
                            q
                            for q in active
                            if (q.effective_at, q.sequence) < (r.effective_at, r.sequence)
                        ],
                    ),
                )
                for r in flows
            ],
            max_mark_age_days=0,
        )
    )
    benchmark = dict(
        identity=dict(
            benchmark_id="synthetic-example-comparison",
            revision="v1",
            name="Synthetic comparison — original illustration",
            provider="Original synthetic fixture",
            methodology_reference="Synthetic anchors v1; see DEMONSTRATION.md; UTC daily GBP.",
            currency="GBP",
            return_basis="net_total_return",
            hedging="not_applicable",
            calendar="UTC_calendar_daily",
            periods_per_year=365,
            currency_policy="already_in_portfolio_currency",
            effective_from=receipt.start.isoformat(),
            effective_to=receipt.end.isoformat(),
            published_at=receipt.loaded_at.isoformat(),
            retrieved_at=receipt.loaded_at.isoformat(),
        ),
        max_level_age_days=0,
        levels=[
            dict(
                date=day.isoformat(),
                level=str(interpolate(spec["comparison_points"], day)),
                observed_at=close(day).isoformat(),
                published_at=receipt.loaded_at.isoformat(),
                retrieved_at=receipt.loaded_at.isoformat(),
                source=spec["fixture_id"],
            )
            for day in days
        ],
    )
    return dict(
        mode="demo",
        label="Demonstration portfolio — synthetic data; no real money invested",
        receipt=receipt.model_dump(mode="json"),
        fixture=spec,
        performance=request.model_dump(mode="json"),
        benchmark=benchmark,
    )

"""Private evidence resolution and reproducibility for hypothetical portfolio alternatives."""

import os
import platform
from datetime import UTC, datetime
from importlib.metadata import version
from typing import Any

from pydantic import AwareDatetime
from sqlalchemy.orm import Session

from src.portfolio.construction.contracts import ConstructionRequest, ConstructionResult
from src.research.schemas import ObservationRead, SecurityRead
from src.research.thesis.schemas import RevisionRead
from src.valuation.contracts import Contract, ExpectedReturnView, ReturnContext
from src.valuation.service import code_identity, digest, evidence
from src.views.expected_return import user_view


class ConstructionEvidence(Contract):
    security: SecurityRead
    observations: list[ObservationRead]
    thesis_revision: RevisionRead | None
    adopted_view: ExpectedReturnView | None


class ConstructionManifest(Contract):
    methodology_version: str = "phase6.1"
    generated_at: AwareDatetime
    resolved_inputs: dict[str, Any]
    input_sha256: str
    evidence_sha256: str
    code_sha256: str
    git_sha: str | None
    git_dirty: bool | None
    build_identity: str | None
    library_versions: dict[str, str]
    evidence: list[ConstructionEvidence]
    data_policy: str = (
        "Supplied data; no provider fetch or permanent report archive. "
        "Hashes identify but do not preserve data."
    )


class ConstructionResponse(Contract):
    result: ConstructionResult
    manifest: ConstructionManifest


def evaluate_construction(session: Session, request: ConstructionRequest) -> ConstructionResponse:
    from src.portfolio.construction.analytics import construct

    records = []
    for asset in request.assets:
        context = (
            asset.investor_view.context
            if asset.investor_view
            else ReturnContext(
                security_id=asset.security_id,
                valuation_date=request.valuation_date,
                horizon_years=1,
                return_basis="total",
                money_basis="nominal",
                currency_basis="local",
                valuation_currency=request.currency,
                local_currency=request.currency,
                valuation_calendar=request.valuation_calendar,
                as_of=request.as_of,
                known_at=request.known_at,
            )
        )
        security, observations, revision = evidence(session, context)
        records.append(
            ConstructionEvidence(
                security=security,
                observations=observations,
                thesis_revision=revision,
                adopted_view=user_view(asset.investor_view) if asset.investor_view else None,
            )
        )
    result = construct(request)
    inputs = request.model_dump(mode="json")
    code_hash, git_sha, dirty = code_identity()
    return ConstructionResponse(
        result=result,
        manifest=ConstructionManifest(
            generated_at=datetime.now(UTC),
            resolved_inputs=inputs,
            input_sha256=digest(inputs),
            evidence_sha256=digest([r.model_dump(mode="json") for r in records]),
            code_sha256=code_hash,
            git_sha=git_sha,
            git_dirty=dirty,
            build_identity=os.environ.get("BUILD_ID"),
            library_versions={
                "python": platform.python_version(),
                **{
                    name: version(name)
                    for name in ("numpy", "scipy", "scikit-learn", "pydantic", "sqlalchemy")
                },
            },
            evidence=records,
        ),
    )

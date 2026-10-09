"""Private security resolution and proportionate supplied-input replay manifest."""

import os
import platform
from datetime import UTC, datetime
from importlib.metadata import version
from typing import Any

from pydantic import AwareDatetime
from sqlalchemy.orm import Session

from src.research.repository import ResearchRepository
from src.research.schemas import SecurityRead
from src.risk.scenarios.historical import evaluate_scenario
from src.risk.scenarios.historical_contracts import StressRequest, StressResult
from src.valuation.contracts import Contract
from src.valuation.service import code_identity, digest


class StressManifest(Contract):
    methodology_version: str = "phase6.supplied-stress.1"
    generated_at: AwareDatetime
    resolved_inputs: dict[str, Any]
    input_sha256: str
    evidence_sha256: str
    code_sha256: str
    git_sha: str | None
    git_dirty: bool | None
    build_identity: str | None
    library_versions: dict[str, str]
    securities: list[SecurityRead]
    random_seed: int | None
    data_policy: str = (
        "Complete supplied history/shocks and current registry snapshots "
        "returned; no provider calls or new archive. Hashes do not preserve data."
    )
    registry_policy: str = (
        "Security registry snapshots identify the current selected "
        "listings; historical identifier/corporate-action mapping is owner-supplied provenance."
    )


class StressResponse(Contract):
    result: StressResult
    manifest: StressManifest


def evaluate(session: Session, request: StressRequest) -> StressResponse:
    repository = ResearchRepository(session)
    securities = [repository.get_security(a.security_id) for a in request.assets]
    if any(security.currency != request.currency for security in securities):
        raise ValueError("Every registered security must use the declared scenario currency")
    result = evaluate_scenario(request)
    inputs = request.model_dump(mode="json")
    code_sha, git_sha, git_dirty = code_identity()
    return StressResponse(
        result=result,
        manifest=StressManifest(
            generated_at=datetime.now(UTC),
            resolved_inputs=inputs,
            input_sha256=digest(inputs),
            evidence_sha256=digest([s.model_dump(mode="json") for s in securities]),
            code_sha256=code_sha,
            git_sha=git_sha,
            git_dirty=git_dirty,
            build_identity=os.environ.get("BUILD_ID"),
            library_versions={
                "python": platform.python_version(),
                **{name: version(name) for name in ("numpy", "pydantic", "sqlalchemy", "fastapi")},
            },
            securities=securities,
            random_seed=request.seed,
        ),
    )

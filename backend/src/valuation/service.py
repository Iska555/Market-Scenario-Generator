"""Resolve authorized point-in-time evidence and emit a proportionate run manifest."""

import hashlib
import json
import os
import platform
import subprocess
from datetime import UTC, datetime
from importlib.metadata import version
from pathlib import Path
from typing import Any

from pydantic import AwareDatetime
from sqlalchemy.orm import Session

from src.research.repository import ResearchRepository
from src.research.schemas import ObservationRead, SecurityRead
from src.research.tables import Observation
from src.research.thesis.schemas import RevisionRead
from src.research.thesis.tables import ThesisRevision
from src.valuation.contracts import (
    CapmRequest,
    Contract,
    EvaluationOutput,
    EvaluationRequest,
    FundamentalRequest,
    HistoricalRequest,
    ReturnContext,
    ReverseRequest,
    ScenarioSetRequest,
    UserViewRequest,
)
from src.valuation.models import fundamental, reverse, scenario_set
from src.views.expected_return import capm, historical, user_view

MODEL_VERSION = "phase5.1"


class RunManifest(Contract):
    model_name: str
    methodology_version: str = MODEL_VERSION
    generated_at: AwareDatetime
    resolved_inputs: dict[str, Any]
    input_sha256: str
    evidence_sha256: str
    code_sha256: str
    git_sha: str | None
    git_dirty: bool | None
    build_identity: str | None
    library_versions: dict[str, str]
    security: SecurityRead
    observations: list[ObservationRead]
    thesis_revision: RevisionRead | None
    random_seed: None = None
    data_policy: str = (
        "Supplied inputs and referenced research snapshots returned; no provider fetch or "
        "new data archive. A hash does not preserve data."
    )
    evidence_use: str = (
        "References support owner assumptions; no automatic mapping of evidence values "
        "into model inputs."
    )


class EvaluationResponse(Contract):
    result: EvaluationOutput
    manifest: RunManifest


def digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    ).hexdigest()


def code_identity() -> tuple[str, str | None, bool | None]:
    root = Path(__file__).resolve().parents[2]
    # Include all domain/transport source, including dirty/untracked Phase 4 dependencies.
    paths = [*sorted((root / "src").rglob("*.py")), root / "main.py"]
    content = [
        (
            str(path.relative_to(root)).replace("\\", "/"),
            hashlib.sha256(path.read_bytes()).hexdigest(),
        )
        for path in paths
    ]
    try:
        sha = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=root,
            capture_output=True,
            text=True,
            check=True,
            timeout=3,
        ).stdout.strip()
        dirty = bool(
            subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=root,
                capture_output=True,
                text=True,
                check=True,
                timeout=3,
            ).stdout.strip()
        )
    except (OSError, subprocess.SubprocessError):
        sha, dirty = None, None
    return digest(content), sha, dirty


def evidence(
    session: Session, context: ReturnContext
) -> tuple[SecurityRead, list[ObservationRead], RevisionRead | None]:
    security = ResearchRepository(session).get_security(context.security_id)
    if security.currency != context.local_currency:
        raise ValueError("Local currency must match the registered security")
    observations = []
    for identifier in context.observation_ids:
        row = session.get(Observation, identifier)
        if row is None or row.security_id != context.security_id:
            raise ValueError("Evidence observation must belong to the selected security")
        if row.reported_at > context.as_of or row.recorded_at > context.known_at:
            raise ValueError("Evidence observation was not available under requested cutoffs")
        if row.currency is not None and row.currency != context.local_currency:
            raise ValueError("Monetary evidence requires matching local currency")
        observations.append(ObservationRead.model_validate(row))
    revision = None
    if context.thesis_revision_id is not None:
        thesis = session.get(ThesisRevision, context.thesis_revision_id)
        if thesis is None or thesis.security_id != context.security_id:
            raise ValueError("Thesis revision must belong to the selected security")
        if thesis.created_at > context.as_of or thesis.created_at > context.known_at:
            raise ValueError("Thesis revision was not available under requested cutoffs")
        revision = RevisionRead.model_validate(thesis)
    return security, observations, revision


def evaluate(session: Session, request: EvaluationRequest) -> EvaluationResponse:
    security, observations, revision = evidence(session, request.context)
    result: EvaluationOutput
    if isinstance(request, UserViewRequest):
        result = user_view(request)
    elif isinstance(request, HistoricalRequest):
        result = historical(request)
    elif isinstance(request, CapmRequest):
        result = capm(request)
    elif isinstance(request, FundamentalRequest):
        result = fundamental(request)
    elif isinstance(request, ScenarioSetRequest):
        result = scenario_set(request)
    else:
        assert isinstance(request, ReverseRequest)
        result = reverse(request)
    inputs = request.model_dump(mode="json")
    code_sha256, git_sha, git_dirty = code_identity()
    snapshots = {
        "security": security.model_dump(mode="json"),
        "observations": [row.model_dump(mode="json") for row in observations],
        "thesis_revision": revision.model_dump(mode="json") if revision else None,
    }
    return EvaluationResponse(
        result=result,
        manifest=RunManifest(
            model_name=request.model,
            generated_at=datetime.now(UTC),
            resolved_inputs=inputs,
            input_sha256=digest(inputs),
            evidence_sha256=digest(snapshots),
            code_sha256=code_sha256,
            git_sha=git_sha,
            git_dirty=git_dirty,
            build_identity=os.environ.get("BUILD_ID"),
            library_versions={
                "python": platform.python_version(),
                **{name: version(name) for name in ("numpy", "pydantic", "sqlalchemy", "fastapi")},
            },
            security=security,
            observations=observations,
            thesis_revision=revision,
        ),
    )

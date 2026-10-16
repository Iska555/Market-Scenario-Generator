"""Deliberately load an isolated demo and preserve its private exact replay bundle."""

import argparse
import hashlib
import json
import os
import sys
import zipfile
from pathlib import Path
from uuid import UUID

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from src.accounting.repository import LedgerRepository
from src.attribution.engine import build_contribution
from src.benchmark.contracts import BenchmarkEvidence
from src.benchmark.engine import build_comparison
from src.performance.contracts import PerformanceRequest
from src.performance.engine import build_report
from src.public_track_record.contracts import DemoCreate
from src.public_track_record.demo import FIXTURE_PATH, demo_evidence, load_demo
from src.public_track_record.repository import create_demo
from src.research.database import postgres_url


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--portfolio-id", required=True, type=UUID)
    parser.add_argument(
        "--create", action="store_true", help="Deliberate creation of a new demo identity"
    )
    parser.add_argument("--name", default="Original synthetic research demonstration")
    parser.add_argument("--output", required=True, type=Path, help="New private evidence directory")
    args = parser.parse_args()
    if args.output.exists() and any(args.output.iterdir()):
        parser.error("Output must be empty; preserve existing reports and choose a fresh directory")
    engine = create_engine(postgres_url(os.environ.get("DATABASE_URL", "")))
    try:
        with Session(engine) as session, session.begin():
            repo = LedgerRepository(session)
            if args.create:
                create_demo(
                    repo,
                    DemoCreate(
                        id=args.portfolio_id, name=args.name, base_currency="GBP", mode="demo"
                    ),
                )
            receipt = load_demo(repo, args.portfolio_id)
            evidence = demo_evidence(repo, args.portfolio_id)
            request = PerformanceRequest.model_validate(evidence["performance"])
            performance = build_report(
                args.portfolio_id, "GBP", repo.rows(args.portfolio_id), request
            )
            contribution = build_contribution(performance)
            comparison = build_comparison(
                performance, BenchmarkEvidence.model_validate(evidence["benchmark"]), contribution
            )
            if contribution.reconciliation.within_tolerance is not True:
                raise ValueError("Synthetic example did not reconcile; no bundle exported")
    finally:
        engine.dispose()
    args.output.mkdir(parents=True, exist_ok=True)
    files = {
        "receipt.json": receipt.model_dump(mode="json"),
        "evidence.json": evidence,
        "performance.json": performance.model_dump(mode="json"),
        "contribution.json": contribution.model_dump(mode="json"),
        "comparison.json": comparison.model_dump(mode="json"),
    }
    for name, data in files.items():
        (args.output / name).write_text(
            json.dumps(data, indent=2, allow_nan=False) + "\n", encoding="utf-8"
        )
    (args.output / "fixture.json").write_bytes(FIXTURE_PATH.read_bytes())
    root = Path(__file__).resolve().parents[1]
    source = [
        *sorted((root / "backend/src").rglob("*.py")),
        root / "backend/main.py",
        FIXTURE_PATH,
        *[
            root / "scripts" / name
            for name in (
                "load_demo.py",
                "replay_performance.py",
                "replay_contribution.py",
                "replay_comparison.py",
            )
        ],
    ]
    with zipfile.ZipFile(
        args.output / "compatible-source.zip", "w", compression=zipfile.ZIP_DEFLATED
    ) as archive:
        for path in source:
            archive.write(path, path.relative_to(root).as_posix())
    manifest = dict(
        mode="demo",
        label=evidence["label"],
        fixture_id=receipt.fixture_id,
        fixture_sha256=receipt.fixture_sha256,
        fixture_period=[str(receipt.start), str(receipt.end)],
        actual_loaded_at=receipt.loaded_at.isoformat(),
        public_publication_at=None,
        backend_source_sha256=performance.manifest.code_sha256,
        libraries=performance.manifest.libraries,
        files={
            p.name: hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(args.output.iterdir())
        },
        archive_scope=(
            "Backend Python, original fixture and replay/loader CLIs only. "
            "No migration, DB backup, dependencies, frontend, secrets or hosting."
        ),
        warning=(
            "Private replay exports. Not public-safe downloads, real-money history, "
            "broker evidence or external attestation."
        ),
    )
    (args.output / "manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    print(
        "Synthetic demonstration loaded; private performance, contribution "
        "and comparison bundle preserved."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Generate the allowlisted original local demo preview from a reviewed isolated load."""

import argparse
import os
import sys
from pathlib import Path
from uuid import UUID

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from src.accounting.repository import LedgerRepository
from src.public_track_record.snapshot import envelope, project_demo
from src.research.database import postgres_url


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--portfolio-id", type=UUID, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Preserve old previews; choose a fresh output")
    engine = create_engine(postgres_url(os.environ.get("DATABASE_URL", "")))
    try:
        with Session(engine) as session, session.begin():
            projected = envelope(project_demo(LedgerRepository(session), args.portfolio_id))
    finally:
        engine.dispose()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(projected.model_dump_json(indent=2) + "\n", encoding="utf-8")
    print(
        "Original allowlisted local preview prepared; no publication or private export performed."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

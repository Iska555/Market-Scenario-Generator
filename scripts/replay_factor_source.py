"""Verify a native factor-source review offline using its compatible source archive."""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from pydantic import ValidationError
from src.factors.source import SourceReview, verify_source_review


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path)
    args = parser.parse_args()
    try:
        saved = SourceReview.model_validate_json(args.report.read_bytes())
        verify_source_review(saved)
    except (OSError, ValidationError):
        print("Replay failed: unreadable file or invalid source-review contract", file=sys.stderr)
        return 1
    except ValueError as error:
        print(f"Replay failed: {error}", file=sys.stderr)
        return 1
    print("Source review replay verified: native rows, provenance, blockers and receipt match")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

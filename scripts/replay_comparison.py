"""Verify a private benchmark comparison offline without providers or a database."""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from pydantic import ValidationError
from src.benchmark.contracts import ComparisonReport
from src.benchmark.replay import verify_comparison


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path)
    args = parser.parse_args()
    try:
        saved = ComparisonReport.model_validate_json(args.report.read_bytes())
        verify_comparison(saved)
    except (OSError, ValidationError):
        print("Replay failed: unreadable file or invalid comparison contract", file=sys.stderr)
        return 1
    except ValueError as error:
        print(f"Replay failed: {error}", file=sys.stderr)
        return 1
    print("Comparison replay verified: financial outputs, evidence and methodology match")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

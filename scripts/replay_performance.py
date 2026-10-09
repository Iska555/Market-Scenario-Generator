"""Verify a downloaded Phase 8 report without accessing a database or provider."""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from pydantic import ValidationError
from src.performance.contracts import PerformanceReport
from src.performance.replay import verify_replay


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "report", type=Path, help="Downloaded report containing private financial data"
    )
    args = parser.parse_args()
    try:
        report = PerformanceReport.model_validate_json(args.report.read_bytes())
        verify_replay(report)
    except (OSError, ValidationError):
        print(
            "Replay failed: file is unreadable or does not match the report contract",
            file=sys.stderr,
        )
        return 1
    except ValueError as exc:
        print(f"Replay failed: {exc}", file=sys.stderr)
        return 1
    print("Replay verified: all financial outputs match; no database or provider was accessed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

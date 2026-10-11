"""Verify a private historical factor report offline without a database/provider."""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from pydantic import ValidationError
from src.factors.contracts import FactorReport
from src.factors.replay import verify_factor_report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path)
    args = parser.parse_args()
    try:
        saved = FactorReport.model_validate_json(args.report.read_bytes())
        verify_factor_report(saved)
    except (OSError, ValidationError):
        print("Replay failed: unreadable file or invalid factor contract", file=sys.stderr)
        return 1
    except ValueError as error:
        print(f"Replay failed: {error}", file=sys.stderr)
        return 1
    print("Factor replay verified: financial outputs, evidence and methodology match")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

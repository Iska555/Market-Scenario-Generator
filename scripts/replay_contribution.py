"""Verify a downloaded contribution report without a database or provider."""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from pydantic import ValidationError
from src.attribution.contracts import ContributionReport
from src.attribution.replay import verify_contribution


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path, help="Private contribution replay JSON")
    args = parser.parse_args()
    try:
        saved = ContributionReport.model_validate_json(args.report.read_bytes())
        verify_contribution(saved)
    except (OSError, ValidationError):
        print("Replay failed: unreadable file or invalid contribution contract", file=sys.stderr)
        return 1
    except ValueError as exc:
        print(f"Replay failed: {exc}", file=sys.stderr)
        return 1
    print("Contribution replay verified: financial outputs and methodology match")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

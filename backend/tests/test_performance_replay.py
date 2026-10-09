"""Downloaded reports must replay exactly or explain why verification is impossible."""

from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest
from src.performance.contracts import PerformanceReport
from src.performance.replay import verify_replay

from tests.test_performance_engine import funded, report, request, transaction


def downloaded() -> PerformanceReport:
    result = report(funded(), request("100", "110", expected_version=2))
    return PerformanceReport.model_validate_json(result.model_dump_json())


def test_download_roundtrip_verifies_all_outputs_without_database() -> None:
    saved = downloaded()
    verify_replay(saved)
    assert saved.manifest.code_sha256 and len(saved.manifest.code_sha256) == 64
    assert "python" in saved.manifest.libraries
    saved.twr = saved.twr.model_copy(update={"value": 0.5})
    with pytest.raises(ValueError, match="financial outputs"):
        verify_replay(saved)


@pytest.mark.parametrize(
    ("field", "expected"),
    [
        ("inputs", "Resolved inputs"),
        ("ledger", "Ledger records"),
        ("source", "Backend source"),
        ("runtime", "library versions"),
        ("legacy", "Legacy report"),
        ("identity", "portfolio identities"),
        ("version", "full ledger versions"),
        ("known_version", "Visible ledger version"),
        ("methodology", "Methodology or conventions"),
        ("conventions", "Methodology or conventions"),
    ],
)
def test_replay_rejects_modified_evidence_or_incompatible_environment(
    field: str, expected: str
) -> None:
    saved = downloaded()
    if field == "inputs":
        saved.manifest.inputs.risk_free_rate = 0.1
    elif field == "ledger":
        saved.manifest.ledger_records[0].amount = Decimal("200")
    elif field == "source":
        saved.manifest.code_sha256 = "0" * 64
    elif field == "runtime":
        saved.manifest.libraries["python"] = "0.0.0"
    elif field == "legacy":
        saved.manifest.code_sha256 = None
    elif field == "identity":
        saved.portfolio_id = uuid4()
    elif field == "version":
        saved.manifest.ledger_version = 20
    elif field == "known_version":
        saved.manifest.known_version = 20
    elif field == "methodology":
        saved.manifest.methodology = "unsupported_methodology"
    else:
        saved.manifest.conventions = ["unsupported_convention"]
    with pytest.raises(ValueError, match=expected):
        verify_replay(saved)


def test_historical_replay_does_not_require_records_unknown_at_cutoff() -> None:
    rows = funded()
    reversal = transaction(3, "REVERSAL", "2025-01-01T10:00:00Z", reverses_id=rows[1].id)
    reversal.recorded_at = datetime(2025, 2, 2, tzinfo=UTC)
    saved = report([*rows, reversal], request("100", "110", expected_version=3))
    assert saved.manifest.known_version == 2
    assert saved.manifest.ledger_version == 3
    assert len(saved.manifest.ledger_records) == 2
    verify_replay(PerformanceReport.model_validate_json(saved.model_dump_json()))

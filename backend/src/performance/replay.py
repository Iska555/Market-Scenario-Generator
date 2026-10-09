"""Verify downloaded performance reports offline, without a database or provider."""

import platform
from importlib.metadata import version

from src.performance.contracts import PerformanceReport
from src.performance.engine import build_report
from src.performance.identity import digest, source_sha256


def verify_replay(saved: PerformanceReport) -> None:
    """Require matching source/runtime and verify inputs and every financial output.

    A historical report retains only records visible at its knowledge cutoff.
    Its full ledger version can exceed the replayed snapshot's version.
    Successful verification is consistency evidence, not external attestation.
    """
    manifest = saved.manifest
    if not manifest.code_sha256:
        raise ValueError("Legacy report has no source fingerprint; regenerate before exact replay")
    if manifest.code_sha256 != source_sha256():
        raise ValueError("Backend source differs from the downloaded report")
    runtime = {
        "python": platform.python_version(),
        **{name: version(name) for name in ("numpy", "scipy", "pydantic")},
    }
    if manifest.libraries != runtime:
        raise ValueError("Python or numerical library versions differ from the downloaded report")
    if digest(manifest.inputs.model_dump(mode="json")) != manifest.inputs_sha256:
        raise ValueError("Resolved inputs do not match their fingerprint")
    if (
        digest([row.model_dump(mode="json") for row in manifest.ledger_records])
        != manifest.ledger_sha256
    ):
        raise ValueError("Ledger records do not match their fingerprint")
    if saved.portfolio_id != manifest.portfolio_id or saved.base_currency != manifest.base_currency:
        raise ValueError("Report and manifest portfolio identities differ")
    if manifest.inputs.expected_version != manifest.ledger_version:
        raise ValueError("Report request and full ledger versions differ")
    replayed = build_report(
        manifest.portfolio_id, manifest.base_currency, manifest.ledger_records, manifest.inputs
    )
    if manifest.known_version != replayed.manifest.known_version:
        raise ValueError("Visible ledger version does not match replayed records")
    if (
        manifest.methodology != replayed.manifest.methodology
        or manifest.conventions != replayed.manifest.conventions
    ):
        raise ValueError("Methodology or conventions differ from the offline replay")
    if saved.model_dump(mode="json", exclude={"manifest"}) != replayed.model_dump(
        mode="json", exclude={"manifest"}
    ):
        raise ValueError("Reported financial outputs do not match the offline replay")

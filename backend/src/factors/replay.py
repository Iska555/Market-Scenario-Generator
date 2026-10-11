"""Offline full-report identity and financial-result consistency verification."""

from src.attribution.replay import verify_contribution
from src.benchmark.replay import verify_comparison
from src.factors.contracts import FactorReport
from src.factors.engine import build_factor_report
from src.performance.identity import digest
from src.performance.replay import verify_replay


def verify_factor_report(saved: FactorReport) -> None:
    verify_replay(saved.performance)
    if digest(saved.factors.model_dump(mode="json")) != saved.factors_sha256:
        raise ValueError("Factor evidence differs from its fingerprint")
    if saved.include_contribution != (saved.contribution is not None):
        raise ValueError("Factor contribution setting differs from its retained result")
    if saved.contribution is not None:
        verify_contribution(saved.contribution)
    if saved.comparison is not None:
        verify_comparison(saved.comparison)
    rebuilt = build_factor_report(
        saved.performance, saved.factors, saved.contribution, saved.comparison
    )
    if saved.model_dump(mode="json") != rebuilt.model_dump(mode="json"):
        raise ValueError("Factor results or methodology differ from the offline replay")

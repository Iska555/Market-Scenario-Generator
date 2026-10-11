"""Offline comparison consistency checking, without database/provider access."""

from src.attribution.replay import verify_contribution
from src.benchmark.contracts import ComparisonReport
from src.benchmark.engine import build_comparison
from src.performance.identity import digest
from src.performance.replay import verify_replay


def verify_comparison(saved: ComparisonReport) -> None:
    verify_replay(saved.performance)
    if saved.benchmark_sha256 != digest(saved.benchmark.model_dump(mode="json")):
        raise ValueError("Benchmark evidence differs from its fingerprint")
    if saved.include_contribution != (saved.contribution is not None):
        raise ValueError("Comparison contribution setting differs from its retained result")
    if saved.contribution is not None:
        verify_contribution(saved.contribution)
    rebuilt = build_comparison(saved.performance, saved.benchmark, saved.contribution)
    if saved.model_dump(mode="json") != rebuilt.model_dump(mode="json"):
        raise ValueError("Comparison results or methodology differ from the offline replay")

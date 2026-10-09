"""Offline consistency check of Phase 9A and its underlying performance."""

from src.attribution.contracts import ContributionReport
from src.attribution.engine import build_contribution
from src.performance.replay import verify_replay


def verify_contribution(saved: ContributionReport) -> None:
    verify_replay(saved.performance)
    if saved.model_dump(mode="json") != build_contribution(saved.performance).model_dump(
        mode="json"
    ):
        raise ValueError("Contribution outputs or methodology differ from the offline replay")

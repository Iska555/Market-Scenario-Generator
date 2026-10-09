"""Portfolio inputs must share investment meaning, identity and information cutoffs."""

from datetime import date, timedelta
from typing import Any
from uuid import UUID, uuid4

import pytest
from src.portfolio.construction.contracts import ConstructionRequest

from tests.test_valuation_contracts import context


def construction_payload(**updates: Any) -> dict[str, Any]:
    ids = [str(uuid4()), str(uuid4())]
    start = date(2020, 1, 1)
    data: dict[str, Any] = {
        "assets": [{"security_id": identifier, "current_weight": 0.5} for identifier in ids],
        "history": {
            "security_ids": ids,
            "observations": [
                {
                    "start": str(start + timedelta(days=i * 30)),
                    "end": str(start + timedelta(days=(i + 1) * 30)),
                    "returns": values,
                }
                for i, values in enumerate(
                    [[-0.02, 0.01], [0.02, -0.01], [0.01, 0.03], [-0.01, -0.03]]
                )
            ],
            "frequency": "monthly",
            "periods_per_year": 12,
            "source": "Synthetic",
            "retrieved_at": "2026-09-09T10:00:00Z",
            "adjustment_policy": "total returns, same close",
            "interval_alignment": "identical_start_end_and_valuation_cutoff",
        },
        "valuation_date": "2026-09-09",
        "currency": "USD",
        "risk_free_rate": 0.03,
        "valuation_calendar": "XNYS close, calendar-year horizon",
        "as_of": "2026-09-09T12:00:00Z",
        "known_at": "2026-09-09T12:00:00Z",
        **updates,
    }
    return data


def adopted_view(identifier: str | UUID, **changes: Any) -> dict[str, Any]:
    return {
        "model": "user_specified",
        "context": context(security_id=identifier, horizon_years=1, **changes).model_dump(
            mode="json"
        ),
        "annualized_return": ".08",
        "rationale": "Explicit owner adoption",
    }


def test_risk_only_views_and_matching_one_year_adoption() -> None:
    payload = construction_payload()
    assert ConstructionRequest.model_validate(payload).assets[0].investor_view is None
    for asset in payload["assets"]:
        asset["investor_view"] = adopted_view(asset["security_id"])
    result = ConstructionRequest.model_validate(payload)
    assert result.assets[0].investor_view is not None


@pytest.mark.parametrize(
    "change",
    [
        {"horizon_years": 3},
        {"return_basis": "price"},
        {"money_basis": "real"},
        {"currency_basis": "base"},
        {"valuation_calendar": "Different cutoff"},
        {"known_at": "2026-09-10T12:00:00Z"},
    ],
)
def test_incompatible_adopted_view_rejected(change: dict) -> None:
    payload = construction_payload()
    identifier = payload["assets"][0]["security_id"]
    c = context(security_id=identifier).model_dump(mode="json")
    payload["assets"][0]["investor_view"] = {
        "context": {**c, "horizon_years": 1, **change},
        "annualized_return": ".08",
        "rationale": "Owner",
    }
    with pytest.raises(ValueError):
        ConstructionRequest.model_validate(payload)


@pytest.mark.parametrize(
    "case",
    [
        "weight_sum",
        "order",
        "duplicates",
        "row_dimension",
        "bounds",
        "strategies",
        "future_history",
        "knowledge",
        "short",
    ],
)
def test_invalid_construction_domains(case: str) -> None:
    payload = construction_payload()
    if case == "weight_sum":
        payload["assets"][0]["current_weight"] = 0.8
    elif case == "order":
        payload["history"]["security_ids"].reverse()
    elif case == "duplicates":
        payload["history"]["security_ids"][1] = payload["history"]["security_ids"][0]
    elif case == "row_dimension":
        payload["history"]["observations"][0]["returns"] = [0.01]
    elif case == "bounds":
        payload["constraints"] = {"max_position_weight": 0.4}
    elif case == "strategies":
        payload["strategies"] = ["current", "current"]
    elif case == "future_history":
        payload["as_of"] = "2019-01-01T00:00:00Z"
    elif case == "knowledge":
        payload["known_at"] = "2020-01-01T00:00:00Z"
    else:
        payload["constraints"] = {"long_only": False}
    with pytest.raises(ValueError):
        ConstructionRequest.model_validate(payload)

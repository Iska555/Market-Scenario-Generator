"""Offline Phase 5 semantic contracts, independently specified before implementation."""

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from uuid import uuid4

import pytest
from pydantic import ValidationError
from src.valuation.contracts import ReturnContext, UserViewRequest
from src.views.expected_return import user_view


def context(**updates: Any) -> ReturnContext:
    return ReturnContext.model_validate(
        {
            "security_id": str(uuid4()),
            "valuation_date": "2026-09-09",
            "horizon_years": 3,
            "return_basis": "total",
            "currency_basis": "local",
            "valuation_currency": "USD",
            "local_currency": "USD",
            "money_basis": "nominal",
            "as_of": "2026-09-09T12:00:00Z",
            "known_at": "2026-09-09T12:00:00Z",
            "valuation_calendar": "XNYS close, calendar-year horizon",
            **updates,
        }
    )


@pytest.mark.parametrize(
    "updates",
    [
        {"horizon_years": 0},
        {"horizon_years": -1},
        {"horizon_years": float("inf")},
        {"horizon_years": float("nan")},
        {"return_basis": "profit"},
        {"currency_basis": "local", "valuation_currency": "EUR"},
        {"as_of": "2026-09-10T00:00:00Z"},
        {"known_at": "2026-09-09"},
    ],
)
def test_invalid_context(updates: dict) -> None:
    with pytest.raises(ValidationError):
        context(**updates)


def test_user_view_preserves_exact_input_and_horizon_round_trip() -> None:
    request = UserViewRequest(
        context=context(), annualized_return=Decimal("0.10"), rationale="Owner view"
    )
    result = user_view(request)
    assert result.returns is not None
    assert result.input.annualized_return is not None
    assert result.returns.cumulative_return == pytest.approx(0.331)
    assert result.input.annualized_return.as_tuple().exponent == -2
    recovered = user_view(
        UserViewRequest(
            context=request.context,
            cumulative_return=Decimal("0.331"),
            rationale="Owner view",
        )
    )
    assert recovered.returns is not None
    assert recovered.returns.annualized_return == pytest.approx(0.1)
    assert result.kind == "investor_view"


@pytest.mark.parametrize(
    "rates",
    [
        {},
        {"annualized_return": "NaN"},
        {"annualized_return": "Infinity"},
        {"annualized_return": "-1.1"},
        {"annualized_return": ".1", "cumulative_return": ".1"},
    ],
)
def test_invalid_user_view(rates: dict) -> None:
    with pytest.raises((ValidationError, ValueError)):
        user_view(UserViewRequest(context=context(), rationale="Owner", **rates))


def test_complete_loss_and_consistent_dual_input() -> None:
    for rates in (
        {"annualized_return": "-1"},
        {"annualized_return": ".1", "cumulative_return": ".331"},
    ):
        result = user_view(
            UserViewRequest.model_validate({"context": context(), "rationale": "Owner", **rates})
        )
        assert result.returns is not None
        assert result.returns.annualized_return == pytest.approx(float(rates["annualized_return"]))
    assert context().known_at.tzinfo == UTC
    assert context().known_at <= datetime(2026, 9, 10, tzinfo=UTC)

"""Research facts require explicit availability, units and reporting context."""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError
from src.research.schemas import ObservationCreate, SecurityCreate


def fact(**changes: object) -> ObservationCreate:
    return ObservationCreate.model_validate(
        {
            "metric": "revenue_growth",
            "value": "0.10",
            "unit": "fraction",
            "period_start": "2024-01-01",
            "period_end": "2024-12-31",
            "period_kind": "annual",
            "reported_at": "2025-02-01T12:00:00Z",
            "fetched_at": "2025-02-02T12:00:00Z",
            "source": "filing",
            "source_record_id": "fact-1",
            "source_document": "filing-2024",
            "basis": "consolidated IFRS",
            **changes,
        }
    )


def test_fact_keeps_reporting_and_availability_dates_distinct() -> None:
    result = fact()
    assert result.reported_at == datetime(2025, 2, 1, 12, tzinfo=UTC)
    assert result.period_end.year == 2024
    assert str(result.value) == "0.10"


@pytest.mark.parametrize(
    "changes",
    [
        {"metric": "invented"},
        {"unit": "ratio"},
        {"value": "NaN"},
        {"value": "Infinity"},
        {"value": "0.00000000001"},
        {"value": "1e30"},
        {"reported_at": "2025-02-01T12:00:00"},
        {"fetched_at": "2025-01-01T00:00:00Z"},
        {"period_end": "2026-12-31"},
        {"period_start": "2025-01-01"},
        {"period_start": None},
        {"source": " "},
        {"basis": " "},
        {"currency": "USD"},
        {"recorded_at": "2020-01-01T00:00:00Z"},
    ],
)
def test_invalid_or_ambiguous_observations_are_rejected(changes: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        fact(**changes)


def test_monetary_observation_requires_currency() -> None:
    with pytest.raises(ValidationError):
        fact(metric="market_cap", unit="currency")
    assert fact(metric="market_cap", unit="currency", currency="USD").currency == "USD"


def test_forward_pe_must_be_explicitly_an_estimate() -> None:
    with pytest.raises(ValidationError):
        fact(metric="forward_pe", unit="ratio")
    assert (
        fact(
            metric="forward_pe", unit="ratio", period_kind="estimate", period_end="2026-12-31"
        ).period_end.year
        == 2026
    )


def test_security_normalizes_label_but_identity_is_not_supplied_by_client() -> None:
    fields = {
        "ticker": " abc ",
        "name": " Example ",
        "exchange": " xnas ",
        "currency": "USD",
        "country": "US",
    }
    security = SecurityCreate.model_validate(fields)
    assert security.ticker == "ABC"
    assert security.exchange == "XNAS"
    assert security.name == "Example"
    with pytest.raises(ValidationError):
        SecurityCreate.model_validate({**fields, "id": "user-ticker"})

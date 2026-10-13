"""Real-source parsing, analytical units, strict failures and private transport."""

import hashlib
import json
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal, localcontext
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from src.factors.source import (
    MAX_BYTES,
    SourceRequest,
    SourceReview,
    review_source,
    verify_source_review,
)

from tests.test_accounting_api import account
from tests.test_research_api import client as client
from tests.test_research_api import configured as configured
from tests.test_research_api import engine as engine

FIXTURE = Path(__file__).parent / "fixtures/french_developed_daily"
IMPORTED = datetime(2026, 10, 13, tzinfo=UTC)
PORTFOLIO = UUID("00000000-0000-0000-0000-000000000001")


def body() -> dict[str, Any]:
    return dict(
        csv_text=(FIXTURE / "excerpt.csv").read_bytes().decode("utf-8"),
        metadata=dict(
            retrieved_at="2026-10-12T14:48:51.017259+00:00", review_note="Real source excerpt"
        ),
        start="1990-07-02",
        end="1990-07-09",
    )


def review(data: dict[str, Any] | None = None, currency: str = "GBP") -> SourceReview:
    return review_source(
        SourceRequest.model_validate(data or body()), PORTFOLIO, currency, IMPORTED
    )


def test_actual_source_fixture_units_range_gap_and_unresolved_readiness() -> None:
    provenance = json.loads((FIXTURE / "provenance.json").read_text(encoding="utf-8"))
    assert (
        hashlib.sha256((FIXTURE / "excerpt.csv").read_bytes()).hexdigest()
        == provenance["excerpt_sha256"]
    )
    result = review()
    assert result.selected_rows == result.total_source_rows == 6
    assert result.database_vintage == "202608"
    assert result.rows[0].returns == dict(
        zip(
            ["Mkt-RF", "SMB", "HML", "RMW", "CMA", "RF"],
            map(Decimal, [".0069", "-.0008", "-.0033", ".0021", "0", ".0003"]),
            strict=True,
        )
    )
    assert result.rows[-1].date == date(1990, 7, 9)
    assert result.calendar_gaps[0].absent_calendar_dates == 2
    assert result.missing_cells == 0 and not result.regression_ready
    assert "historical_publication_availability_unknown" in result.blockers
    assert "source_currency_differs_from_account_currency" in result.blockers
    usd = review(currency="USD")
    assert "source_currency_differs_from_account_currency" not in usd.blockers
    assert not usd.regression_ready
    verify_source_review(SourceReview.model_validate_json(result.model_dump_json()))


def test_sentinel_only_missing_and_extreme_spreads_preserved_with_decimal_precision() -> None:
    data = body()
    data["csv_text"] = (
        data["csv_text"]
        .replace("0.69", "-99.99", 1)
        .replace("-0.08", "-999", 1)
        .replace("-0.33", "123.12345678", 1)
    )
    with localcontext() as context:
        context.prec = 6
        result = review(data)
    assert result.rows[0].returns["Mkt-RF"] is None
    assert result.rows[0].returns["SMB"] == Decimal("-9.99")
    assert result.rows[0].returns["HML"] == Decimal("1.2312345678")
    assert result.missing_cells == 1 and "missing_source_values" in result.blockers


@pytest.mark.parametrize(
    "old,new",
    [
        ("Bloomberg", "Unknown"),
        ("202608", "202613"),
        ("-99.99.", "-999."),
        (",Mkt-RF,SMB", ",SMB,Mkt-RF"),
        ("19900702", "199007"),
        ("19900702", "19900230"),
        ("19900703", "19900702"),
        ("19900703", "19900630"),
        ("0.69", "NaN"),
        ("0.69", "Infinity"),
        ("0.69", "1e5"),
        ("0.69", "private-secret"),
        ("0.69", ""),
        ("0.69", "0.123456789"),
        ("0.69", "0.69,1"),
        (",0.03", ",-100"),
    ],
)
def test_malformed_source_fails_instead_of_dropping_or_guessing(old: str, new: str) -> None:
    data = body()
    assert old in data["csv_text"]
    data["csv_text"] = data["csv_text"].replace(old, new, 1)
    with pytest.raises(ValueError):
        review(data)


def test_full_file_validated_even_outside_selected_window_and_unexpected_footer() -> None:
    data = body()
    data.update(start="1990-07-02", end="1990-07-02")
    data["csv_text"] += "unexpected private footer"
    with pytest.raises(ValueError):
        review(data)
    data["csv_text"] = body()["csv_text"] + '19900710,"unterminated'
    with pytest.raises(ValueError):
        review(data)


def test_empty_outside_partial_windows_and_bom_are_explicit() -> None:
    data = body()
    data.update(start="1990-07-03", end="1990-07-04")
    result = review(data)
    assert result.selected_rows == 2 and result.total_source_rows == 6
    data.update(start="1989-01-01", end="1989-01-02")
    result = review(data)
    assert not result.rows and "no_rows_in_selected_window" in result.blockers
    assert "selected_window_exceeds_source_range" in result.blockers
    data = body()
    data["csv_text"] = "\ufeff" + data["csv_text"]
    assert review(data).rows == review().rows


@pytest.mark.parametrize(
    "patch",
    [
        dict(csv_text="x" * (MAX_BYTES + 1)),
        dict(csv_text="é" * (MAX_BYTES // 2 + 1)),
        dict(csv_text="\ud800"),
        dict(start="1991-01-01"),
        dict(end="2025-01-01"),
        dict(metadata=dict(retrieved_at="2026-01-01", review_note="x")),
        dict(metadata=dict(retrieved_at="2026-01-01T00:00:00Z", review_note=" ")),
        dict(
            metadata=dict(
                source_url="http://private.invalid",
                retrieved_at="2026-01-01T00:00:00Z",
                review_note="x",
            )
        ),
    ],
)
def test_request_bounds_and_metadata(patch: dict[str, Any]) -> None:
    with pytest.raises(ValidationError):
        SourceRequest.model_validate(body() | patch)


def test_publication_is_optional_supported_claim_and_future_dates_rejected() -> None:
    data = body()
    data["metadata"].update(
        published_at="2026-01-01T00:00:00Z", publication_note="Archive receipt reviewed separately"
    )
    assert "declared_publication_requires_independent_review" in review(data).blockers
    for metadata in [dict(published_at="2999-01-01T00:00:00Z"), dict(publication_note="")]:
        with pytest.raises(ValueError):
            review(data | dict(metadata=data["metadata"] | metadata))
    data = body()
    data["metadata"]["retrieved_at"] = "1980-01-01T00:00:00Z"
    with pytest.raises(ValueError, match="Source dates"):
        review(data)
    data["metadata"]["retrieved_at"] = "2999-01-01T00:00:00Z"
    with pytest.raises(ValueError, match="Retrieval"):
        review(data)
    with pytest.raises(ValueError, match="Retrieval"):
        review_source(
            SourceRequest.model_validate(body()), PORTFOLIO, "GBP", datetime(2026, 10, 13)
        )


@pytest.mark.parametrize(
    "field,value",
    [
        ("selected_rows", 4),
        ("receipt_sha256", "a" * 64),
        ("code_sha256", "a" * 64),
        ("submitted_text_sha256", "a" * 64),
        ("blockers", []),
        ("database_vintage", "202601"),
    ],
)
def test_replay_rejects_tampering(field: str, value: Any) -> None:
    result = review().model_dump(mode="json")
    result[field] = value
    with pytest.raises(ValueError, match="differs"):
        verify_source_review(SourceReview.model_validate(result))


def test_private_preview_is_read_only_account_scoped_no_store_and_sanitized(
    client: TestClient,
) -> None:
    portfolio = account(client)
    path = f"/api/factors/portfolios/{portfolio['id']}/source-review"
    response = client.post(path, json=body())
    assert response.status_code == 200, response.text
    saved = SourceReview.model_validate_json(response.content)
    assert saved.portfolio_id == UUID(portfolio["id"]) and saved.account_currency == "GBP"
    verify_source_review(saved)
    assert response.headers["Cache-Control"] == "no-store"
    assert (
        client.get(f"/api/accounting/portfolios/{portfolio['id']}/transactions").json()["total"]
        == 0
    )
    for data, headers, status in [
        (body(), {"X-Research-Key": "bad"}, 401),
        (body() | dict(csv_text="private-secret"), {}, 422),
        (
            body()
            | dict(
                metadata=dict(
                    retrieved_at=(datetime.now(UTC) + timedelta(days=1)).isoformat(),
                    review_note="x",
                )
            ),
            {},
            422,
        ),
    ]:
        response = client.post(path, json=data, headers=headers)
        assert response.status_code == status, response.text
        assert response.headers["Cache-Control"] == "no-store"
        assert "private-secret" not in response.text
    response = client.post(f"/api/factors/portfolios/{uuid4()}/source-review", json=body())
    assert response.status_code == 404 and response.headers["Cache-Control"] == "no-store"
    from src.factors.contracts import FactorEvidence

    with pytest.raises(ValidationError):
        FactorEvidence.model_validate(saved.model_dump(mode="json"))

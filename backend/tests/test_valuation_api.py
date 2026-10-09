"""Private API provenance and point-in-time evidence contracts."""

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

from fastapi.testclient import TestClient

from tests.test_thesis_backend import client as client
from tests.test_thesis_backend import create_thesis
from tests.test_thesis_backend import engine as engine
from tests.test_valuation_contracts import context
from tests.test_valuation_models import assumptions

URL = "/api/research/valuation/evaluate"


def test_private_api_and_security_validation(client: TestClient) -> None:
    body: dict[str, Any] = {
        "model": "user_specified",
        "context": context().model_dump(mode="json"),
        "annualized_return": ".08",
        "rationale": "Owner view",
    }
    assert client.post(URL, json=body, headers={"X-Research-Key": "wrong"}).status_code == 401
    assert client.post(URL, json=body).status_code == 404


def test_replay_manifest_and_revision_availability(client: TestClient) -> None:
    thesis = create_thesis(client)
    cutoff = datetime.now(UTC) + timedelta(seconds=1)
    ctx = context(
        security_id=thesis["security_id"],
        valuation_date=cutoff.date(),
        as_of=cutoff,
        known_at=cutoff,
        thesis_revision_id=thesis["latest"]["id"],
    )
    body: dict[str, Any] = {
        "model": "user_specified",
        "context": ctx.model_dump(mode="json"),
        "annualized_return": "0.0800",
        "rationale": "Owner view",
    }
    response = client.post(URL, json=body)
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["manifest"]["resolved_inputs"]["annualized_return"] == "0.0800"
    assert payload["manifest"]["thesis_revision"]["id"] == thesis["latest"]["id"]
    assert payload["manifest"]["code_sha256"]
    assert payload["manifest"]["library_versions"]["numpy"]
    replay = client.post(URL, json=payload["manifest"]["resolved_inputs"]).json()
    assert replay["result"] == payload["result"]
    assert replay["manifest"]["input_sha256"] == payload["manifest"]["input_sha256"]
    assert response.headers["cache-control"] == "no-store"
    body["context"]["known_at"] = "2000-01-01T00:00:00Z"
    assert client.post(URL, json=body).status_code == 422
    body["context"]["thesis_revision_id"] = str(uuid4())
    assert client.post(URL, json=body).status_code == 422


def test_requested_evidence_cannot_leak_between_securities_or_cutoffs(client: TestClient) -> None:
    thesis = create_thesis(client)
    from tests.test_thesis_backend import SECURITY

    other = client.post("/api/research/securities", json={**SECURITY, "ticker": "BBB"}).json()
    now = datetime.now(UTC) + timedelta(seconds=1)
    from tests.test_research_contracts import fact

    row = client.post(
        f"/api/research/securities/{thesis['security_id']}/fundamentals",
        json={"observations": [fact().model_dump(mode="json")]},
    ).json()[0]
    ctx = context(
        security_id=thesis["security_id"],
        valuation_date=now.date(),
        as_of=now,
        known_at=now,
        observation_ids=[row["id"]],
    )
    body: dict[str, Any] = {
        "model": "user_specified",
        "context": ctx.model_dump(mode="json"),
        "cumulative_return": ".2",
        "rationale": "Owner",
    }
    response = client.post(URL, json=body)
    assert response.status_code == 200, response.text
    assert response.json()["manifest"]["observations"][0]["id"] == row["id"]
    for patch in (
        {"as_of": "2000-01-01T00:00:00Z"},
        {"known_at": "2000-01-01T00:00:00Z"},
        {"security_id": other["id"]},
        {"observation_ids": [str(uuid4())]},
        {"local_currency": "EUR", "valuation_currency": "EUR"},
    ):
        assert (
            client.post(URL, json={**body, "context": {**body["context"], **patch}}).status_code
            == 422
        )


def test_all_operations_dispatch_with_typed_outputs(client: TestClient) -> None:
    from tests.test_valuation_models import sample

    thesis = create_thesis(client)
    now = datetime.now(UTC)
    ctx = context(
        security_id=thesis["security_id"], valuation_date=now.date(), as_of=now, known_at=now
    )
    a = assumptions(price_observed_at=now).model_dump(mode="json")
    samples = sample([0.01, 0.02, 0.03], [0.02, 0.04, 0.06], retrieved_at=now).model_dump(
        mode="json"
    )
    for model, fields, kind in (
        ("fundamental", {"assumptions": a}, "valuation_result"),
        ("reverse", {"assumptions": a, "required_annualized_return": 0.08}, "reverse_valuation"),
        ("historical", {"sample": samples}, "historical_diagnostic"),
        (
            "capm",
            {
                "sample": samples,
                "benchmark": "SYNTH",
                "risk_free_rate": 0.03,
                "equity_risk_premium": 0.05,
                "assumption_source": "Owner",
                "horizon_assumption": "iid_annual_gross_mean",
            },
            "model_estimate",
        ),
        (
            "scenario_set",
            {"scenarios": [{"name": name, "assumptions": a} for name in ("bear", "base", "bull")]},
            "scenario_set",
        ),
    ):
        response = client.post(
            URL, json={"model": model, "context": ctx.model_dump(mode="json"), **fields}
        )
        assert response.status_code == 200, response.text
        assert response.json()["result"]["kind"] == kind
    assert (
        client.post(
            URL,
            json={
                "model": "fundamental",
                "context": ctx.model_dump(mode="json"),
                "assumptions": {**a, "annual_per_share_growth": 1e300},
            },
        ).status_code
        == 422
    )

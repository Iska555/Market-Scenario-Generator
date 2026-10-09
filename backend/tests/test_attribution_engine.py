"""Hand-derived transaction, currency and unit-linking identities."""

from decimal import Decimal, localcontext
from typing import Any
from uuid import UUID

import pytest
from src.accounting.precision import accounting_context
from src.attribution import engine as contribution_engine
from src.attribution.contracts import ContributionReport, ContributionValue
from src.attribution.engine import build_contribution
from src.attribution.replay import verify_contribution

from tests.test_performance_engine import (
    KNOWN,
    SECURITY,
    funded,
    price,
    report,
    request,
    transaction,
)

D = Decimal
SECOND = UUID(int=803)


def rows_by_key(result: ContributionReport) -> dict[str, Any]:
    return {c.key: c for c in result.components}


def security(result: ContributionReport, identity: UUID = SECURITY) -> Any:
    return rows_by_key(result)[f"security:{identity}"]


def checked(rows: Any, req: Any) -> ContributionReport:
    result = build_contribution(report(rows, req))
    assert result.reconciliation.within_tolerance is True
    assert result.reconciliation.residual.value is not None
    assert result.reconciliation.tolerance is not None
    assert abs(result.reconciliation.residual.value) <= result.reconciliation.tolerance
    assert all(
        r.type not in ("DEPOSIT", "WITHDRAWAL")
        for r in rows
        if any(r.id in s.transaction_ids for s in result.segments)
    )
    verify_contribution(ContributionReport.model_validate_json(result.model_dump_json()))
    return result


def fx(rate: str, at: str, currency: str = "USD") -> dict[str, str]:
    return dict(currency=currency, rate=rate, observed_at=at, source="analytical FX")


def foreign_rows() -> Any:
    rows = funded()
    for row in rows:
        row.currency = "USD"
    return rows


def foreign_request(p1: str, p2: str, r1: str, r2: str, **changes: Any) -> Any:
    req = request(p1, p2, expected_version=2, **changes)
    for index, marks in enumerate(req.daily_marks):
        marks.prices[0].currency = "USD"
        from src.accounting.contracts import FX

        marks.fx = [FX.model_validate(fx((r1, r2)[index], f"2025-01-0{index + 1}T20:00:00Z"))]
    return req


def test_two_equities_opening_weights_not_final_weights() -> None:
    rows = [
        transaction(1, "DEPOSIT", "2025-01-01T09:00:00Z", amount="200"),
        transaction(
            2, "BUY", "2025-01-01T10:00:00Z", security_id=SECURITY, quantity="1", price="100"
        ),
        transaction(
            3, "BUY", "2025-01-01T11:00:00Z", security_id=SECOND, quantity="1", price="100"
        ),
    ]
    req = request("100", "120")
    for marks, value in zip(req.daily_marks, ("100", "90"), strict=True):
        mark = marks.prices[0].model_copy(update={"security_id": SECOND, "price": D(value)})
        marks.prices.append(mark)
    result = checked(rows, req)
    assert security(result).total.value == D(".1")
    assert security(result, SECOND).total.value == D("-.05")
    assert result.top_contributors == [f"security:{SECURITY}"]
    assert result.bottom_contributors == [f"security:{SECOND}"]
    assert result.segments[0].opening_positions[0].weight == D(".5")


def test_buy_sell_roundtrip_closed_equity_and_fee_allocation() -> None:
    rows = [
        transaction(1, "DEPOSIT", "2025-01-01T09:00:00Z", amount="200"),
        transaction(
            2,
            "BUY",
            "2025-01-02T10:00:00Z",
            security_id=SECURITY,
            quantity="1",
            price="100",
            fees="2",
        ),
        transaction(
            3,
            "SELL",
            "2025-01-02T11:00:00Z",
            security_id=SECURITY,
            quantity="1",
            price="120",
            fees="3",
        ),
    ]
    result = checked(rows, request(None, None))
    row = security(result)
    assert row.price.value == D(".1") and row.fees.value == D("-.025")
    assert row.total.value == D(".075") and row.pnl_base == 15
    assert not result.performance.daily[-1].nav == 200
    assert result.segments[0].opening_positions == []


def test_partial_sale_new_purchase_and_dividend_in_other_currency() -> None:
    rows = [
        *funded(),
        transaction(
            3, "SELL", "2025-01-02T10:00:00Z", security_id=SECURITY, quantity=".5", price="110"
        ),
        transaction(
            4, "BUY", "2025-01-02T11:00:00Z", security_id=SECURITY, quantity=".25", price="100"
        ),
        transaction(
            5,
            "DIVIDEND",
            "2025-01-02T12:00:00Z",
            security_id=SECURITY,
            amount="5",
        ),
    ]
    # Helper defaults currency; change after strict transaction construction.
    rows[-1].currency = "USD"
    req = request("100", "120", expected_version=5)
    from src.accounting.contracts import FX

    req.daily_marks[-1].fx = [FX.model_validate(fx(".8", "2025-01-02T20:00:00Z"))]
    result = checked(rows, req)
    assert security(result).price.value == D(".2")  # 90 - 100 + 55 - 25
    assert security(result).dividends.value == D(".04")
    assert result.reconciliation.component_total.value == D(".24")


def test_multiple_daily_and_intraday_flows_link_wealth_increments() -> None:
    rows = [
        *funded(),
        transaction(3, "DEPOSIT", "2025-01-02T12:00:00Z", amount="110"),
        transaction(4, "FEE", "2025-01-03T12:00:00Z", amount="10"),
    ]
    req = request(
        "100",
        "120",
        "130",
        expected_version=4,
        flow_marks=[
            dict(transaction_id=str(rows[2].id), prices=[price("110", "2025-01-02T12:00:00Z")])
        ],
    )
    result = checked(rows, req)
    assert security(result).total.value == D(".2")
    assert rows_by_key(result)["account_fees"].total.value == D("-.05")
    assert result.reconciliation.component_total.value == D(".15")
    assert [s.units for s in result.segments] == [100, 200, 200]
    assert [s.linked_total.value for s in result.segments] == [D(".1"), D(".05"), 0]


def test_equal_timestamp_trade_deposit_sequence_determines_exposure() -> None:
    rows = [
        *funded(),
        transaction(
            3, "SELL", "2025-01-02T12:00:00Z", security_id=SECURITY, quantity="1", price="110"
        ),
        transaction(4, "DEPOSIT", "2025-01-02T12:00:00Z", amount="110"),
        transaction(
            5, "BUY", "2025-01-02T12:00:00Z", security_id=SECURITY, quantity="1", price="110"
        ),
    ]
    result = checked(rows, request("100", "120", expected_version=5))
    assert security(result).total.value == D(".15")
    assert result.segments[0].transaction_ids == [rows[2].id]
    assert result.segments[1].transaction_ids == [rows[4].id]
    assert result.segments[1].opening_positions == []


def test_foreign_equity_price_fx_and_interaction_allocation() -> None:
    result = checked(foreign_rows(), foreign_request("100", "110", ".8", ".9"))
    assert security(result).price.value == D(".1125")
    assert security(result).fx.value == D(".125")
    assert result.reconciliation.component_total.value == D(".2375")


def test_foreign_cash_translation_is_not_equity_price_return() -> None:
    rows = [transaction(1, "DEPOSIT", "2025-01-01T09:00:00Z", amount="100")]
    rows[0].currency = "USD"
    req = request(None, None, expected_version=1)
    from src.accounting.contracts import FX

    for mark, rate in zip(req.daily_marks, (".8", ".9"), strict=True):
        mark.fx = [FX.model_validate(fx(rate, mark.date.isoformat() + "T20:00:00Z"))]
    result = checked(rows, req)
    assert rows_by_key(result)["cash:USD"].fx.value == D(".125")
    assert not result.top_contributors


def test_conversion_principal_and_fee_separate_from_cash_fx() -> None:
    rows = [
        transaction(1, "DEPOSIT", "2025-01-01T09:00:00Z", amount="100"),
        transaction(
            2,
            "FX_CONVERSION",
            "2025-01-02T12:00:00Z",
            amount="80",
            to_currency="USD",
            to_amount="100",
            fx_rate="1.25",
            fees="2",
        ),
    ]
    req = request(None, None, expected_version=2)
    from src.accounting.contracts import FX

    req.daily_marks[-1].fx = [FX.model_validate(fx(".9", "2025-01-02T20:00:00Z"))]
    result = checked(rows, req)
    value = rows_by_key(result)["fx_conversion"]
    assert value.fx.value == D(".1") and value.fees.value == D("-.02")
    assert result.reconciliation.component_total.value == D(".08")


def test_sold_currency_needs_end_fx_even_when_phase8_nav_complete() -> None:
    rows = [
        *foreign_rows(),
        transaction(
            3, "SELL", "2025-01-02T10:00:00Z", security_id=SECURITY, quantity="1", price="110"
        ),
        transaction(
            4,
            "FX_CONVERSION",
            "2025-01-02T11:00:00Z",
            amount="110",
            to_currency="USD",
            to_amount="99",
            fx_rate=".9",
        ),
    ]
    rows[2].currency = rows[3].currency = "USD"
    rows[3].to_currency = "GBP"
    req = foreign_request("100", "110", ".8", ".9")
    req.expected_version = 4
    req.daily_marks[-1].prices = []
    req.daily_marks[-1].fx = []
    performance = report(rows, req)
    assert performance.twr.value == pytest.approx(0.2375)
    result = build_contribution(performance)
    assert result.reconciliation.residual.reason == "missing_contribution_fx:USD"
    assert all(c.total.value is None for c in result.components)
    from src.accounting.contracts import FX

    req.daily_marks[-1].fx = [FX.model_validate(fx(".9", "2025-01-02T20:00:00Z"))]
    assert checked(rows, req).reconciliation.within_tolerance


@pytest.mark.parametrize("values", [("100", None, "110"), ("100", "0", "110")])
def test_missing_coverage_or_zero_recovery_is_undefined(values: Any) -> None:
    result = build_contribution(report(funded(), request(*values, expected_version=2)))
    assert result.performance.twr.value is None
    assert result.reconciliation.within_tolerance is None
    assert not result.top_contributors


def test_total_loss_explained_without_resurrecting_capital() -> None:
    result = checked(funded(), request("100", "0", expected_version=2))
    assert security(result).total.value == -1


def test_full_withdrawal_and_refunding_do_not_create_pnl() -> None:
    rows = [
        transaction(1, "DEPOSIT", "2025-01-01T09:00:00Z", amount="100"),
        transaction(2, "WITHDRAWAL", "2025-01-02T12:00:00Z", amount="100"),
        transaction(3, "DEPOSIT", "2025-01-03T12:00:00Z", amount="200"),
    ]
    result = checked(rows, request(None, None, None))
    assert result.reconciliation.component_total.value == 0
    assert [s.units for s in result.segments] == [100, 0, 0, 200]


def test_first_funding_and_empty_portfolio() -> None:
    rows = [transaction(1, "DEPOSIT", "2025-01-02T12:00:00Z", amount="100")]
    assert (
        checked(rows, request(None, None, expected_version=1)).reconciliation.component_total.value
        == 0
    )
    assert (
        build_contribution(
            report([], request(None, None, expected_version=0))
        ).reconciliation.component_total.value
        is None
    )


def test_correction_and_historical_knowledge_preserve_original_economics() -> None:
    rows = [*funded(), transaction(3, "FEE", "2025-01-02T12:00:00Z", amount="10")]
    rows[0].amount = D("200")
    reverse = transaction(4, "REVERSAL", "2025-01-02T12:00:00Z", reverses_id=rows[2].id)
    from datetime import timedelta

    reverse.recorded_at = KNOWN + timedelta(days=1)
    historical = checked([*rows, reverse], request("100", "110", expected_version=4))
    assert historical.reconciliation.component_total.value == 0
    current = checked(
        [*rows, reverse], request("100", "110", expected_version=4, known_at=reverse.recorded_at)
    )
    assert current.reconciliation.component_total.value == D(".05")
    assert "account_fees" not in rows_by_key(current)


def test_multi_period_compounding_is_not_unlinked_sum() -> None:
    result = checked(funded(), request("100", "110", "121", expected_version=2))
    assert security(result).total.value == D(".21")
    assert [s.linked_total.value for s in result.segments] == [D(".1"), D(".11")]


def test_residual_is_visible_and_never_assigned_to_a_security() -> None:
    performance = report(funded(), request("100", "110", expected_version=2))
    performance.twr = performance.twr.model_copy(update={"value": 0.2})
    result = build_contribution(performance)
    assert security(result).total.value == D(".1")
    assert result.reconciliation.residual.value == D(".1")
    assert result.reconciliation.within_tolerance is False


@pytest.mark.parametrize("field", ["result", "methodology", "linking", "fx", "exposure"])
def test_offline_replay_rejects_modified_financial_outputs_and_method(field: str) -> None:
    saved = checked(funded(), request("100", "110", expected_version=2))
    if field == "result":
        saved.components[0].total = ContributionValue(value=D(".5"))
    elif field == "methodology":
        saved.methodology = "other"
    elif field == "linking":
        saved.linking = "other"
    elif field == "fx":
        saved.fx_convention = "other"
    else:
        saved.segments[0].opening_positions[0].quantity = D(10)
    with pytest.raises(ValueError, match="Contribution outputs"):
        verify_contribution(saved)


@pytest.mark.parametrize("value,reason", [(None, None), (D(1), "missing"), (D("NaN"), None)])
def test_undefined_contract_rejects_contradictions(value: Any, reason: Any) -> None:
    with pytest.raises(ValueError):
        ContributionValue(value=value, reason=reason)


def test_decimal_linking_roundoff_retains_visible_tolerance() -> None:
    with localcontext(accounting_context()):
        result = checked(funded(), request("100", "101.2345678901", expected_version=2))
        assert result.reconciliation.tolerance is not None
        assert result.reconciliation.tolerance > 0


def test_capacity_rejects_before_a_large_partial_report(monkeypatch: pytest.MonkeyPatch) -> None:
    performance = report(funded(), request("100", "110", expected_version=2))
    monkeypatch.setattr(contribution_engine, "MAX_CELLS", 1)
    with pytest.raises(ValueError, match="capacity"):
        build_contribution(performance)


def test_trade_at_offset_flow_uses_utc_quote_age() -> None:
    rows = foreign_rows()
    rows.append(transaction(3, "DEPOSIT", "2025-01-03T00:30:00+02:00", amount="88"))
    req = foreign_request("100", "120", ".8", ".8", max_mark_age_days=0)
    req.expected_version = 3
    mark = price("110", "2025-01-02T22:00:00Z")
    mark["currency"] = "USD"
    req.flow_marks = request(
        None,
        None,
        flow_marks=[
            dict(
                transaction_id=str(rows[-1].id),
                prices=[mark],
                fx=[fx(".8", "2025-01-02T22:00:00Z")],
            )
        ],
    ).flow_marks
    result = checked(rows, req)
    assert security(result).total.value == D(".15")
    assert result.segments[0].before_flow_id == rows[-1].id


def test_stale_and_missing_flow_marks_do_not_force_a_zero_contribution() -> None:
    rows = [*funded(), transaction(3, "DEPOSIT", "2025-01-02T12:00:00Z", amount="100")]
    missing = build_contribution(report(rows, request("100", "110")))
    assert missing.reconciliation.component_total.reason == "missing_flow_valuation"
    req = request("100", "110", expected_version=2, max_mark_age_days=0)
    req.daily_marks[-1].prices[0].observed_at = KNOWN.replace(month=1, day=1)
    stale = build_contribution(report(funded(), req))
    assert stale.reconciliation.component_total.reason == "stale_price"


def test_full_withdrawal_after_gains_then_new_funding_preserves_linked_wealth() -> None:
    rows = [
        *funded(),
        transaction(
            3, "SELL", "2025-01-02T10:00:00Z", security_id=SECURITY, quantity="1", price="110"
        ),
        transaction(4, "WITHDRAWAL", "2025-01-02T12:00:00Z", amount="110"),
        transaction(5, "DEPOSIT", "2025-01-03T12:00:00Z", amount="220"),
    ]
    result = checked(rows, request("100", None, None, expected_version=5))
    assert security(result).total.value == D(".1")
    assert result.performance.twr.value == pytest.approx(0.1)
    assert result.segments[-1].units == 200

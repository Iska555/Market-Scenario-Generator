"""Hand-calculated research ratios: no data feeds or binary float arithmetic."""

from collections.abc import Callable
from decimal import Decimal, Overflow, localcontext
from typing import cast

import pytest
from src.research.metrics import CalculationResult, growth, ratio


@pytest.mark.parametrize(
    ("numerator", "denominator", "expected"),
    [
        ("120", "8", "15"),
        ("0.3", "0.1", "3"),
        ("-25", "100", "-0.25"),
        ("0", "100", "0"),
        ("1.23456789", "100", "0.0123456789"),
    ],
)
def test_ratio_preserves_sign_and_decimal_precision(
    numerator: str, denominator: str, expected: str
) -> None:
    assert ratio(Decimal(numerator), Decimal(denominator)) == CalculationResult(
        Decimal(expected), None
    )


@pytest.mark.parametrize("denominator", ["0", "-0", "-5"])
def test_ratio_is_undefined_for_nonpositive_denominator(denominator: str) -> None:
    result = ratio(Decimal("10"), Decimal(denominator))
    assert result.value is None
    assert result.reason


@pytest.mark.parametrize(
    ("current", "previous", "expected"),
    [
        ("125", "100", "0.25"),
        ("75", "100", "-0.25"),
        ("100", "100", "0"),
        ("0", "100", "-1"),
        ("-25", "100", "-1.25"),
        ("0.3", "0.2", "0.5"),
        ("100.00000001", "100", "0.0000000001"),
    ],
)
def test_growth_is_fractional_change_from_positive_base(
    current: str, previous: str, expected: str
) -> None:
    assert growth(Decimal(current), Decimal(previous)) == CalculationResult(Decimal(expected), None)


@pytest.mark.parametrize("previous", ["0", "-0", "-100"])
def test_growth_does_not_invent_growth_from_zero_or_loss_base(previous: str) -> None:
    result = growth(Decimal("100"), Decimal(previous))
    assert result.value is None
    assert result.reason


Calculation = Callable[[Decimal, Decimal], CalculationResult]


@pytest.mark.parametrize("calculate", [ratio, growth])
@pytest.mark.parametrize("invalid", ["NaN", "sNaN", "Infinity", "-Infinity"])
@pytest.mark.parametrize("position", [0, 1])
def test_nonfinite_operands_are_rejected_before_arithmetic(
    calculate: Calculation, invalid: str, position: int
) -> None:
    operands = [Decimal("1"), Decimal("1")]
    operands[position] = Decimal(invalid)
    with pytest.raises(ValueError, match="finite Decimal"):
        calculate(*operands)


@pytest.mark.parametrize("calculate", [ratio, growth])
@pytest.mark.parametrize("invalid", [1, 0.1, "1", None, True])
def test_non_decimal_inputs_are_not_silently_coerced(
    calculate: Calculation, invalid: object
) -> None:
    with pytest.raises(ValueError, match="finite Decimal"):
        calculate(cast(Decimal, invalid), Decimal("1"))
    with pytest.raises(ValueError, match="finite Decimal"):
        calculate(Decimal("1"), cast(Decimal, invalid))


def test_nonfinite_numerator_is_invalid_even_when_denominator_is_undefined() -> None:
    with pytest.raises(ValueError, match="finite Decimal"):
        ratio(Decimal("NaN"), Decimal("0"))
    with pytest.raises(ValueError, match="finite Decimal"):
        growth(Decimal("NaN"), Decimal("0"))


def test_recurring_ratio_uses_decimal_context_without_currency_rounding() -> None:
    with localcontext() as context:
        context.prec = 40
        result = ratio(Decimal("1"), Decimal("3"))
    assert result.value == Decimal("0.3333333333333333333333333333333333333333")


@pytest.mark.parametrize("calculate", [ratio, growth])
@pytest.mark.parametrize("trap_overflow", [True, False])
def test_arithmetic_overflow_cannot_escape_as_a_nonfinite_value(
    calculate: Calculation, trap_overflow: bool
) -> None:
    with localcontext() as context:
        context.Emax = 2
        context.traps[Overflow] = trap_overflow
        with pytest.raises(ValueError, match="Decimal context"):
            calculate(Decimal("999"), Decimal("0.001"))


@pytest.mark.parametrize("trap_overflow", [True, False])
def test_growth_rejects_unrepresentable_change_before_division(trap_overflow: bool) -> None:
    with localcontext() as context:
        context.Emax = 2
        context.traps[Overflow] = trap_overflow
        with pytest.raises(ValueError, match="Decimal context"):
            growth(Decimal("-999"), Decimal("999"))

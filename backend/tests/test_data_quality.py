"""Calendar alignment, provenance and quality flags without magnitude deletion."""

import numpy as np
import pandas as pd
import pytest


def test_mismatched_return_intervals_are_not_correlated() -> None:
    from src.data.preparation import prepare_prices

    # Monday crypto return starts Sunday; equity return starts Friday.
    dates = pd.date_range("2026-01-02", periods=70)
    weekday = dates[dates.weekday < 5]
    stocks = pd.DataFrame({"price": np.arange(len(weekday)) + 100}, index=weekday)
    crypto = pd.DataFrame({"price": np.arange(len(dates)) + 100}, index=dates)
    result = prepare_prices({"STOCK": stocks, "CRYPTO": crypto})
    assert (pd.DatetimeIndex(result.returns.index).weekday != 0).all()
    assert result.excluded_interval_count > 0
    assert list(result.returns.columns) == ["STOCK", "CRYPTO"]


def test_data_flags_preserve_extremes_and_input_is_unmodified() -> None:
    from src.data.preparation import prepare_prices

    frame = pd.DataFrame(
        {"price": [100.0] * 35 + [50.0] * 35}, index=pd.bdate_range("2025-01-01", periods=70)
    )
    before = frame.copy(deep=True)
    result = prepare_prices({"AAA": frame})
    assert len(result.returns) == 69
    assert result.returns.min().iloc[0] == pytest.approx(-np.log(2))
    assert result.diagnostics[0].extreme_return_count == 1
    assert result.diagnostics[0].repeated_price_count == 68
    assert len(result.diagnostics[0].input_sha256) == 64
    pd.testing.assert_frame_equal(frame, before)


def test_invalid_last_price_is_rejected_not_used_as_spot() -> None:
    from src.data.preparation import prepare_prices

    frame = pd.DataFrame({"price": [100.0] * 50 + [0.0]})
    with pytest.raises(ValueError, match="latest"):
        prepare_prices({"AAA": frame})

"""
Unit tests for Silver layer transformations.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

import polars as pl
import pytest

from processing.silver.transform import (
    cast_types,
    calculate_daily_return,
    deduplicate,
    remove_invalid_prices,
    remove_nulls,
    transform_silver,
)


# ---------------------------------------------------------------------------
# cast_types
# ---------------------------------------------------------------------------


def test_cast_types_creates_price_columns(raw_df):
    result = cast_types(raw_df)
    assert "open_price" in result.columns
    assert "close_price" in result.columns
    assert result["close_price"].dtype == pl.Float64


def test_cast_types_strips_and_uppercases_ticker(raw_df):
    df = raw_df.with_columns(pl.lit(" petr4.sa ").alias("ticker"))
    result = cast_types(df)
    assert result["ticker"][0] == "PETR4.SA"


# ---------------------------------------------------------------------------
# remove_nulls
# ---------------------------------------------------------------------------


def test_remove_nulls_drops_rows_with_null_close(raw_df_with_nulls):
    typed = cast_types(raw_df_with_nulls)
    result = remove_nulls(typed)
    # Rows with null close_price must be dropped
    assert result["close_price"].is_null().sum() == 0


def test_remove_nulls_keeps_valid_rows(raw_df):
    typed = cast_types(raw_df)
    before = len(typed)
    result = remove_nulls(typed)
    assert len(result) == before  # no nulls in raw_df


# ---------------------------------------------------------------------------
# remove_invalid_prices
# ---------------------------------------------------------------------------


def test_remove_invalid_prices_drops_zero_close(raw_df):
    typed = cast_types(raw_df)
    # Inject a zero close
    typed = typed.with_columns(
        pl.when(pl.col("ticker") == "ITUB4.SA")
          .then(pl.lit(0.0))
          .otherwise(pl.col("close_price"))
          .alias("close_price")
    )
    result = remove_invalid_prices(typed)
    assert (result["close_price"] > 0).all()


# ---------------------------------------------------------------------------
# deduplicate
# ---------------------------------------------------------------------------


def test_deduplicate_removes_exact_duplicates(raw_df_with_duplicates):
    typed = cast_types(raw_df_with_duplicates)
    # Ensure close_price exists for dedup
    result = deduplicate(typed)
    unique_pairs = result.select(["ticker", "trade_date"]).is_duplicated().sum()
    assert unique_pairs == 0


# ---------------------------------------------------------------------------
# calculate_daily_return
# ---------------------------------------------------------------------------


def test_daily_return_first_row_is_null(raw_df):
    typed = cast_types(raw_df)
    clean = remove_nulls(typed)
    result = calculate_daily_return(clean)

    # First row per ticker should be null
    petr4 = result.filter(pl.col("ticker") == "PETR4.SA").sort("trade_date")
    assert petr4["daily_return"][0] is None


def test_daily_return_formula(raw_df):
    typed = cast_types(raw_df)
    clean = remove_nulls(typed)
    result = calculate_daily_return(clean).sort(["ticker", "trade_date"])

    petr4 = result.filter(pl.col("ticker") == "PETR4.SA").sort("trade_date")
    close_0 = petr4["close_price"][0]
    close_1 = petr4["close_price"][1]
    expected = close_1 / close_0 - 1
    assert abs(petr4["daily_return"][1] - expected) < 1e-9


# ---------------------------------------------------------------------------
# transform_silver (full pipeline)
# ---------------------------------------------------------------------------


def test_transform_silver_no_nulls_in_key_cols(raw_df):
    result = transform_silver(raw_df)
    for col in ["ticker", "trade_date", "close_price", "volume"]:
        assert result[col].is_null().sum() == 0, f"Nulls in {col}"


def test_transform_silver_no_duplicates(raw_df):
    result = transform_silver(raw_df)
    dupes = result.select(["ticker", "trade_date"]).is_duplicated().sum()
    assert dupes == 0


def test_transform_silver_positive_prices(raw_df):
    result = transform_silver(raw_df)
    for col in ["open_price", "high_price", "low_price", "close_price"]:
        assert (result[col] > 0).all(), f"Non-positive values in {col}"


def test_transform_silver_output_columns(raw_df):
    result = transform_silver(raw_df)
    expected = {"ticker", "trade_date", "close_price", "volume", "daily_return", "processed_at"}
    assert expected.issubset(set(result.columns))

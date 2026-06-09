"""
Unit tests for Gold layer aggregations.
"""
from __future__ import annotations

import polars as pl
import pytest

from d_processing.gold.aggregate import (
    build_daily_metrics,
    build_monthly_returns,
    build_portfolio_summary,
)


# ---------------------------------------------------------------------------
# build_daily_metrics
# ---------------------------------------------------------------------------


def test_build_daily_metrics_adds_cum_return(silver_df):
    result = build_daily_metrics(silver_df)
    assert "cum_return" in result.columns


def test_build_daily_metrics_adds_year_month(silver_df):
    result = build_daily_metrics(silver_df)
    assert "year" in result.columns
    assert "month" in result.columns


def test_build_daily_metrics_avg_volume_20d_present(silver_df):
    result = build_daily_metrics(silver_df)
    assert "avg_volume_20d" in result.columns


def test_build_daily_metrics_volatility_present(silver_df):
    result = build_daily_metrics(silver_df)
    assert "volatility_20d" in result.columns


def test_build_daily_metrics_row_count_preserved(silver_df):
    result = build_daily_metrics(silver_df)
    assert len(result) == len(silver_df)


def test_build_daily_metrics_cum_return_starts_near_zero(silver_df):
    """For the first row per ticker, cum_return should be ~0 (no prior period)."""
    result = build_daily_metrics(silver_df).sort(["ticker", "trade_date"])
    first_rows = result.group_by("ticker").agg(pl.col("cum_return").first())
    # First cum_return should be approximately 0 (one period, daily_return ≈ small)
    for val in first_rows["cum_return"].to_list():
        if val is not None:
            assert abs(val) < 0.5, f"First cum_return too large: {val}"


# ---------------------------------------------------------------------------
# build_portfolio_summary
# ---------------------------------------------------------------------------


def test_build_portfolio_summary_one_row_per_ticker(silver_df):
    metrics = build_daily_metrics(silver_df)
    summary = build_portfolio_summary(metrics)
    assert summary["ticker"].n_unique() == silver_df["ticker"].n_unique()
    assert len(summary) == silver_df["ticker"].n_unique()


def test_build_portfolio_summary_has_required_columns(silver_df):
    metrics = build_daily_metrics(silver_df)
    summary = build_portfolio_summary(metrics)
    required = {"ticker", "first_date", "last_date", "total_return", "avg_daily_volume"}
    assert required.issubset(set(summary.columns))


# ---------------------------------------------------------------------------
# build_monthly_returns
# ---------------------------------------------------------------------------


def test_build_monthly_returns_has_month_return(silver_df):
    result = build_monthly_returns(silver_df)
    assert "month_return" in result.columns


def test_build_monthly_returns_grouped_correctly(silver_df):
    result = build_monthly_returns(silver_df)
    # Number of rows = distinct (ticker × year × month) combinations
    expected_groups = silver_df.with_columns(
        pl.col("trade_date").dt.year().alias("year"),
        pl.col("trade_date").dt.month().alias("month"),
    ).select(["ticker", "year", "month"]).n_unique()
    assert len(result) == expected_groups

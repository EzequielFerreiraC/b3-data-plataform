"""
Shared pytest fixtures for the B3 Data Platform test suite.
"""
from __future__ import annotations

from datetime import date
from pathlib import Path

import polars as pl
import pytest


# ---------------------------------------------------------------------------
# Minimal raw (Bronze-like) DataFrame
# ---------------------------------------------------------------------------

@pytest.fixture
def raw_df() -> pl.DataFrame:
    """5 rows of raw OHLCV data as returned by Yahoo Finance ingestion."""
    return pl.DataFrame(
        {
            "ticker":    ["PETR4.SA", "PETR4.SA", "VALE3.SA", "VALE3.SA", "ITUB4.SA"],
            "trade_date": [
                date(2024, 1, 2),
                date(2024, 1, 3),
                date(2024, 1, 2),
                date(2024, 1, 3),
                date(2024, 1, 2),
            ],
            "open":      [28.50, 29.00, 65.10, 66.00, 32.10],
            "high":      [29.20, 29.80, 66.50, 67.20, 33.00],
            "low":       [28.00, 28.50, 64.80, 65.50, 31.90],
            "close":     [29.00, 29.50, 66.00, 67.00, 32.50],
            "adj_close": [29.00, 29.50, 66.00, 67.00, 32.50],
            "volume":    [12_000_000, 13_500_000, 8_000_000, 9_200_000, 5_500_000],
        }
    )


@pytest.fixture
def raw_df_with_nulls(raw_df: pl.DataFrame) -> pl.DataFrame:
    """Same DataFrame but with a null close on row 2."""
    return raw_df.with_columns(
        pl.when(pl.col("trade_date") == date(2024, 1, 3))
          .then(None)
          .otherwise(pl.col("close"))
          .alias("close")
    )


@pytest.fixture
def raw_df_with_duplicates(raw_df: pl.DataFrame) -> pl.DataFrame:
    """DataFrame with one duplicated (ticker, trade_date) row."""
    return pl.concat([raw_df, raw_df.head(1)], how="vertical")


@pytest.fixture
def silver_df(raw_df: pl.DataFrame) -> pl.DataFrame:
    """Full Silver-transformed DataFrame derived from raw_df."""
    from d_processing.silver.transform import transform_silver
    return transform_silver(raw_df)


@pytest.fixture
def tmp_bronze_path(tmp_path: Path) -> Path:
    """Temporary Bronze data directory."""
    p = tmp_path / "bronze"
    p.mkdir()
    return p


@pytest.fixture
def tmp_silver_path(tmp_path: Path) -> Path:
    p = tmp_path / "silver"
    p.mkdir()
    return p

"""
Data quality checks for Silver layer.
All checks are fail-fast assertions — they raise AssertionError on violation.
"""
from __future__ import annotations

import polars as pl

from a_configs.logger import get_logger

logger = get_logger(__name__)


def check_no_nulls(df: pl.DataFrame, columns: list[str]) -> None:
    for col in columns:
        if col not in df.columns:
            continue
        nulls = df[col].is_null().sum()
        assert nulls == 0, f"Column '{col}' has {nulls} null values"


def check_positive_prices(df: pl.DataFrame) -> None:
    price_cols = ["open_price", "high_price", "low_price", "close_price"]
    for col in price_cols:
        if col not in df.columns:
            continue
        non_pos = (df[col] <= 0).sum()
        assert non_pos == 0, f"Column '{col}' has {non_pos} non-positive values"


def check_no_duplicates(df: pl.DataFrame, keys: list[str]) -> None:
    dupes = df.is_duplicated().sum()
    assert dupes == 0, f"DataFrame has {dupes} duplicate rows on keys {keys}"


def check_date_range(df: pl.DataFrame, col: str = "trade_date") -> None:
    import datetime
    today = datetime.date.today()
    max_date = df[col].max()
    assert max_date <= today, f"Future date detected in '{col}': {max_date}"


def run_silver_quality_checks(df: pl.DataFrame) -> pl.DataFrame:
    """
    Run all Silver quality checks. Returns the DataFrame unchanged if all pass.
    Raises AssertionError with a descriptive message on any failure.
    """
    logger.info("Running Silver quality checks", extra={"rows": len(df)})

    check_no_nulls(df, ["ticker", "trade_date", "close_price", "volume"])
    check_positive_prices(df)
    check_no_duplicates(df, ["ticker", "trade_date"])
    check_date_range(df)

    logger.info("All Silver quality checks passed")
    return df

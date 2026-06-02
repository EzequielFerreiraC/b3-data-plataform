"""
Gold layer — analytical aggregations.
Produces ready-to-consume analytical tables from Silver data:
  - daily_metrics: daily OHLCV + return + 20-day rolling volatility and volume
  - portfolio_summary: cumulative return per ticker over the full period
  - sector_performance: (placeholder — requires dim_asset with sector info)
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import polars as pl

from a_configs.logger import get_logger
from a_configs.settings import DATA_PATH_GOLD

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Aggregation functions
# ---------------------------------------------------------------------------


def build_daily_metrics(df: pl.DataFrame) -> pl.DataFrame:
    """
    Enrich each (ticker, trade_date) row with rolling analytical features:
    - avg_volume_20d: 20-trading-day rolling average volume
    - volatility_20d: 20-day rolling stddev of daily_return (annualised × √252)
    - cum_return: cumulative return from the first trade date in the dataset
    - year, month: calendar partitioning helpers
    """
    df = df.sort(["ticker", "trade_date"])

    df = df.with_columns(
        # 20-day rolling average volume
        pl.col("volume")
          .rolling_mean(window_size=20, min_samples=1)
          .over("ticker")
          .alias("avg_volume_20d"),

        # 20-day rolling volatility (annualised)
        (
            pl.col("daily_return")
              .rolling_std(window_size=20, min_samples=2)
              .over("ticker")
            * (252 ** 0.5)
        ).alias("volatility_20d"),

        pl.col("trade_date").dt.year().alias("year"),
        pl.col("trade_date").dt.month().alias("month"),
    )

    # Cumulative return per ticker (compound)
    df = df.with_columns(
        (
            (1 + pl.col("daily_return").fill_null(0))
              .cum_prod()
              .over("ticker")
            - 1
        ).alias("cum_return")
    )

    return df


def build_portfolio_summary(df: pl.DataFrame) -> pl.DataFrame:
    """
    Aggregate to one row per ticker with:
    - first/last trade date
    - total cumulative return
    - average daily volume
    - average annualised volatility
    - max drawdown (peak-to-trough of cum_return)
    """
    return (
        df
        .group_by("ticker")
        .agg(
            pl.col("trade_date").min().alias("first_date"),
            pl.col("trade_date").max().alias("last_date"),
            pl.col("cum_return").last().alias("total_return"),
            pl.col("volume").mean().alias("avg_daily_volume"),
            pl.col("volatility_20d").mean().alias("avg_volatility"),
            pl.col("close_price").max().alias("period_high"),
            pl.col("close_price").min().alias("period_low"),
        )
        .sort("total_return", descending=True)
    )


def build_monthly_returns(df: pl.DataFrame) -> pl.DataFrame:
    """
    Monthly OHLC-style aggregation per ticker:
    uses first open and last close of each month.
    """
    df = df.with_columns(
        pl.col("trade_date").dt.year().alias("year"),
        pl.col("trade_date").dt.month().alias("month"),
    )
    return (
        df
        .sort(["ticker", "trade_date"])
        .group_by(["ticker", "year", "month"])
        .agg(
            pl.col("open_price").first().alias("month_open"),
            pl.col("close_price").last().alias("month_close"),
            pl.col("high_price").max().alias("month_high"),
            pl.col("low_price").min().alias("month_low"),
            pl.col("volume").sum().alias("month_volume"),
            pl.col("daily_return").mean().alias("avg_daily_return"),
        )
        .with_columns(
            ((pl.col("month_close") / pl.col("month_open")) - 1).alias("month_return")
        )
        .sort(["ticker", "year", "month"])
    )


# ---------------------------------------------------------------------------
# I/O helpers
# ---------------------------------------------------------------------------


def write_gold(df: pl.DataFrame, table: str) -> Path:
    """Write a Gold table partitioned by year/month when applicable."""
    if df.is_empty():
        logger.warning("write_gold called with empty DataFrame", extra={"table": table})
        return DATA_PATH_GOLD / table

    output_path = DATA_PATH_GOLD / table
    output_path.mkdir(parents=True, exist_ok=True)

    if "year" in df.columns and "month" in df.columns:
        for (year, month), part_df in df.group_by(["year", "month"]):
            part_dir = output_path / f"year={year}/month={month:02d}"
            part_dir.mkdir(parents=True, exist_ok=True)
            part_df.write_parquet(part_dir / "data.parquet", compression="snappy")
    else:
        df.write_parquet(output_path / "data.parquet", compression="snappy")

    logger.info(
        "Gold write complete",
        extra={"table": table, "rows": len(df), "output": str(output_path)},
    )
    return output_path


def read_gold(table: str) -> pl.DataFrame:
    """Read a Gold table (all partitions)."""
    base = DATA_PATH_GOLD / table
    if not base.exists():
        logger.warning("Gold table not found", extra={"table": table})
        return pl.DataFrame()

    paths = list(base.glob("**/*.parquet"))
    if not paths:
        return pl.DataFrame()

    frames = [pl.read_parquet(p) for p in sorted(paths)]
    df = pl.concat(frames, how="diagonal")
    logger.info("Gold read complete", extra={"table": table, "rows": len(df)})
    return df

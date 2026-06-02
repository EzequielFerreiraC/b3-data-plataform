"""
Silver layer — ETL transformations.
Reads raw Bronze data, applies:
  - Type casting and renaming
  - Deduplication
  - Null removal for key price fields
  - Daily return calculation
  - Timezone-aware processed_at timestamp
Writes clean Parquet partitioned by trade_date.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import polars as pl

from a_configs.logger import get_logger
from a_configs.settings import DATA_PATH_BRONZE, DATA_PATH_SILVER

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Individual transformation steps
# ---------------------------------------------------------------------------


def cast_types(df: pl.DataFrame) -> pl.DataFrame:
    """Ensure all price/volume columns have strict numeric types."""
    return df.with_columns(
        pl.col("open").cast(pl.Float64).alias("open_price"),
        pl.col("high").cast(pl.Float64).alias("high_price"),
        pl.col("low").cast(pl.Float64).alias("low_price"),
        pl.col("close").cast(pl.Float64).alias("close_price"),
        pl.col("adj_close").cast(pl.Float64),
        pl.col("volume").cast(pl.Int64),
        pl.col("trade_date").cast(pl.Date),
        pl.col("ticker").str.strip_chars().str.to_uppercase(),
    )


def remove_nulls(df: pl.DataFrame) -> pl.DataFrame:
    """Drop rows with null values in critical columns."""
    required = ["ticker", "trade_date", "close_price", "volume"]
    before = len(df)
    df = df.drop_nulls(subset=required)
    dropped = before - len(df)
    if dropped:
        logger.warning("Dropped null rows in Silver", extra={"dropped": dropped})
    return df


def remove_invalid_prices(df: pl.DataFrame) -> pl.DataFrame:
    """Remove records where price is zero or negative."""
    before = len(df)
    df = df.filter(
        (pl.col("close_price") > 0)
        & (pl.col("open_price") > 0)
        & (pl.col("high_price") > 0)
        & (pl.col("low_price") > 0)
    )
    dropped = before - len(df)
    if dropped:
        logger.warning("Dropped invalid price rows", extra={"dropped": dropped})
    return df


def deduplicate(df: pl.DataFrame) -> pl.DataFrame:
    """Keep one record per (ticker, trade_date). Latest adj_close wins."""
    before = len(df)
    df = df.sort("adj_close", descending=True).unique(
        subset=["ticker", "trade_date"], keep="first"
    )
    dupes = before - len(df)
    if dupes:
        logger.warning("Removed duplicate rows", extra={"duplicates": dupes})
    return df


def calculate_daily_return(df: pl.DataFrame) -> pl.DataFrame:
    """
    Add ``daily_return`` column: (close_price / prev_close) - 1.
    Window is per ticker, ordered by trade_date.
    """
    return df.with_columns(
        (
            pl.col("close_price")
            / pl.col("close_price").shift(1).over("ticker").sort_by("trade_date")
            - 1
        ).alias("daily_return")
    )


def add_metadata(df: pl.DataFrame) -> pl.DataFrame:
    processed_at = datetime.now(tz=timezone.utc)
    return df.with_columns(pl.lit(processed_at).alias("processed_at"))


def select_silver_columns(df: pl.DataFrame) -> pl.DataFrame:
    cols = [
        "ticker",
        "trade_date",
        "open_price",
        "high_price",
        "low_price",
        "close_price",
        "adj_close",
        "volume",
        "daily_return",
        "processed_at",
    ]
    return df.select([c for c in cols if c in df.columns])


# ---------------------------------------------------------------------------
# Main transform function (pipeline)
# ---------------------------------------------------------------------------


def transform_silver(df: pl.DataFrame) -> pl.DataFrame:
    """
    Apply full Silver ETL pipeline to a raw Bronze DataFrame.
    Steps: cast → remove nulls → remove invalid prices → deduplicate → daily return → metadata.
    """
    return (
        df
        .pipe(cast_types)
        .pipe(remove_nulls)
        .pipe(remove_invalid_prices)
        .pipe(deduplicate)
        .pipe(calculate_daily_return)
        .pipe(add_metadata)
        .pipe(select_silver_columns)
        .sort(["ticker", "trade_date"])
    )


# ---------------------------------------------------------------------------
# I/O helpers
# ---------------------------------------------------------------------------


def write_silver(df: pl.DataFrame) -> Path:
    """Write Silver DataFrame, partitioned by trade_date."""
    if df.is_empty():
        logger.warning("write_silver called with empty DataFrame — skipping")
        return DATA_PATH_SILVER

    DATA_PATH_SILVER.mkdir(parents=True, exist_ok=True)

    for trade_date, partition_df in df.group_by("trade_date"):
        date_str = str(trade_date[0])
        partition_path = DATA_PATH_SILVER / f"trade_date={date_str}"
        partition_path.mkdir(parents=True, exist_ok=True)
        partition_df.write_parquet(partition_path / "data.parquet", compression="snappy")

    unique_dates = df["trade_date"].n_unique()
    logger.info(
        "Silver write complete",
        extra={"rows": len(df), "partitions": unique_dates, "output": str(DATA_PATH_SILVER)},
    )
    return DATA_PATH_SILVER


def read_silver(trade_date: str | None = None) -> pl.DataFrame:
    """Read from Silver layer. Optionally filter by a single trade_date (YYYY-MM-DD)."""
    base = DATA_PATH_SILVER

    if not base.exists():
        logger.error("Silver path not found", extra={"path": str(base)})
        return pl.DataFrame()

    if trade_date:
        paths = [base / f"trade_date={trade_date}" / "data.parquet"]
    else:
        paths = sorted(base.glob("trade_date=*/data.parquet"))

    frames = [pl.read_parquet(p) for p in paths if Path(p).exists()]
    if not frames:
        logger.warning("No Silver files found", extra={"trade_date": trade_date})
        return pl.DataFrame()

    df = pl.concat(frames, how="diagonal")
    logger.info("Silver read complete", extra={"rows": len(df)})
    return df

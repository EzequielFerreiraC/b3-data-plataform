"""
Bronze layer — raw data writer.
Writes ingested data as Parquet, partitioned by trade_date, without any modification.
The Bronze layer is immutable: once written, records are never updated in-place.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import polars as pl

from a_configs.logger import get_logger
from a_configs.settings import DATA_PATH_BRONZE

PARTITION_GLOB = "trade_date_*"

logger = get_logger(__name__)


def write_bronze(df: pl.DataFrame, source: str = "yahoo_finance") -> Path:
    """
    Persist raw ingestion data to the Bronze layer.

    - Adds ``source`` and ``ingested_at`` metadata columns.
    - Writes partitioned Parquet: ``j_data/a_bronze/<source>/trade_date_YYMMDD_HHMM/``.
    - Idempotent: re-running with the same data overwrites the same partition.

    Parameters
    ----------
    df:
        Raw DataFrame with at least columns: ticker, trade_date, close.
    source:
        Logical source identifier (used as the first partition key).

    Returns
    -------
    Path to the root output directory.
    """
    if df.is_empty():
        logger.warning("write_bronze called with empty DataFrame — skipping")
        return DATA_PATH_BRONZE / source

    ingested_at = datetime.now(tz=timezone.utc)

    df = df.with_columns(
        pl.lit(source).alias("source"),
        pl.lit(ingested_at).alias("ingested_at"),
    )

    output_root = DATA_PATH_BRONZE / source
    output_root.mkdir(parents=True, exist_ok=True)

    # Write one Parquet file per trade_date partition
    now = datetime.now(tz=timezone.utc)
    hhmm = now.strftime("%H%M")
    for trade_date, partition_df in df.group_by("trade_date"):
        date_val = trade_date[0]
        if hasattr(date_val, "strftime"):
            yy = date_val.strftime("%y")
            mm = date_val.strftime("%m")
            dd = date_val.strftime("%d")
        else:
            parts = str(date_val).split("-")
            yy = parts[0][2:4]
            mm = parts[1]
            dd = parts[2]
        partition_name = f"trade_date_{yy}{mm}{dd}_{hhmm}"
        partition_path = output_root / partition_name
        partition_path.mkdir(parents=True, exist_ok=True)
        file_path = partition_path / "data.parquet"
        partition_df.write_parquet(file_path, compression="snappy")

    total_rows = len(df)
    unique_dates = df["trade_date"].n_unique()
    logger.info(
        "Bronze write complete",
        extra={
            "source": source,
            "rows": total_rows,
            "partitions": unique_dates,
            "output": str(output_root),
            "ingested_at": ingested_at.isoformat(),
        },
    )
    return output_root


def read_bronze(source: str = "yahoo_finance", trade_date: str | None = None) -> pl.DataFrame:
    """
    Read from the Bronze layer.

    Parameters
    ----------
    source:
        Source identifier (subfolder under j_data/a_bronze/).
    trade_date:
        Optional ISO date string (YYYY-MM-DD) to read a single partition.
        If None, reads all available partitions.
    """
    base = DATA_PATH_BRONZE / source

    if not base.exists():
        logger.error("Bronze path not found", extra={"path": str(base)})
        return pl.DataFrame()

    if trade_date:
        # trade_date comes as YYYY-MM-DD; convert to YYMMDD for glob
        parts = trade_date.split("-")
        yy = parts[0][2:4]
        mm = parts[1]
        dd = parts[2]
        prefix = f"trade_date_{yy}{mm}{dd}_"
        paths = sorted(base.glob(f"{prefix}*/data.parquet"))
    else:
        paths = sorted(base.glob("trade_date_*/data.parquet"))

    if not paths:
        logger.warning("No Bronze files found", extra={"base": str(base), "trade_date": trade_date})
        return pl.DataFrame()

    frames = [pl.read_parquet(p) for p in paths if Path(p).exists()]
    if not frames:
        return pl.DataFrame()

    df = pl.concat(frames, how="diagonal")
    logger.info("Bronze read complete", extra={"rows": len(df), "source": source})
    return df

"""
Silver pipeline — reads Bronze data, applies ETL, runs quality checks, writes Silver.
"""
from __future__ import annotations

from dataclasses import dataclass

import polars as pl

from a_configs.logger import get_logger
from d_processing.bronze.ingest import read_bronze
from d_processing.silver.transform import transform_silver, write_silver
from validation.quality_checks import run_silver_quality_checks

logger = get_logger(__name__)


@dataclass
class SilverPipelineConfig:
    source: str = "yahoo_finance"
    trade_date: str | None = None  # None → process all available Bronze data


class SilverPipeline:
    """
    Read Bronze → ETL → Quality checks → Write Silver.

    Silver contract:
    - All prices are positive floats.
    - No null values in key fields.
    - No duplicate (ticker, trade_date) pairs.
    - daily_return calculated per ticker sorted by trade_date.
    """

    def __init__(self, config: SilverPipelineConfig | None = None):
        self.config = config or SilverPipelineConfig()

    def extract(self) -> pl.DataFrame:
        logger.info("Reading Bronze data", extra={"source": self.config.source, "date": self.config.trade_date})
        return read_bronze(source=self.config.source, trade_date=self.config.trade_date)

    def transform(self, df: pl.DataFrame) -> pl.DataFrame:
        logger.info("Applying Silver transformations", extra={"input_rows": len(df)})
        transformed = transform_silver(df)
        validated = run_silver_quality_checks(transformed)
        logger.info("Transformation complete", extra={"output_rows": len(validated)})
        return validated

    def load(self, df: pl.DataFrame) -> None:
        write_silver(df)

    def run(self) -> pl.DataFrame:
        logger.info("SilverPipeline started")
        raw = self.extract()
        if raw.is_empty():
            logger.warning("Bronze layer is empty — nothing to process")
            return raw
        clean = self.transform(raw)
        self.load(clean)
        logger.info("SilverPipeline finished", extra={"rows": len(clean)})
        return clean

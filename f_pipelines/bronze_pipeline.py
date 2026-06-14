"""
Bronze pipeline — orchestrates ingestion and Bronze write.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta

import polars as pl

from a_configs.logger import get_logger
from a_configs.settings import DEFAULT_TICKERS
from c_ingestion.yahoo_finance import fetch_daily_prices
from d_processing.bronze.ingest import write_bronze

logger = get_logger(__name__)


@dataclass
class BronzePipelineConfig:
    tickers: list[str] = field(default_factory=lambda: DEFAULT_TICKERS)
    start: date = field(default_factory=lambda: date.today() - timedelta(days=365))
    end: date = field(default_factory=date.today)
    source: str = "yahoo_finance"


class BronzePipeline:
    """
    Extract raw B3 price data from Yahoo Finance and write to Bronze layer.

    Bronze contract:
    - No transformation on the data values.
    - Adds only metadata: source identifier and ingestion timestamp.
    - Partitioned by trade_date for efficient downstream reads.
    """

    def __init__(self, config: BronzePipelineConfig | None = None):
        self.config = config or BronzePipelineConfig()

    def extract(self) -> pl.DataFrame:
        logger.info(
            "Bronze extraction started",
            extra={
                "tickers": len(self.config.tickers),
                "start": str(self.config.start),
                "end": str(self.config.end),
            },
        )
        return fetch_daily_prices(
            tickers=self.config.tickers,
            start=self.config.start,
            end=self.config.end,
        )

    def load(self, df: pl.DataFrame) -> None:
        write_bronze(df, source=self.config.source)

    def run(self) -> pl.DataFrame:
        logger.info("BronzePipeline started")
        df = self.extract()
        if df.is_empty():
            logger.warning("Nothing to load — extraction returned empty DataFrame")
            return df
        self.load(df)
        logger.info("BronzePipeline finished", extra={"rows": len(df)})
        return df

"""
Gold pipeline — builds analytical tables from Silver data.
"""
from __future__ import annotations

from dataclasses import dataclass

import polars as pl

from a_configs.logger import get_logger
from d_processing.gold.aggregate import (
    build_daily_metrics,
    build_monthly_returns,
    build_portfolio_summary,
    write_gold,
)
from d_processing.silver.transform import read_silver

logger = get_logger(__name__)


@dataclass
class GoldPipelineConfig:
    trade_date: str | None = None  # None → all available Silver data


class GoldPipeline:
    """
    Read Silver → build analytical Gold tables → persist.

    Tables produced:
    - ``daily_metrics``:     per (ticker, trade_date) with rolling features
    - ``portfolio_summary``: one row per ticker, period aggregates
    - ``monthly_returns``:   monthly OHLC + returns per ticker
    """

    def __init__(self, config: GoldPipelineConfig | None = None):
        self.config = config or GoldPipelineConfig()

    def extract(self) -> pl.DataFrame:
        logger.info("Reading Silver data for Gold pipeline")
        return read_silver(trade_date=self.config.trade_date)

    def transform(self, df: pl.DataFrame) -> dict[str, pl.DataFrame]:
        logger.info("Building Gold tables", extra={"input_rows": len(df)})
        daily = build_daily_metrics(df)
        summary = build_portfolio_summary(daily)
        monthly = build_monthly_returns(df)
        return {
            "daily_metrics": daily,
            "portfolio_summary": summary,
            "monthly_returns": monthly,
        }

    def load(self, tables: dict[str, pl.DataFrame]) -> None:
        for name, df in tables.items():
            write_gold(df, table=name)

    def run(self) -> dict[str, pl.DataFrame]:
        logger.info("GoldPipeline started")
        silver_df = self.extract()
        if silver_df.is_empty():
            logger.warning("Silver layer is empty — nothing to aggregate")
            return {}
        tables = self.transform(silver_df)
        self.load(tables)
        for name, df in tables.items():
            logger.info("Gold table ready", extra={"table": name, "rows": len(df)})
        logger.info("GoldPipeline finished")
        return tables

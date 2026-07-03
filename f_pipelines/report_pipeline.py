"""
Report pipeline — generates PDF reports from Gold layer data.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import polars as pl

from a_configs.logger import get_logger
from a_configs.settings import OUTPUTS_PATH
from d_processing.gold.aggregate import read_gold
from d_processing.report.generate_pdf import generate_report

logger = get_logger(__name__)


@dataclass
class ReportPipelineConfig:
    output_dir: Path | None = None
    report_date: datetime | None = None


class ReportPipeline:
    """
    Read Gold tables → generate PDF report → save to y_outputs/.

    Output: relatorio_YYMMDD_HHMM.pdf
    """

    def __init__(self, config: ReportPipelineConfig | None = None):
        self.config = config or ReportPipelineConfig()

    def extract(self) -> dict[str, pl.DataFrame]:
        logger.info("Reading Gold tables for report generation")
        return {
            "daily_metrics": read_gold("daily_metrics"),
            "portfolio_summary": read_gold("portfolio_summary"),
            "monthly_returns": read_gold("monthly_returns"),
        }

    def generate(self, tables: dict[str, pl.DataFrame]) -> Path:
        report_date = self.config.report_date or datetime.now(timezone.utc)
        output_dir = self.config.output_dir or OUTPUTS_PATH

        return generate_report(
            daily_metrics=tables["daily_metrics"],
            portfolio_summary=tables["portfolio_summary"],
            monthly_returns=tables["monthly_returns"],
            output_dir=output_dir,
            report_date=report_date,
        )

    def run(self) -> Path | None:
        logger.info("ReportPipeline started")

        tables = self.extract()

        # Check if we have data
        if all(df.is_empty() for df in tables.values()):
            logger.warning("All Gold tables are empty — cannot generate report")
            return None

        output_path = self.generate(tables)
        logger.info("ReportPipeline finished", extra={"output": str(output_path)})
        return output_path


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    result = ReportPipeline().run()
    if result:
        print(f"Report generated: {result}")
    else:
        print("No data available for report generation.")

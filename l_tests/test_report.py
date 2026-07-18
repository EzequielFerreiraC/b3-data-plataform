"""
Tests for the PDF report generation pipeline.
"""
from __future__ import annotations

from datetime import date, datetime, timezone
from pathlib import Path

import polars as pl
import pytest


@pytest.fixture
def gold_daily_metrics() -> pl.DataFrame:
    """Minimal Gold daily_metrics DataFrame for testing."""
    dates = [date(2024, 1, d) for d in range(2, 23) if date(2024, 1, d).weekday() < 5]
    rows = []
    for ticker in ["PETR4.SA", "VALE3.SA", "ITUB4.SA"]:
        for i, d in enumerate(dates):
            rows.append({
                "ticker": ticker,
                "trade_date": d,
                "open_price": 30.0 + i * 0.1,
                "high_price": 31.0 + i * 0.1,
                "low_price": 29.0 + i * 0.1,
                "close_price": 30.5 + i * 0.1,
                "volume": 10_000_000 + i * 100_000,
                "daily_return": 0.005 * (1 if i % 2 == 0 else -1),
                "avg_volume_20d": 10_500_000.0,
                "volatility_20d": 0.25 + i * 0.001,
                "cum_return": i * 0.003,
                "year": 2024,
                "month": 1,
            })
    return pl.DataFrame(rows).with_columns(pl.col("trade_date").cast(pl.Date))


@pytest.fixture
def gold_portfolio_summary() -> pl.DataFrame:
    """Minimal Gold portfolio_summary DataFrame."""
    return pl.DataFrame({
        "ticker": ["PETR4.SA", "VALE3.SA", "ITUB4.SA"],
        "first_date": [date(2024, 1, 2)] * 3,
        "last_date": [date(2024, 1, 22)] * 3,
        "total_return": [0.045, 0.032, 0.018],
        "avg_daily_volume": [12_000_000.0, 8_500_000.0, 5_200_000.0],
        "avg_volatility": [0.28, 0.22, 0.19],
        "period_high": [31.50, 68.20, 33.80],
        "period_low": [28.00, 63.50, 31.00],
    }).with_columns(
        pl.col("first_date").cast(pl.Date),
        pl.col("last_date").cast(pl.Date),
    )


@pytest.fixture
def gold_monthly_returns() -> pl.DataFrame:
    """Minimal Gold monthly_returns DataFrame."""
    return pl.DataFrame({
        "ticker": ["PETR4.SA", "VALE3.SA", "ITUB4.SA"] * 2,
        "year": [2024] * 6,
        "month": [1, 1, 1, 2, 2, 2],
        "month_open": [28.5, 65.1, 32.1, 29.5, 67.0, 32.5],
        "month_close": [29.5, 67.0, 32.5, 30.2, 68.5, 33.1],
        "month_high": [30.0, 68.0, 33.5, 31.0, 69.5, 34.0],
        "month_low": [27.5, 64.0, 31.0, 28.8, 66.0, 32.0],
        "month_volume": [250_000_000, 180_000_000, 110_000_000, 230_000_000, 175_000_000, 105_000_000],
        "avg_daily_return": [0.003, 0.002, 0.001, 0.002, 0.003, 0.002],
        "month_return": [0.035, 0.029, 0.012, 0.024, 0.022, 0.018],
    })


class TestReportGeneration:
    """Test PDF report generation."""

    def test_generate_report_creates_pdf(
        self, gold_daily_metrics, gold_portfolio_summary, gold_monthly_returns, tmp_path
    ):
        """Report generation should produce a valid PDF file."""
        from d_processing.d_report.generate_pdf import generate_report

        report_date = datetime(2024, 1, 22, 18, 30, tzinfo=timezone.utc)
        result = generate_report(
            daily_metrics=gold_daily_metrics,
            portfolio_summary=gold_portfolio_summary,
            monthly_returns=gold_monthly_returns,
            output_dir=tmp_path,
            report_date=report_date,
        )

        assert result.exists()
        assert result.name == "report_240122_1830.pdf"
        assert result.stat().st_size > 1000  # PDF should have real content

    def test_generate_report_naming_pattern(
        self, gold_daily_metrics, gold_portfolio_summary, gold_monthly_returns, tmp_path
    ):
        """Verify the YYMMDD_HHMM naming pattern."""
        from d_processing.d_report.generate_pdf import generate_report

        report_date = datetime(2026, 7, 5, 14, 0, tzinfo=timezone.utc)
        result = generate_report(
            daily_metrics=gold_daily_metrics,
            portfolio_summary=gold_portfolio_summary,
            monthly_returns=gold_monthly_returns,
            output_dir=tmp_path,
            report_date=report_date,
        )

        assert result.name == "report_260705_1400.pdf"

    def test_generate_report_empty_data(self, tmp_path):
        """Report should still generate with empty DataFrames (no charts)."""
        from d_processing.d_report.generate_pdf import generate_report

        report_date = datetime(2024, 1, 22, 18, 30, tzinfo=timezone.utc)
        result = generate_report(
            daily_metrics=pl.DataFrame(),
            portfolio_summary=pl.DataFrame(),
            monthly_returns=pl.DataFrame(),
            output_dir=tmp_path,
            report_date=report_date,
        )

        assert result.exists()
        assert result.suffix == ".pdf"

    def test_report_pipeline_no_data(self, tmp_path, monkeypatch):
        """Pipeline should return None when Gold tables are empty."""
        from d_processing.c_gold import aggregate
        from lab_vacation260625.b3_data_plataform_ezequiel_fc.f_pipelines.d_report_pipeline import ReportPipeline, ReportPipelineConfig

        monkeypatch.setattr(aggregate, "read_gold", lambda table: pl.DataFrame())

        cfg = ReportPipelineConfig(output_dir=tmp_path)
        result = ReportPipeline(config=cfg).run()
        assert result is None

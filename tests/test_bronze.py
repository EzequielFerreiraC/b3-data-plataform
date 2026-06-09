"""
Unit tests for Bronze layer (processing/bronze/ingest.py).
"""
from __future__ import annotations

from datetime import date
from pathlib import Path

import polars as pl
import pytest

from d_processing.bronze.ingest import write_bronze, read_bronze
import a_configs.settings as settings


# ---------------------------------------------------------------------------
# write_bronze
# ---------------------------------------------------------------------------


def test_write_bronze_creates_parquet_files(raw_df, tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "DATA_PATH_BRONZE", tmp_path / "bronze")

    from d_processing.bronze import ingest as _module
    monkeypatch.setattr(_module, "DATA_PATH_BRONZE", tmp_path / "bronze")

    out = write_bronze(raw_df, source="test_src")
    parquet_files = list(out.glob("**/*.parquet"))
    assert len(parquet_files) > 0, "Expected at least one Parquet file"


def test_write_bronze_adds_metadata_columns(raw_df, tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "DATA_PATH_BRONZE", tmp_path / "bronze")
    from d_processing.bronze import ingest as _module
    monkeypatch.setattr(_module, "DATA_PATH_BRONZE", tmp_path / "bronze")

    write_bronze(raw_df, source="test_src")
    result = read_bronze_from(tmp_path / "bronze", "test_src")

    assert "source" in result.columns
    assert "ingested_at" in result.columns
    assert result["source"].unique().to_list() == ["test_src"]


def test_write_bronze_partitions_by_trade_date(raw_df, tmp_path, monkeypatch):
    from d_processing.bronze import ingest as _module
    monkeypatch.setattr(_module, "DATA_PATH_BRONZE", tmp_path / "bronze")

    write_bronze(raw_df, source="test_src")
    partitions = list((tmp_path / "bronze" / "test_src").glob("trade_date=*/"))
    # raw_df has 2 unique trade_dates
    assert len(partitions) == 2


def test_write_bronze_empty_df_is_noop(tmp_path, monkeypatch):
    from d_processing.bronze import ingest as _module
    monkeypatch.setattr(_module, "DATA_PATH_BRONZE", tmp_path / "bronze")

    empty = pl.DataFrame()
    write_bronze(empty, source="test_src")
    assert not (tmp_path / "bronze" / "test_src").exists()


# ---------------------------------------------------------------------------
# read_bronze
# ---------------------------------------------------------------------------


def test_read_bronze_returns_all_rows(raw_df, tmp_path, monkeypatch):
    from d_processing.bronze import ingest as _module
    monkeypatch.setattr(_module, "DATA_PATH_BRONZE", tmp_path / "bronze")

    write_bronze(raw_df, source="test_src")
    result = read_bronze_from(tmp_path / "bronze", "test_src")
    # Rows should match (metadata cols added but row count preserved)
    assert len(result) == len(raw_df)


def test_read_bronze_missing_path_returns_empty(tmp_path, monkeypatch):
    from d_processing.bronze import ingest as _module
    monkeypatch.setattr(_module, "DATA_PATH_BRONZE", tmp_path / "bronze")

    result = read_bronze(source="nonexistent")
    assert result.is_empty()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def read_bronze_from(base: Path, source: str) -> pl.DataFrame:
    """Read all parquet files from a temp bronze path."""
    paths = list((base / source).glob("**/*.parquet"))
    frames = [pl.read_parquet(p) for p in paths]
    return pl.concat(frames, how="diagonal") if frames else pl.DataFrame()

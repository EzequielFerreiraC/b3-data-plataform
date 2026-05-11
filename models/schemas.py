"""
Pydantic domain models and Spark schemas for B3 data.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, field_validator
from pyspark.sql.types import (
    DateType,
    DecimalType,
    DoubleType,
    IntegerType,
    LongType,
    StringType,
    StructField,
    StructType,
    TimestampType,
)


# ---------------------------------------------------------------------------
# Pydantic models — used for row-level validation at ingestion boundaries
# ---------------------------------------------------------------------------


class RawTrade(BaseModel):
    """
    Represents a single daily OHLCV record as ingested from Yahoo Finance.
    At Bronze level the values are strings to preserve the original payload.
    """

    ticker: str
    trade_date: date
    open_price: Optional[Decimal] = None
    high_price: Optional[Decimal] = None
    low_price: Optional[Decimal] = None
    close_price: Optional[Decimal] = None
    adj_close: Optional[Decimal] = None
    volume: Optional[int] = None
    source: str = "yahoo_finance"

    @field_validator("ticker")
    @classmethod
    def normalize_ticker(cls, v: str) -> str:
        return v.strip().upper()


class CleanTrade(BaseModel):
    """Silver-layer trade record: all types resolved, no nulls in key fields."""

    ticker: str
    trade_date: date
    open_price: Decimal
    high_price: Decimal
    low_price: Decimal
    close_price: Decimal
    adj_close: Decimal
    volume: int
    daily_return: Optional[Decimal] = None

    @field_validator("close_price", "open_price", "high_price", "low_price", "adj_close")
    @classmethod
    def price_positive(cls, v: Decimal) -> Decimal:
        if v < 0:
            raise ValueError(f"Price must be non-negative, got {v}")
        return v

    @field_validator("volume")
    @classmethod
    def volume_positive(cls, v: int) -> int:
        if v < 0:
            raise ValueError(f"Volume must be non-negative, got {v}")
        return v


# ---------------------------------------------------------------------------
# Spark schemas — declared explicitly; never use inferSchema=True in production
# ---------------------------------------------------------------------------

BRONZE_SCHEMA = StructType(
    [
        StructField("ticker",      StringType(),     nullable=False),
        StructField("trade_date",  DateType(),       nullable=False),
        StructField("open",        DoubleType(),     nullable=True),
        StructField("high",        DoubleType(),     nullable=True),
        StructField("low",         DoubleType(),     nullable=True),
        StructField("close",       DoubleType(),     nullable=True),
        StructField("adj_close",   DoubleType(),     nullable=True),
        StructField("volume",      LongType(),       nullable=True),
        StructField("source",      StringType(),     nullable=False),
        StructField("ingested_at", TimestampType(),  nullable=False),
    ]
)

SILVER_SCHEMA = StructType(
    [
        StructField("ticker",        StringType(),        nullable=False),
        StructField("trade_date",    DateType(),          nullable=False),
        StructField("open_price",    DecimalType(18, 4),  nullable=False),
        StructField("high_price",    DecimalType(18, 4),  nullable=False),
        StructField("low_price",     DecimalType(18, 4),  nullable=False),
        StructField("close_price",   DecimalType(18, 4),  nullable=False),
        StructField("adj_close",     DecimalType(18, 4),  nullable=False),
        StructField("volume",        LongType(),          nullable=False),
        StructField("daily_return",  DoubleType(),        nullable=True),
        StructField("processed_at",  TimestampType(),     nullable=False),
    ]
)

GOLD_DAILY_SCHEMA = StructType(
    [
        StructField("ticker",          StringType(),        nullable=False),
        StructField("trade_date",      DateType(),          nullable=False),
        StructField("close_price",     DecimalType(18, 4),  nullable=False),
        StructField("daily_return",    DoubleType(),        nullable=True),
        StructField("avg_volume_20d",  DoubleType(),        nullable=True),
        StructField("volatility_20d",  DoubleType(),        nullable=True),
        StructField("cum_return",      DoubleType(),        nullable=True),
        StructField("year",            IntegerType(),       nullable=False),
        StructField("month",           IntegerType(),       nullable=False),
    ]
)

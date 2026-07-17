"""
Yahoo Finance ingestion adapter.
Downloads daily OHLCV data for a list of B3 tickers and returns
a Polars DataFrame ready to be written to the Bronze layer.
"""
from __future__ import annotations

import sys
from datetime import date, timedelta

# Block curl_cffi BEFORE yfinance is imported — its native C bindings
# segfault inside Jupyter kernels (especially on WSL).
# yfinance will fall back to the standard `requests` library.
sys.modules["curl_cffi"] = None  # type: ignore[assignment]

import polars as pl
import requests
import yfinance as yf

from a_configs.logger import get_logger
from a_configs.settings import DEFAULT_TICKERS

logger = get_logger(__name__)

# Force yfinance to use `requests` instead of `curl_cffi` which segfaults
# inside Jupyter kernels (especially on WSL).
_session = requests.Session()
_session.headers.update({"User-Agent": "Mozilla/5.0"})


def _safe_download(ticker: str, start: date, end: date) -> pl.DataFrame | None:
    """Download a single ticker; return None on failure."""
    try:
        tk = yf.Ticker(ticker, session=_session)
        raw = tk.history(start=str(start), end=str(end), auto_adjust=False)

        if raw.empty:
            logger.warning("No data returned", extra={"ticker": ticker, "start": str(start)})
            return None

        raw = raw.reset_index()

        # yfinance versions differ on the date column name after reset_index()
        if "Date" not in raw.columns and "index" in raw.columns:
            raw = raw.rename(columns={"index": "Date"})
        if "Date" not in raw.columns and "Datetime" in raw.columns:
            raw = raw.rename(columns={"Datetime": "Date"})

        df = pl.from_pandas(raw).with_columns(
            pl.lit(ticker).alias("ticker"),
            pl.col("Date").cast(pl.Date).alias("trade_date"),
        )

        # Normalise column names to snake_case
        rename_map = {
            "Open": "open",
            "High": "high",
            "Low": "low",
            "Close": "close",
            "Adj Close": "adj_close",
            "Volume": "volume",
        }
        df = df.rename({k: v for k, v in rename_map.items() if k in df.columns})

        # Select only columns that exist (history() may not return Adj Close)
        cols = ["ticker", "trade_date", "open", "high", "low", "close", "volume"]
        if "adj_close" in df.columns:
            cols.insert(6, "adj_close")
        else:
            df = df.with_columns(pl.col("close").alias("adj_close"))
            cols.insert(6, "adj_close")

        df = df.select(cols)
        return df

    except Exception as exc:
        logger.error("Download failed", extra={"ticker": ticker, "error": str(exc)})
        return None


def fetch_daily_prices(
    tickers: list[str] | None = None,
    start: date | None = None,
    end: date | None = None,
) -> pl.DataFrame:
    """
    Fetch daily OHLCV prices for a list of tickers from Yahoo Finance.

    Parameters
    ----------
    tickers:
        List of Yahoo Finance symbols. Defaults to DEFAULT_TICKERS.
    start:
        First date to fetch (inclusive). Defaults to 365 days before *end*.
    end:
        Last date to fetch (exclusive). Defaults to today.

    Returns
    -------
    pl.DataFrame with columns:
        ticker, trade_date, open, high, low, close, adj_close, volume
    """
    if end is None:
        end = date.today()
    if start is None:
        start = end - timedelta(days=365)
    if tickers is None:
        tickers = DEFAULT_TICKERS

    logger.info(
        "Starting Yahoo Finance ingestion",
        extra={"tickers": len(tickers), "start": str(start), "end": str(end)},
    )

    frames: list[pl.DataFrame] = []
    for ticker in tickers:
        df = _safe_download(ticker, start, end)
        if df is not None:
            frames.append(df)

    if not frames:
        logger.error("No data fetched — returning empty DataFrame")
        return pl.DataFrame(
            schema={
                "ticker": pl.Utf8,
                "trade_date": pl.Date,
                "open": pl.Float64,
                "high": pl.Float64,
                "low": pl.Float64,
                "close": pl.Float64,
                "adj_close": pl.Float64,
                "volume": pl.Int64,
            }
        )

    result = pl.concat(frames, how="vertical")
    logger.info("Ingestion complete", extra={"total_rows": len(result), "tickers_ok": len(frames)})
    return result

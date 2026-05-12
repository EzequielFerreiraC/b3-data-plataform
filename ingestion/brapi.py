"""
BRAPI (https://brapi.dev) ingestion adapter.
Provides an alternative source for B3 data with Brazilian-centric fields.
Requires a BRAPI token set in B3_API_TOKEN env var.
"""
from __future__ import annotations

from datetime import date, timedelta
from typing import Any

import polars as pl
import requests

from configs.logger import get_logger
from configs.settings import B3_API_TOKEN

logger = get_logger(__name__)

_BASE_URL = "https://brapi.dev/api"
_TIMEOUT = 30  # seconds


def _request(path: str, params: dict[str, Any] | None = None) -> dict:
    """Execute a GET request to BRAPI, raising on HTTP errors."""
    headers: dict[str, str] = {}
    if B3_API_TOKEN:
        headers["Authorization"] = f"Bearer {B3_API_TOKEN}"

    url = f"{_BASE_URL}{path}"
    resp = requests.get(url, params=params, headers=headers, timeout=_TIMEOUT)
    resp.raise_for_status()
    return resp.json()


def fetch_quote(ticker: str) -> dict | None:
    """Fetch current quote for a single B3 ticker (without '.SA' suffix)."""
    try:
        data = _request(f"/quote/{ticker}", params={"range": "1d", "interval": "1d"})
        results = data.get("results", [])
        return results[0] if results else None
    except requests.HTTPError as exc:
        logger.error("BRAPI HTTP error", extra={"ticker": ticker, "status": exc.response.status_code})
        return None
    except Exception as exc:
        logger.error("BRAPI fetch failed", extra={"ticker": ticker, "error": str(exc)})
        return None


def fetch_historical_prices(
    ticker: str,
    start: date | None = None,
    end: date | None = None,
) -> pl.DataFrame | None:
    """
    Fetch historical OHLCV data for a single B3 ticker via BRAPI.

    Parameters
    ----------
    ticker:
        B3 ticker WITHOUT the '.SA' suffix (e.g. 'PETR4').
    start, end:
        Date range. Defaults to last 365 days.

    Returns
    -------
    pl.DataFrame or None if the request fails.
    """
    if end is None:
        end = date.today()
    if start is None:
        start = end - timedelta(days=365)

    try:
        data = _request(
            f"/quote/{ticker}",
            params={
                "range": "custom",
                "interval": "1d",
                "from": str(start),
                "to": str(end),
            },
        )
        results = data.get("results", [])
        if not results or "historicalDataPrice" not in results[0]:
            logger.warning("No historical data", extra={"ticker": ticker})
            return None

        rows = results[0]["historicalDataPrice"]
        df = pl.DataFrame(rows).with_columns(
            pl.lit(ticker + ".SA").alias("ticker"),
            pl.col("date").str.to_date("%Y-%m-%d").alias("trade_date"),
        )

        rename_map = {
            "open": "open",
            "high": "high",
            "low": "low",
            "close": "close",
            "adjustedClose": "adj_close",
            "volume": "volume",
        }
        df = df.rename({k: v for k, v in rename_map.items() if k in df.columns})
        existing = [c for c in ["ticker", "trade_date", "open", "high", "low", "close", "adj_close", "volume"] if c in df.columns]
        return df.select(existing)

    except Exception as exc:
        logger.error("BRAPI historical fetch failed", extra={"ticker": ticker, "error": str(exc)})
        return None

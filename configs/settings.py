"""
Central settings loaded from environment variables / .env file.
All pipeline components must import from here — never read os.environ directly.
"""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Base paths
# ---------------------------------------------------------------------------
ROOT_DIR: Path = Path(__file__).resolve().parent.parent

DATA_PATH_BRONZE: Path = ROOT_DIR / os.getenv("DATA_PATH_BRONZE", "data/bronze")
DATA_PATH_SILVER: Path = ROOT_DIR / os.getenv("DATA_PATH_SILVER", "data/silver")
DATA_PATH_GOLD: Path = ROOT_DIR / os.getenv("DATA_PATH_GOLD", "data/gold")
LOGS_PATH: Path = ROOT_DIR / os.getenv("LOGS_PATH", "logs")

# ---------------------------------------------------------------------------
# MinIO / S3
# ---------------------------------------------------------------------------
MINIO_ENDPOINT: str = os.getenv("MINIO_ENDPOINT", "http://localhost:9000")
MINIO_ACCESS_KEY: str = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
MINIO_SECRET_KEY: str = os.getenv("MINIO_SECRET_KEY", "minioadmin")
MINIO_BUCKET_BRONZE: str = os.getenv("MINIO_BUCKET_BRONZE", "b3-bronze")
MINIO_BUCKET_SILVER: str = os.getenv("MINIO_BUCKET_SILVER", "b3-silver")
MINIO_BUCKET_GOLD: str = os.getenv("MINIO_BUCKET_GOLD", "b3-gold")

# ---------------------------------------------------------------------------
# Spark
# ---------------------------------------------------------------------------
SPARK_APP_NAME: str = os.getenv("SPARK_APP_NAME", "b3-data-platform")
SPARK_MASTER: str = os.getenv("SPARK_MASTER", "local[*]")

# ---------------------------------------------------------------------------
# B3 / Data
# ---------------------------------------------------------------------------
B3_API_TOKEN: str | None = os.getenv("B3_API_TOKEN")

# Default B3 tickers to track (Yahoo Finance format: ticker + ".SA")
DEFAULT_TICKERS: list[str] = [
    "PETR4.SA",  # Petrobras PN
    "VALE3.SA",  # Vale ON
    "ITUB4.SA",  # Itaú Unibanco PN
    "BBDC4.SA",  # Bradesco PN
    "ABEV3.SA",  # Ambev ON
    "WEGE3.SA",  # WEG ON
    "RENT3.SA",  # Localiza ON
    "MGLU3.SA",  # Magazine Luiza ON
    "BPAC11.SA", # BTG Pactual UNT
    "LREN3.SA",  # Lojas Renner ON
    "BBAS3.SA",  # Banco do Brasil ON
    "RADL3.SA",  # Raia Drogasil ON
]

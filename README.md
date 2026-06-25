# B3 Data Platform

> Financial data lakehouse for B3 (Brazilian Stock Exchange) using the **Medallion Architecture** (Bronze -> Silver -> Gold).

---

## Stack

| Component       | Tool                        | Purpose                              |
|-----------------|-----------------------------|--------------------------------------|
| Processing      | **Polars** + **PySpark**    | Transformations (medium & large vol) |
| Orchestration   | **Apache Airflow**          | DAG per layer, retry & sensors       |
| Storage         | **MinIO** (local S3)        | Object storage for Parquet files     |
| Notebooks       | **JupyterLab**              | Interactive exploration               |
| Visualisation   | **Plotly** + **Seaborn**    | Charts inside notebooks              |
| Data source     | **Yahoo Finance** / BRAPI   | B3 daily OHLCV prices                |
| Containerisation| **Docker Compose**          | Full local environment               |

---

## Project Structure

```
b3-data/
├── configs/            # Settings, Spark factory, MinIO client, JSON logger
├── ingestion/          # Yahoo Finance + BRAPI adapters
├── processing/
│   ├── bronze/         # Raw writer / reader
│   ├── silver/         # ETL transformations
│   └── gold/           # Aggregations (daily metrics, portfolio, monthly)
├── models/             # Pydantic models + Spark schemas
├── pipelines/          # Bronze / Silver / Gold pipeline classes
├── validation/         # Quality checks (fail-fast assertions)
├── dags/               # Airflow DAGs (Bronze → Silver → Gold chain)
├── notebooks/          # 01 Bronze · 02 Silver · 03 Gold · 04 Exploration
├── tests/              # pytest unit tests + conftest fixtures
├── j_data/             # Local Parquet store (bronze / silver / gold)
├── k_logs/             # Runtime JSON / log files
├── docker-compose.yml  # MinIO + PostgreSQL + Airflow + JupyterLab
└── requirements.txt
```

---

## Quick Start

### 1 — Local (no Docker)

```bash
# Create virtual environment
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Copy env file
cp .env.example .env

# Run full pipeline (Bronze → Silver → Gold)
python - <<'EOF'
from pipelines.bronze_pipeline import BronzePipeline
from pipelines.silver_pipeline import SilverPipeline
from pipelines.gold_pipeline import GoldPipeline

BronzePipeline().run()
SilverPipeline().run()
GoldPipeline().run()
EOF

# Start JupyterLab
jupyter lab notebooks/
```

### 2 — Docker Compose (full stack)

```bash
docker compose up -d

# Services:
#   JupyterLab  →  http://localhost:8888  (token: b3data)
#   Airflow UI  →  http://localhost:8080
#   MinIO UI    →  http://localhost:9001  (user/pass: minioadmin)
```

### 3 — Run tests

```bash
pytest -v
```

---

## Notebooks

| # | Notebook | Description |
|---|---|---|
| 01 | `01_bronze_ingestion.ipynb` | Ingest raw prices, inspect Bronze layer |
| 02 | `02_silver_etl.ipynb`       | Step-by-step ETL, quality checks        |
| 03 | `03_gold_analytics.ipynb`   | Cumulative return, volatility, heatmaps |
| 04 | `04_exploration.ipynb`      | Correlation, Bollinger Bands, Spark SQL |

---

## Airflow DAGs

| DAG | Schedule | Description |
|---|---|---|
| `b3_bronze_ingestion` | Mon–Fri 22:00 UTC | Fetch prices → Bronze |
| `b3_silver_etl`       | Mon–Fri 22:30 UTC | Bronze → Silver ETL   |
| `b3_gold_aggregation` | Mon–Fri 23:00 UTC | Silver → Gold tables  |

DAGs use `ExternalTaskSensor` so Silver waits for Bronze and Gold waits for Silver.

---

## Tracked Tickers (default)

`PETR4` · `VALE3` · `ITUB4` · `BBDC4` · `ABEV3` · `WEGE3` · `RENT3` · `MGLU3` · `BPAC11` · `LREN3` · `BBAS3` · `RADL3`

Override via `DEFAULT_TICKERS` in `configs/settings.py` or pass a custom list to whichever pipeline you run.

---


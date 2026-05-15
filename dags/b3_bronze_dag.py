"""
Airflow DAG — Bronze layer ingestion.
Schedule: daily at 19:00 BRT (22:00 UTC) after B3 market close.
"""
from __future__ import annotations

from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator

DEFAULT_ARGS = {
    "owner": "data-engineering",
    "depends_on_past": False,
    "retries": 3,
    "retry_delay": timedelta(minutes=5),
    "email_on_failure": False,
    "email_on_retry": False,
}


def run_bronze_pipeline(**context) -> None:
    """Task callable — imported inside function to avoid import at DAG parse time."""
    from pipelines.bronze_pipeline import BronzePipeline, BronzePipelineConfig
    from datetime import date

    logical_date: date = context["logical_date"].date()
    cfg = BronzePipelineConfig(
        start=logical_date,
        end=logical_date + timedelta(days=1),
    )
    pipeline = BronzePipeline(config=cfg)
    pipeline.run()


with DAG(
    dag_id="b3_bronze_ingestion",
    description="Ingest raw B3 daily prices from Yahoo Finance into Bronze layer",
    schedule="0 22 * * 1-5",  # Mon–Fri at 22:00 UTC (19:00 BRT)
    start_date=datetime(2024, 1, 2),
    catchup=False,
    max_active_runs=1,
    default_args=DEFAULT_ARGS,
    tags=["b3", "bronze", "ingestion"],
) as dag:

    ingest_task = PythonOperator(
        task_id="run_bronze_pipeline",
        python_callable=run_bronze_pipeline,
    )

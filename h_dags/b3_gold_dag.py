"""
Airflow DAG — Gold aggregations.
Runs after Silver ETL completes for the day.
"""
from __future__ import annotations

from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.sensors.external_task import ExternalTaskSensor

DEFAULT_ARGS = {
    "owner": "data-engineering",
    "depends_on_past": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=10),
    "email_on_failure": False,
}


def run_gold_pipeline(**context) -> None:
    from datetime import date
    from f_pipelines.gold_pipeline import GoldPipeline, GoldPipelineConfig

    logical_date: date = context["logical_date"].date()
    cfg = GoldPipelineConfig(trade_date=str(logical_date))
    GoldPipeline(config=cfg).run()


with DAG(
    dag_id="b3_gold_aggregation",
    description="Aggregate Silver data into Gold analytical tables",
    schedule="0 23 * * 1-5",  # 1.5 h after Bronze DAG
    start_date=datetime(2024, 1, 2),
    catchup=False,
    max_active_runs=1,
    default_args=DEFAULT_ARGS,
    tags=["b3", "gold", "aggregation"],
) as dag:

    wait_for_silver = ExternalTaskSensor(
        task_id="wait_for_silver_etl",
        external_dag_id="b3_silver_etl",
        external_task_id="run_silver_pipeline",
        timeout=3600,
        mode="reschedule",
    )

    gold_task = PythonOperator(
        task_id="run_gold_pipeline",
        python_callable=run_gold_pipeline,
    )

    wait_for_silver >> gold_task

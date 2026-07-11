"""
Airflow DAG — Silver ETL.
Runs after Bronze ingestion completes for the day.
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


def run_silver_pipeline(**context) -> None:
    from datetime import date
    from f_pipelines.b_silver_pipeline import SilverPipeline, SilverPipelineConfig

    logical_date: date = context["logical_date"].date()
    cfg = SilverPipelineConfig(trade_date=str(logical_date))
    SilverPipeline(config=cfg).run()


with DAG(
    dag_id="b_b3_silver_etl",
    description="ETL transformations: Bronze → Silver with quality checks",
    schedule="30 22 * * 1-5",  # 30 min after Bronze DAG
    start_date=datetime(2024, 1, 2),
    catchup=False,
    max_active_runs=1,
    default_args=DEFAULT_ARGS,
    tags=["b3", "silver", "etl"],
) as dag:

    wait_for_bronze = ExternalTaskSensor(
        task_id="wait_for_bronze_ingestion",
        external_dag_id="a_b3_bronze_ingestion",
        external_task_id="run_bronze_pipeline",
        execution_delta=timedelta(minutes=30),  # Bronze runs 30 min before Silver
        timeout=3600,
        mode="reschedule",
    )

    silver_task = PythonOperator(
        task_id="run_silver_pipeline",
        python_callable=run_silver_pipeline,
    )

    wait_for_bronze >> silver_task

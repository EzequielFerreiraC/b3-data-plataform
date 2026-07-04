"""
Airflow DAG — PDF Report Generation.
Runs after Gold aggregations complete for the day.
"""
from __future__ import annotations

from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.sensors.external_task import ExternalTaskSensor

DEFAULT_ARGS = {
    "owner": "data-engineering",
    "depends_on_past": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
    "email_on_failure": False,
}


def run_report_pipeline(**context) -> None:
    from datetime import datetime as dt, timezone
    from pathlib import Path
    from f_pipelines.report_pipeline import ReportPipeline, ReportPipelineConfig

    logical_date = context["logical_date"]
    cfg = ReportPipelineConfig(
        output_dir=Path("/opt/airflow/outputs"),
        report_date=logical_date.replace(tzinfo=timezone.utc),
    )
    result = ReportPipeline(config=cfg).run()
    if result:
        context["ti"].xcom_push(key="report_path", value=str(result))


with DAG(
    dag_id="b3_report_generation",
    description="Generate PDF analytical report from Gold layer data",
    schedule="30 23 * * 1-5",  # 30 min after Gold DAG
    start_date=datetime(2024, 1, 2),
    catchup=False,
    max_active_runs=1,
    default_args=DEFAULT_ARGS,
    tags=["b3", "report", "pdf"],
) as dag:

    wait_for_gold = ExternalTaskSensor(
        task_id="wait_for_gold_aggregation",
        external_dag_id="b3_gold_aggregation",
        external_task_id="run_gold_pipeline",
        timeout=3600,
        mode="reschedule",
    )

    report_task = PythonOperator(
        task_id="generate_pdf_report",
        python_callable=run_report_pipeline,
    )

    wait_for_gold >> report_task

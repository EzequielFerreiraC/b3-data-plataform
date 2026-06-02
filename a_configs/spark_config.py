"""
Spark session factory with Delta Lake support.
Use create_spark_session() everywhere instead of building SparkSession inline.
"""
from __future__ import annotations

from pyspark.sql import SparkSession

from a_configs.settings import SPARK_APP_NAME, SPARK_MASTER


def create_spark_session(app_name: str = SPARK_APP_NAME) -> SparkSession:
    """
    Build a SparkSession pre-configured with:
    - Delta Lake extensions
    - Adaptive Query Execution (AQE)
    - Correct date rebase mode for Parquet
    """
    # If a previous session was stopped, getOrCreate() would return the dead
    # instance instead of creating a new one.  Clear the stale reference first.
    _cached = SparkSession._instantiatedSession
    if _cached is not None:
        _sess = _cached() if callable(_cached) else _cached
        if _sess is not None and _sess.sparkContext._jsc is None:
            SparkSession._instantiatedSession = None

    return (
        SparkSession.builder
        .appName(app_name)
        .master(SPARK_MASTER)
        # Delta Lake
        .config("spark.jars.packages", "io.delta:delta-spark_2.12:3.1.0")
        .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension")
        .config(
            "spark.sql.catalog.spark_catalog",
            "org.apache.spark.sql.delta.catalog.DeltaCatalog",
        )
        # Performance
        .config("spark.sql.adaptive.enabled", "true")
        .config("spark.sql.adaptive.coalescePartitions.enabled", "true")
        .config("spark.sql.adaptive.skewJoin.enabled", "true")
        # Compatibility
        .config("spark.sql.parquet.datetimeRebaseModeInWrite", "CORRECTED")
        .config("spark.sql.parquet.int96RebaseModeInWrite", "CORRECTED")
        # Logging verbosity
        .config("spark.log.level", "WARN")
        .getOrCreate()
    )

import os, sys, traceback
os.environ.setdefault("JAVA_HOME", r"C:\Users\efcardoso\java\jdk-17.0.19+10")
os.environ.setdefault("PYSPARK_SUBMIT_ARGS", "--master local[*] pyspark-shell")
print("JAVA_HOME =", os.environ.get("JAVA_HOME"))
print("PYTHONPATH =", os.environ.get("PYTHONPATH"))
print("python   =", sys.executable)

try:
    from pyspark.sql import SparkSession
    spark = (
        SparkSession.builder
        .appName("diag")
        .master("local[*]")
        .config("spark.driver.host", "127.0.0.1")
        .config("spark.driver.bindAddress", "127.0.0.1")
        .getOrCreate()
    )
    print("Spark version:", spark.version)
    spark.stop()
except Exception:
    traceback.print_exc()

#!/usr/bin/env python3
"""Run full B3 data pipeline: Bronze -> Silver -> Gold -> Report"""

from a_configs.logger import get_logger
from f_pipelines.a_bronze_pipeline import BronzePipeline
from f_pipelines.b_silver_pipeline import SilverPipeline
from f_pipelines.c_gold_pipeline import GoldPipeline
from f_pipelines.d_report_pipeline import ReportPipeline

logger = get_logger(__name__)


def main():
    """Execute all pipeline stages"""
    
    print("=" * 80)
    print("B3 DATA PLATFORM - FULL PIPELINE EXECUTION")
    print("=" * 80)
    
    try:
        # Stage 1: Bronze
        print("\n[1/4] Running Bronze Pipeline (Data Ingestion)...")
        bronze_pipeline = BronzePipeline()
        bronze_df = bronze_pipeline.run()
        print(f"✓ Bronze complete: {len(bronze_df)} rows ingested")
        
        # Stage 2: Silver
        print("\n[2/4] Running Silver Pipeline (Data Transformation)...")
        silver_pipeline = SilverPipeline()
        silver_result = silver_pipeline.run()
        print(f"✓ Silver complete")
        
        # Stage 3: Gold
        print("\n[3/4] Running Gold Pipeline (Analytics & Aggregation)...")
        gold_pipeline = GoldPipeline()
        gold_result = gold_pipeline.run()
        print(f"✓ Gold complete")
        
        # Stage 4: Report
        print("\n[4/4] Running Report Pipeline (PDF Generation)...")
        report_pipeline = ReportPipeline()
        report_path = report_pipeline.run()
        print(f"✓ Report complete: {report_path}")
        
        print("\n" + "=" * 80)
        print("PIPELINE EXECUTION COMPLETE!")
        print("=" * 80)
        
    except Exception as e:
        logger.error(f"Pipeline failed: {e}", exc_info=True)
        print(f"\n❌ Pipeline failed: {e}")
        raise


if __name__ == "__main__":
    main()

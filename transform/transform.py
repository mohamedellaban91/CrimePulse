import os
import sys
import pandas as pd
from datetime import datetime

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from logger import get_logger, log_to_db
from transform.cleaners import (
    fix_dtypes,
    drop_duplicates,
    drop_unnecessary_columns,
    handle_missing
)
from transform.validators import validate_columns, validate_rows

logger = get_logger(__name__)

BRONZE_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'bronze')
SILVER_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'silver')
os.makedirs(SILVER_PATH, exist_ok=True)


def transform(filename: str = 'crimes_initial.parquet') -> pd.DataFrame:
    start = datetime.now()
    try:
        logger.info(f"Starting TRANSFORM: {filename}")

        input_path = os.path.join(BRONZE_PATH, filename)
        df = pd.read_parquet(input_path)
        logger.info(f"Loaded {len(df)} rows from Bronze")

        if len(df) == 0:
            logger.warning("No rows to transform, skipping...")
            log_to_db('transform', 'success', rows_fetched=0, duration_sec=0)
            return df

        if not validate_columns(df):
            raise ValueError("Column validation failed")
        if not validate_rows(df):
            raise ValueError("Row validation failed")

        df = fix_dtypes(df)
        df = drop_duplicates(df)
        df = drop_unnecessary_columns(df)
        df = handle_missing(df)

        output_path = os.path.join(SILVER_PATH, filename)
        df.to_parquet(output_path, index=False)

        duration = round((datetime.now() - start).total_seconds(), 2)
        logger.info(f"Transform completed: {len(df)} rows → {output_path}")
        log_to_db('transform', 'success', rows_fetched=len(df), rows_loaded=len(df), duration_sec=duration)
        return df

    except Exception as e:
        duration = round((datetime.now() - start).total_seconds(), 2)
        logger.error(f"Transform failed: {e}")
        log_to_db('transform', 'failed', error_message=str(e), duration_sec=duration)
        raise


if __name__ == "__main__":
    filename = sys.argv[1] if len(sys.argv) > 1 else 'crimes_initial.parquet'
    transform(filename)
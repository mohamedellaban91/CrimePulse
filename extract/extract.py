import os
import sys
import pandas as pd
from datetime import datetime, timedelta

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from logger import get_logger, log_to_db
from extract.api_client import fetch_data

logger = get_logger(__name__)

BATCH_SIZE  = 50000
BRONZE_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'bronze')
os.makedirs(BRONZE_PATH, exist_ok=True)


def initial_load() -> pd.DataFrame:
    start = datetime.now()
    try:
        logger.info("Starting INITIAL LOAD...")
        start_date = (datetime.now() - timedelta(days=150)).strftime('%Y-%m-%dT%H:%M:%S')

        params = {
            "$limit": BATCH_SIZE,
            "$where": f"date >= '{start_date}'",
            "$order": "date DESC"
        }

        df = fetch_data(params)

        output_path = os.path.join(BRONZE_PATH, 'crimes_initial.parquet')
        df.to_parquet(output_path, index=False)

        duration = round((datetime.now() - start).total_seconds(), 2)
        logger.info(f"Initial load completed: {len(df)} rows → {output_path}")
        log_to_db('extract_initial', 'success', rows_fetched=len(df), duration_sec=duration)
        return df

    except Exception as e:
        duration = round((datetime.now() - start).total_seconds(), 2)
        logger.error(f"Initial load failed: {e}")
        log_to_db('extract_initial', 'failed', error_message=str(e), duration_sec=duration)
        raise


def incremental_load() -> pd.DataFrame:
    start = datetime.now()
    try:
        logger.info("Starting INCREMENTAL LOAD...")
        yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%dT%H:%M:%S')
        today     = datetime.now().strftime('%Y-%m-%dT%H:%M:%S')

        params = {
            "$limit": 10000,
            "$where": f"date >= '{yesterday}' AND date < '{today}'",
            "$order": "date DESC"
        }

        df = fetch_data(params)

        date_str    = datetime.now().strftime('%Y%m%d')
        output_path = os.path.join(BRONZE_PATH, f'crimes_{date_str}.parquet')
        df.to_parquet(output_path, index=False)

        duration = round((datetime.now() - start).total_seconds(), 2)
        logger.info(f"Incremental load completed: {len(df)} rows → {output_path}")
        log_to_db('extract_incremental', 'success', rows_fetched=len(df), duration_sec=duration)
        return df

    except Exception as e:
        duration = round((datetime.now() - start).total_seconds(), 2)
        logger.error(f"Incremental load failed: {e}")
        log_to_db('extract_incremental', 'failed', error_message=str(e), duration_sec=duration)
        raise


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "initial"

    if mode == "initial":
        initial_load()
    elif mode == "incremental":
        incremental_load()
    else:
        logger.error(f"Unknown mode: {mode}")
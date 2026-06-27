import os
import sys
import pandas as pd
import psycopg2
from psycopg2.extras import execute_values
from datetime import datetime
from dotenv import load_dotenv

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from logger import get_logger, log_to_db

load_dotenv(os.path.join(os.path.dirname(__file__), '..', 'config', '.env'))

logger = get_logger(__name__)

SILVER_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'silver')

COLUMNS = [
    'id', 'case_number', 'date', 'iucr', 'primary_type',
    'description', 'fbi_code', 'block', 'location_description',
    'community_area', 'district', 'ward', 'beat',
    'x_coordinate', 'y_coordinate', 'latitude', 'longitude',
    'arrest', 'domestic', 'year', 'updated_on'
]


def get_conn():
    try:
        conn = psycopg2.connect(os.getenv('DB_URL'))
        logger.info("Database connected successfully")
        return conn
    except Exception as e:
        logger.error(f"Connection failed: {e}")
        raise


def load_raw_crimes(filename: str = 'crimes_initial.parquet') -> None:
    start = datetime.now()
    try:
        logger.info(f"Starting LOAD: {filename}")

        input_path = os.path.join(SILVER_PATH, filename)

        if not os.path.exists(input_path):
            logger.warning(f"File not found, skipping: {input_path}")
            log_to_db('load_raw_crimes', 'success', error_message='File not found, skipped')
            return

        df = pd.read_parquet(input_path)
        logger.info(f"Loaded {len(df)} rows from Silver")

        if len(df) == 0:
            logger.warning("No rows to load, skipping...")
            log_to_db('load_raw_crimes', 'success', error_message='Empty file, skipped')
            return

        df = df[[col for col in COLUMNS if col in df.columns]]
        df = df.astype(object).where(pd.notnull(df), None)

        conn = get_conn()
        cursor = conn.cursor()

        values = [tuple(row) for row in df.itertuples(index=False)]
        cols = ', '.join(df.columns)

        execute_values(
            cursor,
            f"INSERT INTO raw_crimes ({cols}) VALUES %s ON CONFLICT (id) DO NOTHING",
            values,
            page_size=1000
        )

        conn.commit()
        cursor.close()
        conn.close()

        duration = round((datetime.now() - start).total_seconds(), 2)
        logger.info(f"Load completed: {len(df)} rows in {duration}s")
        log_to_db('load_raw_crimes', 'success', rows_fetched=len(df), rows_loaded=len(df), duration_sec=duration)

    except Exception as e:
        duration = round((datetime.now() - start).total_seconds(), 2)
        logger.error(f"Load failed: {e}")
        log_to_db('load_raw_crimes', 'failed', error_message=str(e), duration_sec=duration)
        raise


def load_daily_crimes_by_area(filename: str = 'crimes_initial.parquet') -> None:
    start = datetime.now()
    try:
        logger.info("Starting LOAD: daily_crimes_by_area")

        input_path = os.path.join(SILVER_PATH, filename)

        if not os.path.exists(input_path):
            logger.warning(f"File not found, skipping: {input_path}")
            log_to_db('load_daily_crimes', 'success', error_message='File not found, skipped')
            return

        df = pd.read_parquet(input_path)

        if len(df) == 0:
            logger.warning("No rows to load, skipping...")
            log_to_db('load_daily_crimes', 'success', error_message='Empty file, skipped')
            return

        df['date'] = pd.to_datetime(df['date']).dt.date
        daily = df.groupby(['date', 'community_area']).size().reset_index(name='crime_count')
        daily.columns = ['date', 'community_area', 'crime_count']
        daily = daily.astype(object).where(pd.notnull(daily), None)

        conn = get_conn()
        cursor = conn.cursor()

        values = [tuple(row) for row in daily.itertuples(index=False)]

        execute_values(
            cursor,
            """
            INSERT INTO daily_crimes_by_area (date, community_area, crime_count)
            VALUES %s
            ON CONFLICT (date, community_area) DO NOTHING
            """,
            values,
            page_size=1000
        )

        conn.commit()
        cursor.close()
        conn.close()

        duration = round((datetime.now() - start).total_seconds(), 2)
        logger.info(f"daily_crimes_by_area loaded: {len(daily)} rows")
        log_to_db('load_daily_crimes', 'success', rows_fetched=len(df), rows_loaded=len(daily), duration_sec=duration)

    except Exception as e:
        duration = round((datetime.now() - start).total_seconds(), 2)
        logger.error(f"Load daily_crimes_by_area failed: {e}")
        log_to_db('load_daily_crimes', 'failed', error_message=str(e), duration_sec=duration)
        raise


if __name__ == "__main__":
    load_raw_crimes()
    load_daily_crimes_by_area()
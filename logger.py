import logging
import os
import psycopg2
from datetime import datetime
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), 'config', '.env'))


def get_logger(name: str) -> logging.Logger:
    log_dir = os.path.join(os.path.dirname(__file__), 'logs')
    os.makedirs(log_dir, exist_ok=True)

    logger = logging.getLogger(name)

    if not logger.handlers:
        logger.setLevel(logging.INFO)
        formatter = logging.Formatter('[%(asctime)s] %(levelname)s - %(message)s')

        file_handler = logging.FileHandler(
            os.path.join(log_dir, f'crimepulse_{datetime.now().strftime("%Y%m%d")}.log')
        )
        file_handler.setFormatter(formatter)

        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)

        logger.addHandler(file_handler)
        logger.addHandler(console_handler)

    return logger


def log_to_db(process: str, status: str, rows_fetched: int = 0,
              rows_loaded: int = 0, error_message: str = None,
              duration_sec: float = 0.0):
    try:
        conn = psycopg2.connect(os.getenv('DB_URL'))
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO etl_logs 
                (run_date, process, status, rows_fetched, rows_loaded, error_message, duration_sec)
            VALUES 
                (%s, %s, %s, %s, %s, %s, %s)
        """, (
            datetime.now(),
            process,
            status,
            rows_fetched,
            rows_loaded,
            error_message,
            duration_sec
        ))

        conn.commit()
        cursor.close()
        conn.close()

    except Exception as e:
        logging.getLogger(__name__).error(f"Failed to log to DB: {e}")
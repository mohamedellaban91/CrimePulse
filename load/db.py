import os
import sys
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from logger import get_logger
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '..', 'config', '.env'))

logger = get_logger(__name__)


def get_engine() -> Engine:
    try:
        db_url = os.getenv('DB_URL')
        if not db_url:
            raise ValueError("DB_URL not found in .env")

        engine = create_engine(db_url)
        logger.info("Database engine created successfully")
        return engine

    except Exception as e:
        logger.error(f"Failed to create engine: {e}")
        raise
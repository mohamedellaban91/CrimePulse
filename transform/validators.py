import pandas as pd
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from logger import get_logger

logger = get_logger(__name__)

REQUIRED_COLUMNS = [
    'id', 'case_number', 'date', 'primary_type',
    'community_area', 'district', 'beat',
    'latitude', 'longitude', 'arrest', 'domestic'
]


def validate_columns(df: pd.DataFrame) -> bool:
    try:
        missing = [col for col in REQUIRED_COLUMNS if col not in df.columns]
        if missing:
            logger.error(f"Missing columns: {missing}")
            return False
        logger.info("Column validation passed")
        return True
    except Exception as e:
        logger.error(f"Column validation error: {e}")
        raise


def validate_rows(df: pd.DataFrame) -> bool:
    try:
        if df.empty:
            logger.error("DataFrame is empty")
            return False
        logger.info(f"Row validation passed: {len(df)} rows")
        return True
    except Exception as e:
        logger.error(f"Row validation error: {e}")
        raise
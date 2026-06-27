import pandas as pd
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from logger import get_logger

logger = get_logger(__name__)


def fix_dtypes(df: pd.DataFrame) -> pd.DataFrame:
    try:
        df['date']       = pd.to_datetime(df['date'],       errors='coerce')
        df['updated_on'] = pd.to_datetime(df['updated_on'], errors='coerce')

        for col in ['latitude', 'longitude', 'x_coordinate', 'y_coordinate']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')

        for col in ['community_area', 'ward', 'year', 'beat', 'district']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').astype('Int64')

        logger.info("Data types fixed")
        return df
    except Exception as e:
        logger.error(f"fix_dtypes failed: {e}")
        raise


def drop_duplicates(df: pd.DataFrame) -> pd.DataFrame:
    try:
        before = len(df)
        df = df.drop_duplicates(subset=['id'])
        logger.info(f"Duplicates removed: {before - len(df)} rows dropped")
        return df
    except Exception as e:
        logger.error(f"drop_duplicates failed: {e}")
        raise


def drop_unnecessary_columns(df: pd.DataFrame) -> pd.DataFrame:
    try:
        cols_to_drop = ['location']
        existing = [col for col in cols_to_drop if col in df.columns]
        df = df.drop(columns=existing)
        logger.info(f"Dropped columns: {existing}")
        return df
    except Exception as e:
        logger.error(f"drop_unnecessary_columns failed: {e}")
        raise


def handle_missing(df: pd.DataFrame) -> pd.DataFrame:
    try:
        before = len(df)
        df = df.dropna(subset=['date', 'primary_type', 'community_area'])
        logger.info(f"Missing values handled: {before - len(df)} rows dropped")
        return df
    except Exception as e:
        logger.error(f"handle_missing failed: {e}")
        raise
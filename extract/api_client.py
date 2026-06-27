import requests
import pandas as pd
import time
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from logger import get_logger

logger = get_logger(__name__)

API_URL = "https://data.cityofchicago.org/resource/ijzp-q8t2.json"


def fetch_data(params: dict) -> pd.DataFrame:
    try:
        logger.info(f"Fetching data with params: {params}")
        start = time.time()

        response = requests.get(API_URL, params=params, timeout=60)
        response.raise_for_status()

        df = pd.DataFrame(response.json())

        logger.info(f"Fetched {len(df)} rows in {round(time.time() - start, 2)}s")
        return df

    except requests.exceptions.Timeout:
        logger.error("Request timed out")
        raise
    except requests.exceptions.RequestException as e:
        logger.error(f"Request failed: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise
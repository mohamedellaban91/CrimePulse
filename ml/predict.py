import os
import sys
import pandas as pd
import numpy as np
import psycopg2
import joblib
from datetime import datetime, timedelta
from dotenv import load_dotenv

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from logger import get_logger

load_dotenv(os.path.join(os.path.dirname(__file__), '..', 'config', '.env'))
logger = get_logger(__name__)

MODEL_PATH = os.path.join(os.path.dirname(__file__), 'model', 'crime_model.pkl')


# ========================
# Load Model
# ========================
def load_model():
    try:
        model = joblib.load(MODEL_PATH)
        logger.info("Model loaded successfully")
        return model
    except Exception as e:
        logger.error(f"Failed to load model: {e}")
        raise


# ========================
# Get Historical Data
# ========================
def get_historical_data(community_area: int) -> pd.DataFrame:
    try:
        conn = psycopg2.connect(os.getenv('DB_URL'))

        query = """
            SELECT 
                d.date,
                d.community_area,
                d.crime_count,
                COALESCE(r.arrest_rate, 0)   AS arrest_rate,
                COALESCE(r.domestic_rate, 0) AS domestic_rate
            FROM daily_crimes_by_area d
            LEFT JOIN (
                SELECT 
                    DATE(date)     AS date,
                    community_area,
                    ROUND(AVG(CASE WHEN arrest   THEN 1.0 ELSE 0.0 END)::numeric, 4) AS arrest_rate,
                    ROUND(AVG(CASE WHEN domestic THEN 1.0 ELSE 0.0 END)::numeric, 4) AS domestic_rate
                FROM raw_crimes
                GROUP BY DATE(date), community_area
            ) r ON d.date = r.date AND d.community_area = r.community_area
            WHERE d.community_area = %s
            ORDER BY d.date DESC
            LIMIT 60
        """

        df = pd.read_sql(query, conn, params=(community_area,))
        conn.close()
        return df.sort_values('date')

    except Exception as e:
        logger.error(f"Failed to get historical data: {e}")
        raise


# ========================
# Build Predict Features
# ========================
def build_predict_features(df: pd.DataFrame, target_date: datetime, community_area: int) -> pd.DataFrame:
    try:
        df['date'] = pd.to_datetime(df['date'])

        # Lag values from historical data
        lag_1  = df['crime_count'].iloc[-1]
        lag_7  = df['crime_count'].iloc[-7]  if len(df) >= 7  else df['crime_count'].mean()
        lag_30 = df['crime_count'].iloc[-30] if len(df) >= 30 else df['crime_count'].mean()

        rolling_avg_7  = df['crime_count'].iloc[-7:].mean()  if len(df) >= 7  else df['crime_count'].mean()
        rolling_avg_30 = df['crime_count'].iloc[-30:].mean() if len(df) >= 30 else df['crime_count'].mean()

        arrest_rate   = df['arrest_rate'].iloc[-1]
        domestic_rate = df['domestic_rate'].iloc[-1]

        month = target_date.month
        season_map = {
            12: 1, 1: 1, 2: 1,
            3: 2,  4: 2, 5: 2,
            6: 3,  7: 3, 8: 3,
            9: 4, 10: 4, 11: 4
        }

        features = {
            'community_area' : community_area,
            'day_of_week'    : target_date.weekday(),
            'month'          : month,
            'day'            : target_date.day,
            'quarter'        : (month - 1) // 3 + 1,
            'week_of_year'   : target_date.isocalendar()[1],
            'is_weekend'     : int(target_date.weekday() in [5, 6]),
            'season'         : season_map[month],
            'lag_1'          : lag_1,
            'lag_7'          : lag_7,
            'lag_30'         : lag_30,
            'rolling_avg_7'  : rolling_avg_7,
            'rolling_avg_30' : rolling_avg_30,
            'arrest_rate'    : arrest_rate,
            'domestic_rate'  : domestic_rate
        }

        return pd.DataFrame([features])

    except Exception as e:
        logger.error(f"Failed to build predict features: {e}")
        raise


# ========================
# Predict
# ========================
def predict(community_area: int, days_ahead: int = 7):
    try:
        logger.info(f"Starting PREDICTION for community_area={community_area}, days_ahead={days_ahead}")

        model = load_model()
        df    = get_historical_data(community_area)

        if df.empty:
            logger.error(f"No historical data for community_area={community_area}")
            return

        # Get last date in data
        last_date = pd.to_datetime(df['date'].max())

        results = []
        for i in range(1, days_ahead + 1):
            target_date = last_date + timedelta(days=i)
            X = build_predict_features(df, target_date, community_area)
            pred = round(float(model.predict(X)[0]), 2)
            pred = max(0, pred)  # مش ممكن يكون سالب

            results.append({
                'date'          : target_date.strftime('%Y-%m-%d'),
                'community_area': community_area,
                'predicted_crimes': pred
            })

            logger.info(f"  {target_date.strftime('%Y-%m-%d')} → {pred} crimes")

        results_df = pd.DataFrame(results)
        logger.info(f"Prediction completed for {days_ahead} days")
        return results_df

    except Exception as e:
        logger.error(f"Prediction failed: {e}")
        raise


# ========================
# Main
# ========================
if __name__ == "__main__":
    import sys

    community_area = int(sys.argv[1]) if len(sys.argv) > 1 else 43
    days_ahead     = int(sys.argv[2]) if len(sys.argv) > 2 else 7

    results = predict(community_area, days_ahead)

    print("\n=== Prediction Results ===")
    print(results.to_string(index=False))
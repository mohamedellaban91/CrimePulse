import os
import sys
import pandas as pd
import numpy as np
import psycopg2
import joblib
from datetime import datetime
from dotenv import load_dotenv
from xgboost import XGBRegressor
from sklearn.model_selection import train_test_split, RandomizedSearchCV
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from logger import get_logger

load_dotenv(os.path.join(os.path.dirname(__file__), '..', 'config', '.env'))
logger = get_logger(__name__)

MODEL_PATH = os.path.join(os.path.dirname(__file__), 'model', 'crime_model.pkl')


# ========================
# Load Data
# ========================
def load_data() -> pd.DataFrame:
    try:
        logger.info("Loading data from Supabase...")
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
                    DATE(date)       AS date,
                    community_area,
                    ROUND(AVG(CASE WHEN arrest  THEN 1.0 ELSE 0.0 END)::numeric, 4) AS arrest_rate,
                    ROUND(AVG(CASE WHEN domestic THEN 1.0 ELSE 0.0 END)::numeric, 4) AS domestic_rate
                FROM raw_crimes
                GROUP BY DATE(date), community_area
            ) r ON d.date = r.date AND d.community_area = r.community_area
            ORDER BY d.community_area, d.date
        """

        df = pd.read_sql(query, conn)
        conn.close()
        logger.info(f"Loaded {len(df)} rows")
        return df

    except Exception as e:
        logger.error(f"Load data failed: {e}")
        raise


# ========================
# Feature Engineering
# ========================
def build_features(df: pd.DataFrame) -> pd.DataFrame:
    try:
        logger.info("Building features...")
        df['date'] = pd.to_datetime(df['date'])

        # Time features
        df['day_of_week']  = df['date'].dt.dayofweek
        df['month']        = df['date'].dt.month
        df['day']          = df['date'].dt.day
        df['quarter']      = df['date'].dt.quarter
        df['week_of_year'] = df['date'].dt.isocalendar().week.astype(int)
        df['is_weekend']   = df['day_of_week'].isin([5, 6]).astype(int)
        df['season']       = df['month'].map({
            12: 1, 1: 1, 2: 1,
            3: 2,  4: 2, 5: 2,
            6: 3,  7: 3, 8: 3,
            9: 4, 10: 4, 11: 4
        })

        # Lag features per community_area
        df = df.sort_values(['community_area', 'date'])
        grp = df.groupby('community_area')['crime_count']

        df['lag_1']          = grp.shift(1)
        df['lag_7']          = grp.shift(7)
        df['lag_30']         = grp.shift(30)
        df['rolling_avg_7']  = grp.shift(1).rolling(7).mean().reset_index(level=0, drop=True)
        df['rolling_avg_30'] = grp.shift(1).rolling(30).mean().reset_index(level=0, drop=True)

        # Drop rows with NaN from lag
        df = df.dropna()
        logger.info(f"Features built: {len(df)} rows")
        return df

    except Exception as e:
        logger.error(f"Feature engineering failed: {e}")
        raise


# ========================
# Hyperparameter Tuning
# ========================
def tune_model(X_train, y_train) -> XGBRegressor:
    try:
        logger.info("Starting Hyperparameter Tuning...")

        param_grid = {
            'n_estimators'  : [100, 200, 300, 500],
            'learning_rate' : [0.01, 0.05, 0.1, 0.2],
            'max_depth'     : [3, 4, 5, 6, 8],
            'subsample'     : [0.6, 0.7, 0.8, 1.0],
            'colsample_bytree': [0.6, 0.7, 0.8, 1.0],
            'min_child_weight': [1, 3, 5]
        }

        model = XGBRegressor(random_state=42, n_jobs=-1)

        search = RandomizedSearchCV(
            estimator  = model,
            param_distributions = param_grid,
            n_iter     = 30,        # بيجرب 30 combination
            cv         = 3,         # 3-fold cross validation
            scoring    = 'neg_mean_absolute_error',
            random_state = 42,
            n_jobs     = -1,
            verbose    = 1
        )

        search.fit(X_train, y_train)

        logger.info(f"Best params: {search.best_params_}")
        logger.info(f"Best MAE: {round(-search.best_score_, 4)}")
        return search.best_estimator_

    except Exception as e:
        logger.error(f"Tuning failed: {e}")
        raise


# ========================
# Train Model
# ========================
def train():
    try:
        logger.info("Starting TRAINING...")
        start = datetime.now()

        # Load & build features
        df = load_data()
        df = build_features(df)

        # Define features & target
        FEATURES = [
            'community_area',
            'day_of_week', 'month', 'day', 'quarter',
            'week_of_year', 'is_weekend', 'season',
            'lag_1', 'lag_7', 'lag_30',
            'rolling_avg_7', 'rolling_avg_30',
            'arrest_rate', 'domestic_rate'
        ]
        TARGET = 'crime_count'

        X = df[FEATURES]
        y = df[TARGET]

        # Split
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, shuffle=False
        )
        logger.info(f"Train: {len(X_train)} rows | Test: {len(X_test)} rows")

        # Tune & Train
        model = tune_model(X_train, y_train)

        # Evaluate
        y_pred = model.predict(X_test)
        mae    = round(mean_absolute_error(y_test, y_pred), 4)
        rmse   = round(np.sqrt(mean_squared_error(y_test, y_pred)), 4)
        r2     = round(r2_score(y_test, y_pred), 4)

        logger.info("=== Model Evaluation ===")
        logger.info(f"MAE:  {mae}")
        logger.info(f"RMSE: {rmse}")
        logger.info(f"R2:   {r2}")

        # Feature Importance
        importance = pd.Series(model.feature_importances_, index=FEATURES)
        importance = importance.sort_values(ascending=False)
        logger.info("=== Feature Importance ===")
        for feat, score in importance.items():
            logger.info(f"  {feat}: {round(score, 4)}")

        # Save model
        joblib.dump(model, MODEL_PATH)
        logger.info(f"Model saved → {MODEL_PATH}")

        duration = round((datetime.now() - start).total_seconds(), 2)
        logger.info(f"Training completed in {duration}s")

    except Exception as e:
        logger.error(f"Training failed: {e}")
        raise


if __name__ == "__main__":
    train()
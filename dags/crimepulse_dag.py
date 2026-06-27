import sys
import os
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator

sys.path.append('/home/mohamed/CrimePulse')

from extract.extract import initial_load, incremental_load
from transform.transform import transform
from load.load import load_raw_crimes, load_daily_crimes_by_area

# ========================
# Default Args
# ========================
default_args = {
    'owner'           : 'mohamed',
    'retries'         : 3,
    'retry_delay'     : timedelta(minutes=5),
    'email_on_failure': False,
}

# ========================
# Initial Load DAG
# ========================
with DAG(
    dag_id            = 'crimepulse_initial_load',
    default_args      = default_args,
    description       = 'Initial load of Chicago Crime data',
    schedule_interval = None,
    start_date        = datetime(2026, 1, 1),
    catchup           = False,
    tags              = ['crimepulse', 'initial']
) as initial_dag:

    extract_initial = PythonOperator(
        task_id         = 'extract_initial',
        python_callable = initial_load
    )

    transform_initial = PythonOperator(
        task_id         = 'transform_initial',
        python_callable = lambda: transform('crimes_initial.parquet')
    )

    load_crimes_initial = PythonOperator(
        task_id         = 'load_crimes_initial',
        python_callable = lambda: load_raw_crimes('crimes_initial.parquet')
    )

    load_daily_initial = PythonOperator(
        task_id         = 'load_daily_initial',
        python_callable = lambda: load_daily_crimes_by_area('crimes_initial.parquet')
    )

    extract_initial >> transform_initial >> load_crimes_initial >> load_daily_initial


# ========================
# Incremental Load DAG
# ========================
with DAG(
    dag_id            = 'crimepulse_incremental_load',
    default_args      = default_args,
    description       = 'Daily incremental load of Chicago Crime data',
    schedule_interval = '0 6 * * *',
    start_date        = datetime(2026, 1, 1),
    catchup           = False,
    tags              = ['crimepulse', 'incremental']
) as incremental_dag:

    extract_incr = PythonOperator(
        task_id         = 'extract_incremental',
        python_callable = incremental_load
    )

    transform_incr = PythonOperator(
        task_id         = 'transform_incremental',
        python_callable = lambda: transform(
            f"crimes_{datetime.now().strftime('%Y%m%d')}.parquet"
        )
    )

    load_crimes_incr = PythonOperator(
        task_id         = 'load_crimes_incremental',
        python_callable = lambda: load_raw_crimes(
            f"crimes_{datetime.now().strftime('%Y%m%d')}.parquet"
        )
    )

    load_daily_incr = PythonOperator(
        task_id         = 'load_daily_incremental',
        python_callable = lambda: load_daily_crimes_by_area(
            f"crimes_{datetime.now().strftime('%Y%m%d')}.parquet"
        )
    )

    extract_incr >> transform_incr >> load_crimes_incr >> load_daily_incr
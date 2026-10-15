
import streamlit as st
from google.cloud import bigquery

PROJECT_ID = "careflow-analytics-98234"
TABLE_ID = "careflow-analytics-98234.careflow_analytics.event_logs"


@st.cache_data(ttl=300)
def load_bigquery_events(limit=1000):
    client = bigquery.Client(project=PROJECT_ID)

    query = f"""
        SELECT case_id, activity, timestamp
        FROM `{TABLE_ID}`
        WHERE case_id IS NOT NULL
          AND activity IS NOT NULL
          AND timestamp IS NOT NULL
        LIMIT {int(limit)}
    """

    job_config = bigquery.QueryJobConfig(
        maximum_bytes_billed=20_000_000
    )

    return client.query(
        query,
        job_config=job_config
    ).to_dataframe()

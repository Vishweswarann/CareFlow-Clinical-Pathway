
from google.cloud import bigquery
import streamlit as st

PROJECT_ID = "careflow-analytics-98234"

TABLE_ID = (
    "careflow-analytics-98234."
    "careflow_analytics.event_logs"
)


@st.cache_data(ttl=300)
def load_bigquery_events(limit=1000):
    client = bigquery.Client(project=PROJECT_ID)

    query = f"""
    WITH numbered_events AS (
        SELECT
            case_id,
            activity,
            timestamp,
            ROW_NUMBER() OVER (
                PARTITION BY case_id
                ORDER BY timestamp
            ) AS event_number
        FROM `{TABLE_ID}`
        WHERE case_id IS NOT NULL
          AND activity IS NOT NULL
          AND timestamp IS NOT NULL
    )
    SELECT
        case_id,
        activity,
        timestamp
    FROM numbered_events
    WHERE event_number <= 20
    ORDER BY case_id, timestamp
    LIMIT {int(limit)}
    """

    job_config = bigquery.QueryJobConfig(
        maximum_bytes_billed=20_000_000
    )

    df = client.query(
        query,
        job_config=job_config
    ).to_dataframe()

    return df


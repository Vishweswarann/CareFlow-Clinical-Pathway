
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
    SELECT
        case_id,
        activity,
        timestamp,
        department
    FROM `{TABLE_ID}`
    WHERE case_id IS NOT NULL
      AND activity IS NOT NULL
      AND timestamp IS NOT NULL
    ORDER BY FARM_FINGERPRINT(
        CONCAT(
            CAST(case_id AS STRING),
            CAST(timestamp AS STRING)
        )
    )
    LIMIT @row_limit
    """

    job_config = bigquery.QueryJobConfig(
        maximum_bytes_billed=20_000_000,
        query_parameters=[
            bigquery.ScalarQueryParameter(
                "row_limit", "INT64", int(limit)
            )
        ],
    )

    df = client.query(
        query,
        job_config=job_config,
    ).to_dataframe()

    return df

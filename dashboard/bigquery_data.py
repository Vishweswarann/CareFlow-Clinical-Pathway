
from google.cloud import bigquery
import streamlit as st

PROJECT_ID = "careflow-analytics-98234"
TABLE_ID = "careflow-analytics-98234.careflow_analytics.event_logs"


@st.cache_data(ttl=1800)
def load_bigquery_events(limit=200):
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

    job = client.query(query, job_config=job_config)
    result = job.result(timeout=60)

    return result.to_dataframe(create_bqstorage_client=False)


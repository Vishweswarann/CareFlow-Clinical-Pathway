
from google.cloud import bigquery
from google.oauth2 import service_account
import streamlit as st
import time
import logging

PROJECT_ID = "careflow-analytics-98234"
TABLE_ID = "careflow-analytics-98234.careflow_analytics.event_logs"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@st.cache_resource
def get_bigquery_client():
    # Use the service account credentials configured in Streamlit Cloud.
    if "gcp_service_account" in st.secrets:
        credentials_info = dict(st.secrets["gcp_service_account"])

        credentials = (
            service_account.Credentials.from_service_account_info(
                credentials_info
            )
        )

        return bigquery.Client(
            project=PROJECT_ID,
            credentials=credentials,
        )

    # Local fallback: use Google Application Default Credentials.
    return bigquery.Client(project=PROJECT_ID)


@st.cache_data(ttl=1800)
def load_bigquery_events(limit=200):
    client = get_bigquery_client()

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
                "row_limit",
                "INT64",
                int(limit),
            )
        ],
    )

    start = time.perf_counter()

    job = client.query(query, job_config=job_config)
    submitted = time.perf_counter()

    result = job.result(timeout=60)
    query_finished = time.perf_counter()

    df = result.to_dataframe(create_bqstorage_client=False)
    finished = time.perf_counter()

    logger.info(
        "BigQuery timings | Submit: %.2fs | Wait: %.2fs | "
        "DataFrame: %.2fs | Total: %.2fs | Rows: %d",
        submitted - start,
        query_finished - submitted,
        finished - query_finished,
        finished - start,
        len(df),
    )

    return df

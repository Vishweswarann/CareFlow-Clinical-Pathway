
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
    """
    Use Streamlit service-account secrets when available.
    If secrets are absent locally, fall back to Google ADC.
    """
    credentials_info = None

    try:
        credentials_info = st.secrets.get("gcp_service_account")
    except Exception as exc:
        logger.info(
            "Streamlit secrets unavailable; trying local ADC (%s).",
            type(exc).__name__,
        )

    if credentials_info:
        credentials = (
            service_account.Credentials.from_service_account_info(
                dict(credentials_info)
            )
        )

        return bigquery.Client(
            project=PROJECT_ID,
            credentials=credentials,
        )

    return bigquery.Client(project=PROJECT_ID)


@st.cache_data(ttl=1800, show_spinner=False)
def load_bigquery_events(limit=200):
    """Load event records from BigQuery with a billing limit."""
    client = get_bigquery_client()

    limit = int(limit)
    if limit < 1 or limit > 1000:
        raise ValueError("Limit must be between 1 and 1000.")

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
        ORDER BY case_id, timestamp
        LIMIT @row_limit
    """

    job_config = bigquery.QueryJobConfig(
        maximum_bytes_billed=20_000_000,
        query_parameters=[
            bigquery.ScalarQueryParameter(
                "row_limit",
                "INT64",
                limit,
            )
        ],
    )

    start = time.perf_counter()

    try:
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

    except Exception:
        logger.exception("Failed to load events from BigQuery.")
        raise

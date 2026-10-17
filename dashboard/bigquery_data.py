
from google.cloud import bigquery
import streamlit as st

PROJECT_ID = "careflow-analytics-98234"

TABLE_ID = (
    "careflow-analytics-98234."
    "careflow_analytics.event_logs"
)


@st.cache_data(ttl=300)
def load_bigquery_events(limit=5000):
    client = bigquery.Client(project=PROJECT_ID)

    query = f"""
    WITH sampled_events AS (
        SELECT
            case_id,
            activity,
            timestamp,
            event_sequence
        FROM `{TABLE_ID}`
        WHERE case_id IS NOT NULL
          AND activity IS NOT NULL
          AND timestamp IS NOT NULL
        QUALIFY ROW_NUMBER() OVER (
            PARTITION BY activity
            ORDER BY FARM_FINGERPRINT(
                CONCAT(
                    CAST(case_id AS STRING),
                    CAST(event_sequence AS STRING)
                )
            )
        ) <= 1000
    )
    SELECT
        case_id,
        activity,
        timestamp
    FROM sampled_events
    ORDER BY FARM_FINGERPRINT(
        CONCAT(
            CAST(case_id AS STRING),
            CAST(timestamp AS STRING)
        )
    )
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

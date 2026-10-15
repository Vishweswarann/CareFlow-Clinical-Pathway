
from pathlib import Path

import pandas as pd
from google.cloud import bigquery

PROJECT_ID = "careflow-analytics-98234"
DATASET_ID = "careflow_analytics"
TABLE_ID = "event_logs_test"

ROOT = Path(__file__).resolve().parent.parent
CSV_PATH = ROOT / "data" / "ehr_events_full.csv"


def main():
    if not CSV_PATH.exists():
        raise FileNotFoundError(f"Dataset not found: {CSV_PATH}")

    df = pd.read_csv(CSV_PATH)
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="raise")

    required_columns = [
        "event_id", "case_id", "activity", "timestamp", "department",
        "event_sequence", "resource_role", "resource_id", "event_detail",
        "arrival_mode", "age_group", "gender", "chief_complaint",
        "triage_level", "disposition",
    ]

    missing = set(required_columns) - set(df.columns)
    if missing:
        raise ValueError(f"Missing columns: {sorted(missing)}")

    if df["event_id"].duplicated().any():
        raise ValueError("Duplicate event IDs found; upload cancelled.")

    df = df[required_columns]

    client = bigquery.Client(project=PROJECT_ID)
    table_ref = f"{PROJECT_ID}.{DATASET_ID}.{TABLE_ID}"

    job_config = bigquery.LoadJobConfig(
        write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
        autodetect=False,
        schema=[
            bigquery.SchemaField("event_id", "STRING"),
            bigquery.SchemaField("case_id", "STRING"),
            bigquery.SchemaField("activity", "STRING"),
            bigquery.SchemaField("timestamp", "TIMESTAMP"),
            bigquery.SchemaField("department", "STRING"),
            bigquery.SchemaField("event_sequence", "INT64"),
            bigquery.SchemaField("resource_role", "STRING"),
            bigquery.SchemaField("resource_id", "STRING"),
            bigquery.SchemaField("event_detail", "STRING"),
            bigquery.SchemaField("arrival_mode", "STRING"),
            bigquery.SchemaField("age_group", "STRING"),
            bigquery.SchemaField("gender", "STRING"),
            bigquery.SchemaField("chief_complaint", "STRING"),
            bigquery.SchemaField("triage_level", "INT64"),
            bigquery.SchemaField("disposition", "STRING"),
        ],
    )

    job = client.load_table_from_dataframe(
        df, table_ref, job_config=job_config
    )
    job.result()

    table = client.get_table(table_ref)
    print(f"Upload successful: {table.full_table_id}")
    print(f"Rows uploaded: {table.num_rows}")


if __name__ == "__main__":
    main()

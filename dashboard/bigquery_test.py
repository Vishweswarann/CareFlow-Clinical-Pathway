
from google.cloud import bigquery

PROJECT_ID = "careflow-analytics-98234"
TABLE_ID = (
    "careflow-analytics-98234."
    "careflow_analytics.event_logs"
)

client = bigquery.Client(project=PROJECT_ID)

query = f"""
SELECT case_id, activity, timestamp
FROM `{TABLE_ID}`
LIMIT 1000
"""

job_config = bigquery.QueryJobConfig(
    maximum_bytes_billed=20_000_000
)


df = client.query(
    query,
    job_config=job_config
).to_dataframe()

print("BigQuery query successful!")
print("Rows retrieved:", len(df))
print("Columns:", list(df.columns))
print(df.head())

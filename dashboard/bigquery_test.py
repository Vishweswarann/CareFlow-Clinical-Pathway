
from google.cloud import bigquery

PROJECT_ID = "careflow-analytics-98234"
TABLE_ID = "careflow-analytics-98234.careflow_analytics.event_logs"

client = bigquery.Client(project=PROJECT_ID)

query = f"""
SELECT
    activity,
    COUNT(*) AS event_count
FROM `{TABLE_ID}`
GROUP BY activity
ORDER BY event_count DESC
"""

job_config = bigquery.QueryJobConfig(
    maximum_bytes_billed=20_000_000
)

df = client.query(
    query,
    job_config=job_config
).to_dataframe()

print("Number of activities:", len(df))
print(df.to_string(index=False))


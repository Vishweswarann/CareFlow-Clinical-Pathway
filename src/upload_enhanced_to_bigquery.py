

from pathlib import Path
from google.cloud import bigquery

# Locate the enhanced CSV in the Careflow project root
project_root = Path(__file__).resolve().parent.parent
csv_file = project_root / "ehr_events_enhanced.csv"

# Existing Google Cloud project
project_id = "careflow-analytics-98234"
dataset_id = "careflow_analytics"
table_id = "event_logs_enhanced"

if not csv_file.exists():
    raise FileNotFoundError(f"CSV not found: {csv_file}")

client = bigquery.Client(project=project_id)

table_ref = f"{project_id}.{dataset_id}.{table_id}"

job_config = bigquery.LoadJobConfig(
    source_format=bigquery.SourceFormat.CSV,
    skip_leading_rows=1,
    autodetect=True,
    write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE
)

print(f"Uploading: {csv_file}")
print(f"Destination: {table_ref}")

with open(csv_file, "rb") as file:
    job = client.load_table_from_file(
        file,
        table_ref,
        job_config=job_config
    )

job.result()

table = client.get_table(table_ref)

print("\nUpload successful!")
print("Table:", table.full_table_id)
print("Rows:", table.num_rows)
print("Columns:", len(table.schema))
print("Column names:")
for column in table.schema:
    print(f" - {column.name}: {column.field_type}")

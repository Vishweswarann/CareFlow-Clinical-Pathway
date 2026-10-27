# CareFlow-Clinical-Pathway

## BigQuery Data Upload

CareFlow supports uploading the synthetic hospital event dataset to Google BigQuery using a Python uploader.

### Dataset
- Input file: `data/ehr_events_full.csv`
- BigQuery project: `careflow-analytics-98234`
- Dataset: `careflow_analytics`
- Test table: `event_logs_test`

### Prerequisites
- Python environment with project dependencies installed
- Google Cloud CLI configured and authenticated
- Permission to create and load BigQuery tables

### Run the uploader

From the project root, execute:

```bash
python src/upload_to_bigquery.py
```

The uploader validates the required columns and duplicate event IDs before loading the dataset into the test table. It then reports the uploaded row count.

### Verification

Verify the upload in BigQuery:

```sql
SELECT
  COUNT(*) AS total_rows,
  COUNT(DISTINCT event_id) AS unique_events,
  COUNT(DISTINCT case_id) AS unique_cases,
  MIN(timestamp) AS first_event,
  MAX(timestamp) AS last_event
FROM `careflow-analytics-98234.careflow_analytics.event_logs_test`;
```

**Note:** The uploader currently targets a test table. Nightly automated ingestion is not yet configured.

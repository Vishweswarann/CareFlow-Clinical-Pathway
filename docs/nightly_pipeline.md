# CareFlow Nightly Pipeline

## Overview

The CareFlow nightly pipeline currently provides local CSV validation, event ID deduplication simulation, logging, and dry-run reporting.

## Current Features

- Validates the required 15 event-log columns.
- Checks for missing or duplicate event IDs.
- Validates timestamp formats.
- Simulates incremental ingestion by identifying unseen event IDs.
- Generates a dry-run report.
- Logs pipeline execution and errors.

## Run Locally

Activate the project's virtual environment and run:

```powershell
python src/nightly_bigquery_pipeline.py
```

Run the local deduplication test:

```powershell
python src/test_incremental_merge.py
```

## Output Files

- `data/pipeline_reports/dry_run_report.txt`
- `logs/nightly_pipeline.log`
- `data/pipeline_test/`

These are generated locally and should not be committed as datasets or runtime outputs.

## Current Limitations

- The current nightly script compares against a small local synthetic baseline, not a live BigQuery table.
- No BigQuery writes or actual nightly cloud ingestion are implemented.
- BigQuery write testing is pending because billing is not enabled for the project.
- The local deduplication test verifies basic idempotency logic but does not prove that a BigQuery `MERGE` works.

## Next Steps

1. Implement and test a BigQuery staging and incremental `MERGE` workflow when project access permits.
2. Integrate with the team's agreed event-log target.
3. Add shared scheduling after validation.
4. Coordinate with the Streamlit team on the expected data source and schema.
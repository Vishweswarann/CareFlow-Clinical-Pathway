# CareFlow End-to-End Pipeline Audit – Day 2

## Work completed
- Inspected the dbt project configuration.
- Reviewed the stg_event_logs staging model.
- Confirmed that dbt recognises one staging model and six staging tests.
- Reviewed the staging schema and existing data quality tests.
- Attempted to execute the six staging tests.
- Inspected the dashboard BigQuery data loader and data validation.
- Reviewed the dbt OAuth profile without changing authentication.

## Findings
- The staging model includes event_sequence, resource_role, arrival_mode and disposition.
- All six staging tests returned errors because of a BigQuery permission issue. Their data quality results remain unverified.
- The dashboard currently reads directly from the original BigQuery table rather than the dbt staging view.
- The dashboard supports both timestamp and event_timestamp column names.
- No authentication settings or application code were changed during this audit.

## Next step
Investigate a safe way to connect the dbt staging model with the dashboard without disrupting the existing working data loader.

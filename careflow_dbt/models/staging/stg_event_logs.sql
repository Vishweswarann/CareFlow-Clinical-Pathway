
{{ config(materialized='view') }}

SELECT
    CAST(event_id AS STRING) AS event_id,
    CAST(case_id AS STRING) AS case_id,
    TRIM(activity) AS activity,
    SAFE_CAST(timestamp AS TIMESTAMP) AS event_timestamp,
    COALESCE(NULLIF(TRIM(department), ''), 'Unknown') AS department
FROM `careflow-analytics-98234.careflow_analytics.event_logs`

{{ config(materialized='view') }}

SELECT
    TRIM(CAST(case_id AS STRING)) AS case_id,
    TRIM(CAST(event_id AS STRING)) AS event_id,
    TRIM(activity) AS activity,
    SAFE_CAST(timestamp AS TIMESTAMP) AS event_timestamp,
    TRIM(department) AS department
FROM `careflow-analytics-98234.careflow_analytics.event_logs`

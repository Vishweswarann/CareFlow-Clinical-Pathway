{{ config(materialized='view') }}

SELECT *
FROM `careflow-analytics-98234.careflow_analytics.event_logs_analysis`
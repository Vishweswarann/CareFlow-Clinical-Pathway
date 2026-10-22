
-- CareFlow: Clinical Event Data Quality Checks
-- Read-only validation; does not modify production data.

SELECT
    COUNT(*) AS total_events,
    COUNTIF(event_id IS NULL OR TRIM(event_id) = '') AS missing_event_ids,
    COUNTIF(case_id IS NULL OR TRIM(case_id) = '') AS missing_case_ids,
    COUNTIF(activity IS NULL OR TRIM(activity) = '') AS missing_activities,
    COUNTIF(timestamp IS NULL) AS missing_timestamps,
    COUNT(DISTINCT event_id) AS unique_event_ids
FROM `careflow-analytics-98234.careflow_analytics.event_logs`;

-- Identify duplicate event IDs.
SELECT
    event_id,
    COUNT(*) AS occurrences
FROM `careflow-analytics-98234.careflow_analytics.event_logs`
WHERE event_id IS NOT NULL
GROUP BY event_id
HAVING COUNT(*) > 1
ORDER BY occurrences DESC;

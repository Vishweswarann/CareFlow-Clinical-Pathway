
-- CareFlow: Patient Case Duration Analysis
-- Read-only analysis of completed event sequences.

WITH case_durations AS (
    SELECT
        case_id,
        COUNT(*) AS event_count,
        MIN(timestamp) AS start_time,
        MAX(timestamp) AS end_time,
        TIMESTAMP_DIFF(
            MAX(timestamp),
            MIN(timestamp),
            MINUTE
        ) AS duration_minutes
    FROM `careflow-analytics-98234.careflow_analytics.event_logs_test`
    WHERE case_id IS NOT NULL
      AND timestamp IS NOT NULL
    GROUP BY case_id
)
SELECT
    COUNT(*) AS total_cases,
    ROUND(AVG(duration_minutes), 2) AS avg_duration_minutes,
    APPROX_QUANTILES(duration_minutes, 100)[OFFSET(50)]
        AS median_duration_minutes,
    MAX(duration_minutes) AS max_duration_minutes,
    COUNTIF(event_count = 1) AS single_event_cases
FROM case_durations;

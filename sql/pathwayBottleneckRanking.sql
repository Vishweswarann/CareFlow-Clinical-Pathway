
-- CareFlow: Clinical Pathway Bottleneck Ranking
-- Read-only analysis; one row per observed event transition.

WITH ordered_events AS (
    SELECT
        case_id,
        activity,
        timestamp,
        event_sequence,
        event_id,
        LAG(activity) OVER (
            PARTITION BY case_id
            ORDER BY timestamp, event_sequence, event_id
        ) AS previous_activity,
        LAG(timestamp) OVER (
            PARTITION BY case_id
            ORDER BY timestamp, event_sequence, event_id
        ) AS previous_timestamp
    FROM `careflow-analytics-98234.careflow_analytics.event_logs_test`
    WHERE case_id IS NOT NULL
      AND activity IS NOT NULL
      AND timestamp IS NOT NULL
),
transitions AS (
    SELECT
        previous_activity,
        activity AS current_activity,
        TIMESTAMP_DIFF(timestamp, previous_timestamp, SECOND) / 60.0
            AS elapsed_minutes
    FROM ordered_events
    WHERE previous_timestamp IS NOT NULL
      AND previous_activity IS NOT NULL
      AND timestamp >= previous_timestamp
),
summary AS (
    SELECT
        previous_activity,
        current_activity,
        COUNT(*) AS transition_count,
        ROUND(AVG(elapsed_minutes), 2) AS mean_elapsed_minutes,
        ROUND(APPROX_QUANTILES(elapsed_minutes, 100)[OFFSET(50)], 2)
            AS median_elapsed_minutes,
        ROUND(APPROX_QUANTILES(elapsed_minutes, 100)[OFFSET(90)], 2)
            AS p90_elapsed_minutes,
        ROUND(MAX(elapsed_minutes), 2) AS max_elapsed_minutes
    FROM transitions
    GROUP BY previous_activity, current_activity
    HAVING COUNT(*) >= 30
)
SELECT
    *,
    DENSE_RANK() OVER (ORDER BY p90_elapsed_minutes DESC)
        AS bottleneck_rank
FROM summary
ORDER BY bottleneck_rank, transition_count DESC;

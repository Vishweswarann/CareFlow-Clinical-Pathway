
-- CareFlow: Activity Transition Time Summary

WITH transitions AS (
  SELECT
    case_id,
    activity,
    timestamp,

    LAG(activity) OVER (
      PARTITION BY case_id
      ORDER BY timestamp, event_sequence, event_id
    ) AS previous_activity,

    LAG(timestamp) OVER (
      PARTITION BY case_id
      ORDER BY timestamp, event_sequence, event_id
    ) AS previous_timestamp

  FROM `careflow-analytics-98234.careflow_analytics.event_logs_test`
),

elapsed_times AS (
  SELECT
    previous_activity,
    activity AS current_activity,
    TIMESTAMP_DIFF(
      timestamp,
      previous_timestamp,
      SECOND
    ) / 60.0 AS elapsed_minutes
  FROM transitions
  WHERE previous_timestamp IS NOT NULL
)

SELECT
  previous_activity,
  current_activity,
  COUNT(*) AS transition_count,
  ROUND(AVG(elapsed_minutes), 2) AS mean_elapsed_minutes,
  ROUND(
    APPROX_QUANTILES(elapsed_minutes, 100)[OFFSET(50)], 2
  ) AS median_elapsed_minutes,
  ROUND(MAX(elapsed_minutes), 2) AS max_elapsed_minutes

FROM elapsed_times
WHERE elapsed_minutes >= 0
GROUP BY previous_activity, current_activity
ORDER BY median_elapsed_minutes DESC;

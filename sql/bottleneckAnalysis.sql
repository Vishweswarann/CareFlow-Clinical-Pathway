
-- CareFlow: Department and activity bottleneck analysis

SELECT
  department,
  activity,
  COUNT(*) AS total_events,
  ROUND(AVG(waiting_time_minutes), 2) AS avg_wait_minutes,
  APPROX_QUANTILES(waiting_time_minutes, 100)
    [OFFSET(50)] AS median_wait_minutes,
  MAX(waiting_time_minutes) AS max_wait_minutes
FROM
  `careflow-analytics-98234.careflow_analytics.event_logs_analysis`
WHERE
  waiting_time_minutes IS NOT NULL
GROUP BY
  department,
  activity
ORDER BY
  avg_wait_minutes DESC;

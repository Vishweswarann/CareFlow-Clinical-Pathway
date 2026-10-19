
-- CareFlow: Patient journey duration analysis

WITH case_summary AS (
  SELECT
    case_id,
    MIN(timestamp) AS case_start,
    MAX(timestamp) AS case_end,
    COUNT(*) AS event_count,
    COUNTIF(
      disposition = 'Left Without Being Seen'
    ) > 0 AS is_lwbs,
    COUNTIF(activity = 'Emergency Surgery') > 0
      AS had_emergency_surgery
  FROM
    `careflow-analytics-98234.careflow_analytics.event_logs_analysis`
  GROUP BY case_id
)
SELECT
  COUNT(*) AS total_cases,
  ROUND(
    AVG(TIMESTAMP_DIFF(case_end, case_start, MINUTE)), 2
  ) AS avg_journey_minutes,
  APPROX_QUANTILES(
    TIMESTAMP_DIFF(case_end, case_start, MINUTE), 100
  )[OFFSET(50)] AS median_journey_minutes,
  COUNTIF(is_lwbs) AS lwbs_cases,
  COUNTIF(had_emergency_surgery) AS surgery_cases,
  ROUND(AVG(event_count), 2) AS avg_events_per_case
FROM case_summary;

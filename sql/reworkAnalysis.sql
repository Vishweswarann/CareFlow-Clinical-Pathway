
-- CareFlow: Repeated activity and rework analysis

WITH case_activity_counts AS (
  SELECT
    case_id,
    activity,
    COUNT(*) AS activity_visits
  FROM
    `careflow-analytics-98234.careflow_analytics.event_logs_analysis`
  GROUP BY
    case_id,
    activity
),
rework_summary AS (
  SELECT
    case_id,
    SUM(
      GREATEST(activity_visits - 1, 0)
    ) AS extra_visits
  FROM case_activity_counts
  GROUP BY case_id
)
SELECT
  COUNT(*) AS total_cases,
  COUNTIF(extra_visits > 0) AS cases_with_rework,
  SUM(extra_visits) AS total_extra_visits,
  ROUND(
    100.0 * COUNTIF(extra_visits > 0) / COUNT(*), 2
  ) AS rework_case_percentage,
  ROUND(AVG(extra_visits), 2) AS avg_extra_visits_per_case
FROM rework_summary;

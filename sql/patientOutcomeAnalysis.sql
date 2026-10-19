
-- CareFlow: Patient outcome and LWBS analysis

WITH case_outcomes AS (
  SELECT
    case_id,
    ARRAY_AGG(
      disposition IGNORE NULLS
      ORDER BY event_sequence DESC
      LIMIT 1
    )[SAFE_OFFSET(0)] AS final_disposition,
    COUNT(*) AS event_count
  FROM
    `careflow-analytics-98234.careflow_analytics.event_logs_analysis`
  GROUP BY case_id
)
SELECT
  COALESCE(final_disposition, 'Unknown')
    AS final_disposition,
  COUNT(*) AS total_cases,
  ROUND(
    100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2
  ) AS percentage_of_cases,
  ROUND(AVG(event_count), 2) AS avg_events_per_case
FROM case_outcomes
GROUP BY final_disposition
ORDER BY total_cases DESC;

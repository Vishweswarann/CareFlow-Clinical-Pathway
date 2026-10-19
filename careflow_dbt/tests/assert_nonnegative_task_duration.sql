SELECT *
FROM {{ ref('stg_event_logs') }}
WHERE task_duration_minutes < 0
SELECT *
FROM {{ ref('stg_event_logs') }}
WHERE waiting_time_minutes < 0
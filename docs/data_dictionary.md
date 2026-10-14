# Data dictionary: synthetic ED event log

All data is **fictional**. Probabilities are design choices for testing, not real hospital statistics, and nothing is copied from MIMIC-IV or any real patient record.

One row = one event inside one hospital encounter. The file is sorted by `timestamp` across the whole hospital.

| # | Column | Level | Type | Example | Purpose |
|---|---|---|---|---|---|
| 1 | `event_id` | event | string, unique | `EV0000042` | Primary key of an event row. |
| 2 | `case_id` | encounter | string | `ED000007` | Groups events into one encounter (the process-mining "case"). |
| 3 | `activity` | event | string | `Imaging` | What happened. One of 9 activities. |
| 4 | `timestamp` | event | datetime `YYYY-MM-DD HH:MM:SS` | `2025-03-02 14:05:11` | When it happened. Strictly increasing within a case. |
| 5 | `department` | event | string | `Radiology` | Responsible department. Determined by `activity`. |
| 6 | `event_sequence` | event | int | `4` | Position of the event inside its case (1, 2, 3 ...). Makes ordering explicit and survives re-sorting. |
| 7 | `resource_role` | event | string | `Radiographer` | Role of the staff member who performed the step. Determined by `activity`. |
| 8 | `resource_id` | event | string | `RAD03` | Fictional staff member. Enables workload and per-doctor analysis. |
| 9 | `event_detail` | event | string | `CT Scan` | Sub-type of the activity (test type, imaging modality, loop-back reason, ward ...). |
| 10 | `arrival_mode` | encounter | string | `Ambulance` | Walk-in, Ambulance or Transfer. |
| 11 | `age_group` | encounter | string | `65+` | `0-17`, `18-34`, `35-49`, `50-64`, `65+`. Supports demographic drill-down. |
| 12 | `gender` | encounter | string | `Female` | Fictional demographic attribute for drill-down. |
| 13 | `chief_complaint` | encounter | string | `Chest pain` | Reason for visit (8 categories). Influences how many tests are ordered. |
| 14 | `triage_level` | encounter | int 1-5 | `2` | 1 = most urgent, 5 = least urgent. |
| 15 | `disposition` | encounter | string | `Admitted` | `Admitted` or `Discharged`. Always matches the final event. |

## Activities
`Registration`, `Triage`, `Doctor Consultation`, `Laboratory Testing`, `Imaging`, `Treatment`, `Reassessment`, `Discharge`, `Hospital Admission`.

## Consistency rules (guaranteed by construction, checked by pytest)
- Encounter-level columns (10-15) are chosen once per encounter and copied to every row of it.
- Every case starts `Registration > Triage` and ends with exactly one of `Discharge` (if `Discharged`) or `Hospital Admission` (if `Admitted`).
- `Triage` appearing twice means the patient was sent back after imaging (a deliberate loop-back, reason in `event_detail`).
- Lab testing, treatment and reassessment can repeat.

## Deliberately NOT included
Derived values such as waiting time between events, length of stay, shift, or bottleneck flags are left out on purpose. They are the job of the dbt and PM4Py stages, so computing them here would duplicate teammates' work and risk inconsistent definitions.

## Mapping to PM4Py / XES naming
| This log | XES / PM4Py standard name |
|---|---|
| `case_id` | `case:concept:name` |
| `activity` | `concept:name` |
| `timestamp` | `time:timestamp` |
| `resource_id` | `org:resource` |
| `resource_role` | `org:role` |

# Exploratory Data Analysis Reports

This directory contains reports generated during exploratory data analysis of the synthetic emergency department (ED) event log.

## Report Descriptions

| File | Purpose |
|---|---|
| `activity_frequency.csv` | Frequency of activities recorded in the event log. |
| `activity_frequency.png` | Visual summary of activity frequencies. |
| `activity_interval_summary.csv` | Mean and median elapsed times for each activity-to-activity transition, including transition counts. |
| `age_group_distribution.csv` | Distribution of encounters by age group. |
| `arrival_mode_distribution.csv` | Distribution of encounter arrival modes. |
| `disposition_distribution.csv` | Distribution of final encounter dispositions. |
| `encounter_duration.png` | Visualization of encounter durations. |
| `encounter_summary.csv` | Encounter-level summary data. |
| `gender_distribution.csv` | Distribution of recorded gender categories. |
| `resource_role_distribution.csv` | Distribution of events by resource role. |
| `top_pathway_variants.csv` | Most frequently observed activity sequences. |
| `triage_level_distribution.csv` | Distribution of encounters by triage level. |



## Activity Transition Analysis

The `activity_interval_summary.csv` report summarizes elapsed time between consecutive events within each patient encounter.

Each row represents a specific transition between two hospital activities.

### Report Columns

| Column | Description |
|---|---|
| `from_activity` | Activity at the beginning of the transition. |
| `to_activity` | Activity at the end of the transition. |
| `mean_interval_minutes` | Average elapsed time between the two events. |
| `median_interval_minutes` | Median elapsed time between the two events. |
| `transition_count` | Number of times the transition occurred. |

### Example Findings

The generated synthetic dataset includes the following results:

- Doctor Consultation to Hospital Admission: median 62.52 minutes across 95 transitions.
- Doctor Consultation to Reassessment: median 54.40 minutes across 3,345 transitions.
- Triage to Doctor Consultation: median 33.68 minutes across 33,169 transitions.

These statistics help identify transitions that may deserve further investigation during process mining.

### Interpretation Limitations

Transition intervals measure elapsed time between consecutive event timestamps. They do not necessarily represent pure waiting time because they may include activity execution time.

A long interval does not automatically establish a bottleneck.

All results come from synthetic data and should not be interpreted as real hospital performance.



## Intended Use

These reports support initial exploration of activity frequencies, encounter characteristics, resource roles, durations, and pathway variations. They can help identify patterns for further process-mining analysis.

All underlying patient encounters are synthetic. Observed patterns reflect the generator's design and should not be interpreted as real hospital statistics.

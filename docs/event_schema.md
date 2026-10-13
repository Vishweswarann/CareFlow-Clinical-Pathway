# CareFlow — Synthetic EHR Event Schema

## 1. Overview

CareFlow is a Clinical Pathway Process Mining project that analyses how hospital encounters progress through clinical activities, identifies variations in patient journeys, and investigates potential operational delays.

This document describes the schema of the synthetic Emergency Department (ED) event log generated for the project.

The dataset contains entirely fictional records created using Python and pandas. It does not contain real patient information and must not be interpreted as actual hospital statistics.

## 2. Dataset Summary

| Property | Value |
|---|---|
| Dataset type | Synthetic Emergency Department event log |
| Generation language | Python |
| Data processing library | pandas |
| File format | CSV |
| Number of encounters in the current full dataset | 5,000 |
| Number of events in the current full dataset | 34,680 |
| Number of columns | 8 |
| Number of activity types | 9 |
| Random seed used | 42 |
| Arrival date range configured | 2025-01-01 over 365 days |
| Full dataset path | `data/ehr_events_full.csv` |
| Sample dataset path | `data/sample/ehr_events_sample.csv` |

The full dataset contains multiple events per encounter. Therefore, the number of event records is greater than the number of encounters.

## 3. Event-Level Schema

Each row represents one activity performed during a hospital encounter.

| Column | Description | Purpose |
|---|---|---|
| `event_id` | Unique identifier for an event | Distinguishes individual event records |
| `case_id` | Unique identifier for a hospital encounter | Groups events belonging to the same encounter |
| `activity` | Name of the clinical activity performed | Represents a step in the clinical pathway |
| `timestamp` | Date and time associated with the event | Establishes event order and supports duration analysis |
| `department` | Department responsible for the activity | Supports department-level analysis |
| `arrival_mode` | Synthetic mode of arrival | Provides encounter context |
| `triage_level` | Synthetic triage urgency level from 1 to 5 | Supports grouping by assigned urgency |
| `disposition` | Encounter outcome, such as discharge or hospital admission | Identifies how the encounter concludes |

### Identifier conventions

- `event_id` identifies an individual event and must be unique across the dataset.
- `case_id` identifies an encounter and is shared by all events within that encounter.
- A single encounter may contain several events.
- The dataset does not use real patient identifiers.

### Timestamp conventions

Timestamps represent the generated times of clinical activities. Events within an encounter are expected to occur in chronological order.

Differences between consecutive timestamps can be used to calculate elapsed time between activities. These differences should not automatically be interpreted as pure waiting time because they may include processing time or other intervals.

## 4. Clinical Activities

The current dataset contains nine activity types.

| Activity | Description |
|---|---|
| Registration | Recording the encounter at arrival |
| Triage | Initial urgency assessment |
| Doctor Consultation | Clinical consultation |
| Laboratory Testing | Laboratory investigation |
| Imaging | Diagnostic imaging |
| Treatment | Treatment-related activity |
| Reassessment | Follow-up clinical assessment |
| Discharge | Ending the encounter with discharge |
| Hospital Admission | Ending the ED encounter with hospital admission |

The generator supports variations in the sequence and number of activities. Some encounters include diagnostic testing, repeated activities, reassessments, or longer intervals between events.

These sequences are simplified synthetic representations intended for process-mining experimentation. They are not clinical guidelines.

## 5. Synthetic Data Generation Assumptions

The dataset is generated programmatically using Python and pandas.

The generator supports configuration of:
- Number of encounters
- Random seed
- Output CSV path
- Start date
- Number of days over which arrivals are generated

A fixed random seed makes generation reproducible when the code, configuration, and software environment remain unchanged.

Pathway choices, activity frequencies, and time intervals are generated according to assumptions encoded in the script. They have not been established as representative of real hospital populations or operational performance.

## 6. Data Quality Requirements

The generated event log should satisfy the following checks:

1. All required columns are present.
2. Event identifiers are unique.
3. Encounter identifiers are valid.
4. Required fields contain no missing values.
5. Timestamps can be parsed as valid date-time values.
6. Events are chronologically ordered within each encounter.
7. Encounter-level attributes remain consistent across events belonging to the same encounter.
8. Each encounter ends with an appropriate terminal event.
9. Activity and department values follow the generator's definitions.

Initial validation of the 5,000-encounter dataset found:
- 34,680 event records
- 5,000 unique encounters
- 34,680 unique event identifiers
- Zero missing values
- Zero invalid timestamps
- Zero out-of-order adjacent events in the generated CSV
- Zero encounters without a terminal event

These results describe the checks performed so far. Further automated testing is required to verify pathway logic, reproducibility, and other constraints.

## 7. Process Mining Compatibility

The dataset is designed to support process mining with PM4Py.

The primary fields for event-log construction are:
- Case identifier: `case_id`
- Activity identifier: `activity`
- Timestamp: `timestamp`

The event log can support:
- Process discovery
- Process variant analysis
- Repeated-activity and loop analysis
- Elapsed-time analysis
- Identification of potential bottlenecks

Conformance checking requires an explicitly defined reference process model and is not established merely by generating the event log.

## 8. File Locations

- Python generator: `src/generate_ehr_events.py`
- Sample event log: `data/sample/ehr_events_sample.csv`
- Full event log: `data/ehr_events_full.csv`
- Requirements: `requirements.txt`
- Event schema documentation: `docs/event_schema.md`

The sample dataset is intended for quick inspection and testing. The full dataset is intended for the team's analysis and integration workflow.

## 9. Limitations

- All records are synthetic.
- Clinical pathways are simplified.
- Timing and activity distributions are assumptions.
- The dataset is not suitable for clinical decision-making.
- Data-quality checks do not establish clinical realism.
- The final schema and full-dataset sharing method should be confirmed with the project team before downstream integration.

## 10. Intended Use

This dataset is intended solely for the CareFlow academic project, including data ingestion, transformation, process mining, operational analysis, and dashboard development.
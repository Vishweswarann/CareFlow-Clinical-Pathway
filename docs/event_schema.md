# CareFlow — Synthetic EHR Event Schema

## 1. Overview

CareFlow is a Clinical Pathway Process Mining project that analyses how hospital encounters progress through clinical activities, identifies variations in patient journeys, and investigates potential operational delays.

This document describes the schema of the synthetic Emergency Department (ED) event log generated for the project.

All records are fictional and generated programmatically. The dataset contains no real patient information and must not be interpreted as actual hospital statistics or clinical guidance.

## 2. Dataset Summary

| Property | Value |
|---|---|
| Dataset type | Synthetic Emergency Department event log |
| Generation language | Python |
| Data processing library | pandas |
| File format | CSV |
| Events in the current full dataset | 200,004 |
| Encounters in the current full dataset | 28,737 |
| Number of columns | 15 |
| Number of activity types | 9 |
| Random seed used for the current dataset | 42 |
| Configured start date | 2025-01-01 |
| Full dataset path | `data/ehr_events_full.csv` |
| Sample dataset path | `data/sample/ehr_events_sample.csv` |

The full dataset contains multiple events per encounter. Therefore, the number of event records is greater than the number of encounters.

The event target is a minimum rather than an exact count because the generator completes encounters instead of cutting an encounter off to reach an exact row count.

## 3. Event-Level Schema

Each row represents one activity performed during a hospital encounter.

| Column | Description | Purpose |
|---|---|---|
| `event_id` | Unique event identifier | Distinguishes individual event records |
| `case_id` | Encounter identifier | Groups events belonging to the same encounter |
| `activity` | Clinical activity name | Represents a step in the clinical pathway |
| `timestamp` | Generated event date and time | Establishes event order and supports elapsed-time analysis |
| `department` | Department associated with the activity | Supports department-level analysis |
| `event_sequence` | Position of the event within its encounter, starting at 1 | Supports ordering and pathway reconstruction |
| `resource_role` | Fictional staff role assigned to the activity | Supports role-level analysis |
| `resource_id` | Fictional staff identifier | Identifies the assigned synthetic resource |
| `event_detail` | Generated description of the activity | Adds contextual detail to the event |
| `arrival_mode` | Synthetic mode of arrival | Provides encounter context |
| `age_group` | Synthetic age category | Supports age-group analysis |
| `gender` | Synthetic gender category | Supports demographic grouping |
| `chief_complaint` | Synthetic reason for the visit | Supports complaint-level pathway analysis |
| `triage_level` | Synthetic urgency level from 1 to 5 | Supports grouping by assigned urgency |
| `disposition` | Encounter outcome: discharge or admission | Identifies how the encounter concludes |

### Identifier conventions

- `event_id` must be unique across the dataset.
- `case_id` is shared by all events belonging to the same encounter.
- `event_sequence` starts at 1 and increases consecutively within each encounter.
- Resource identifiers refer to fictional staff members, not real employees.
- No real patient identifiers are used.

### Timestamp conventions

Timestamps represent generated event times. Events within an encounter are expected to be chronologically ordered.

Differences between consecutive timestamps measure elapsed time between recorded activities. They should not automatically be interpreted as pure waiting time because they may include other operational intervals.

## 4. Clinical Activities and Staff Roles

The generator supports nine activity types.

| Activity | Expected department | Assigned staff role |
|---|---|---|
| Registration | Front Desk | Registration Clerk |
| Triage | Triage | Triage Nurse |
| Doctor Consultation | Emergency Medicine | ED Physician |
| Laboratory Testing | Laboratory | Lab Technician |
| Imaging | Radiology | Radiographer |
| Treatment | Emergency Medicine | ED Nurse |
| Reassessment | Emergency Medicine | ED Nurse |
| Discharge | Emergency Medicine | ED Physician |
| Hospital Admission | Inpatient Admissions | Admissions Officer |

Encounters begin with Registration followed by Triage. Subsequent activities vary according to the generator's pathway rules. Encounters conclude with Discharge or Hospital Admission according to their generated disposition.

The generator may include diagnostic tests, repeated activities, reassessments, and other pathway variations. These are simplified synthetic representations, not clinical guidelines.

## 5. Synthetic Data Generation Assumptions

The generator supports configuration of:

- Encounter count or target event count
- Random seed
- Output CSV path
- Start date
- Number of days over which arrivals are generated

A fixed random seed makes generation reproducible when the code, configuration, and software environment remain unchanged.

The current generation command is:

```powershell
python src/generate_ehr_events.py --target-events 200000 --seed 42 --output data/ehr_events_full.csv
```

The generator produced 200,004 events across 28,737 encounters for this configuration.

### Waiting-time constraint

The generator draws waiting times using a lognormal distribution and applies a minimum wait of 60 seconds and a maximum wait of four hours for each individual event-to-event interval.

The four-hour maximum is a synthetic-data modeling constraint intended to limit extreme random draws. It is not a claim about actual hospital waiting-time standards. Total encounter duration can exceed four hours because an encounter may contain multiple intervals.

Pathway choices, activity frequencies, staff assignments, and timing distributions are assumptions encoded in the generator. They have not been established as representative of real hospital populations or operational performance.

## 6. Data Quality and Validation

The current dataset has been checked for:

- Required columns and missing values
- Duplicate event records and event identifiers
- Timestamp validity and chronological ordering
- Consecutive event sequence numbers
- Consistency of encounter-level attributes
- Activity-to-department mapping
- Correct encounter starts and terminal activities
- Activity-to-staff-role mapping
- Resource ID prefixes matching their assigned staff roles

The latest validation run reported:

- 200,004 event records and 28,737 encounters
- Zero missing values
- Zero exact duplicate rows
- Zero duplicate event identifiers
- Zero invalid or missing timestamps
- Zero negative or zero timestamp gaps
- Consecutive event sequences for every encounter
- Zero activity-to-department mismatches
- Zero incorrect final activities
- Zero resource-role mismatches
- Zero resource ID prefix mismatches

The automated test suite previously passed all 16 tests, including tests for schema, uniqueness, encounter structure, pathway variation, reproducibility, and target-event behavior.

These checks establish consistency with the implemented generation rules. They do not establish clinical realism or guarantee that every possible data-quality issue has been tested.

## 7. Process Mining Compatibility

The dataset is designed to support event-log construction in PM4Py.

The primary fields are:

- Case identifier: `case_id`
- Activity identifier: `activity`
- Timestamp: `timestamp`

Potential analyses include:

- Process discovery
- Pathway variant analysis
- Repeated-activity and loop analysis
- Elapsed-time analysis
- Investigation of potential bottlenecks

Conformance checking requires an explicitly defined reference process model; generating an event log alone does not establish conformance.

## 8. Project File Locations

- Generator: `src/generate_ehr_events.py`
- Automated tests: `tests/test_generate_ehr_events.py`
- Sample event log: `data/sample/ehr_events_sample.csv`
- Full generated event log: `data/ehr_events_full.csv`
- Data dictionary: `docs/data_dictionary.md`
- Event schema: `docs/event_schema.md`
- Data validation: `src/eda_validation.py`
- EDA analysis: `src/eda_analysis.py`
- Runtime dependencies: `requirements.txt`
- Development dependencies: `requirements-dev.txt`
- CI workflow: `.github/workflows/ci.yml`

The full generated dataset is excluded from normal Git tracking by the project's ignore rules. Coordinate a separate handoff method with the team if the full CSV is required by other contributors.

## 9. Limitations

- All records are synthetic.
- Clinical pathways are simplified.
- Activity and timing distributions are assumptions.
- The four-hour interval cap is a generation constraint, not a real-world standard.
- The dataset is not suitable for clinical decision-making.
- Data-quality checks do not establish clinical validity.
- Downstream integration and the full-dataset sharing method should be confirmed with the project team.

## 10. Intended Use

This dataset is intended for the CareFlow academic project, including data ingestion, transformation, process mining, operational analysis, and dashboard development.
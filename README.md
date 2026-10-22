# CareFlow-Clinical-Pathway


## Overview

CareFlow is a clinical pathway process-mining project that uses synthetic Electronic Health Record (EHR) event data to study patient journeys through a hospital workflow.

The project generates realistic, structured patient encounter events and validates them for consistency, event ordering, and logical correctness. The generated event log can be used to explore clinical pathways, identify common workflow patterns, and support further process-mining analysis.

**Current scope:** Synthetic EHR event generation, data validation, exploratory data analysis (EDA), and preparation of event logs for process mining.

## Key Features

- **Synthetic EHR data generation:** Generate configurable event logs using a reproducible random seed.
- **Patient encounter tracking:** Represent each encounter as an ordered sequence of clinical and administrative events.
- **Resource information:** Include staff roles and resource identifiers associated with events.
- **Data validation:** Check missing values, duplicate records, timestamp ordering, event sequences, and workflow consistency.
- **Exploratory data analysis:** Examine activity frequencies, encounter durations, waiting times, and pathway variants.
- **Automated testing:** Use pytest to test the generator's schema, reproducibility, and workflow rules.
- **Continuous integration:** Include a GitHub Actions workflow for automated checks.

## Dataset

The generator produces a synthetic event log containing **15 columns**.

| Column | Description |
|---|---|
| `event_id` | Unique identifier for an event |
| `case_id` | Identifier for a patient encounter |
| `activity` | Activity performed during the encounter |
| `timestamp` | Time at which the event occurred |
| `department` | Department responsible for the activity |
| `event_sequence` | Event order within an encounter |
| `resource_role` | Staff role associated with the event |
| `resource_id` | Identifier for the staff resource |
| `event_detail` | Additional event information |
| `arrival_mode` | How the patient arrived |
| `age_group` | Patient age category |
| `gender` | Synthetic patient gender category |
| `chief_complaint` | Primary reason for the visit |
| `triage_level` | Synthetic triage priority level |
| `disposition` | Final encounter outcome |

### Dataset size

The current full dataset contains **200,004 events across 28,737 encounters**. The number of events can vary slightly from the requested target because the generator preserves complete encounters rather than cutting an encounter off partway through.

The dataset is synthetic and is not real patient data.

## Clinical Workflow

The synthetic event log includes activities such as:

- Registration
- Triage
- Doctor Consultation
- Laboratory Testing
- Imaging
- Treatment
- Reassessment
- Hospital Admission
- Discharge

Not every encounter follows exactly the same pathway. This variation allows the event log to represent different workflow routes and outcomes.

## Project Structure

```text
CareFlow-Clinical-Pathway/
├── .github/
│   └── workflows/
│       └── ci.yml
├── data/
│   └── sample/
│       └── ehr_events_sample.csv
├── docs/
│   ├── data_dictionary.md
│   └── event_schema.md
├── reports/
│   └── eda/
├── src/
│   ├── generate_ehr_events.py
│   ├── eda_validation.py
│   └── eda_analysis.py
├── tests/
│   └── test_generate_ehr_events.py
├── .gitignore
├── requirements.txt
├── requirements-dev.txt
└── README.md
```

The full generated dataset is kept locally and excluded from Git tracking to avoid committing a large CSV file. The sample dataset is provided for reference.

## Setup

### 1. Clone the repository

```bash
git clone https://github.com/Vishweswarann/CareFlow-Clinical-Pathway.git
cd CareFlow-Clinical-Pathway
```

### 2. Create and activate a virtual environment

On Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 3. Install dependencies

```bash
python -m pip install -r requirements.txt
python -m pip install -r requirements-dev.txt
```

## Generate Synthetic EHR Events

To generate approximately 200,000 events:

```bash
python src/generate_ehr_events.py --target-events 200000 --seed 42 --output data/ehr_events_full.csv
```

The random seed makes the generated dataset reproducible when the generator configuration and software environment remain the same.

The generator also supports configurable encounter counts, output paths, start dates, and generation periods. Run the following command to inspect its available options:

```bash
python src/generate_ehr_events.py --help
```

## Validate the Dataset

Run the validation script against the generated dataset:

```bash
python src/eda_validation.py
```

The validation checks include:

- Missing values and duplicate records
- Unique event identifiers
- Valid timestamps and chronological event order
- Event sequence consistency within encounters
- Consistency of encounter-level attributes
- Activity-to-department mapping
- Valid starting and terminal activities
- Resource-role and resource-identifier consistency

The validation script reports its findings without modifying the dataset.

## Exploratory Data Analysis

Run the EDA script to analyze the generated event log:

```bash
python src/eda_analysis.py
```

The analysis examines activity frequencies, encounter characteristics, event timing, and pathway variants. Generated analysis outputs are saved under `reports/eda/`.

## Run Tests

Run the automated tests from the repository root:

```bash
python -m pytest -v
```

The tests cover generator behavior, schema expectations, event ordering, workflow rules, reproducibility, and target event-count handling.

## Data and Modeling Assumptions

- The records are synthetically generated for development and research.
- Encounter attributes remain consistent across events belonging to the same encounter.
- Event sequences are ordered chronologically within each encounter.
- The generator applies a four-hour cap to individual simulated waiting-time intervals.
- Synthetic workflow rules and distributions are assumptions, not validated representations of a real hospital.

## Limitations

Synthetic data can support pipeline development and process-mining experiments, but it does not establish that the observed patterns reflect actual clinical practice. Any conclusions from this dataset should be interpreted in light of the generator's assumptions.

## Contributors

This repository is developed collaboratively as part of the CareFlow Clinical Pathway Process Mining project.

See the repository's branches and commit history for individual contributions.

## Handoff to Person 2: BigQuery Ingestion

The synthetic EHR event log is available at `data/ehr_events_full.csv`.

The dataset contains 200,004 events across 28,737 encounters and includes 15 columns.

### Next steps

1. Load the CSV into a raw event-log table in Google BigQuery.
2. Enable the header row during import.
3. Verify the row count, column names, data types, and timestamp parsing.
4. Preserve `case_id`, `activity`, `timestamp`, and `event_sequence` for process-mining analysis.

Refer to `docs/event_schema.md` and `docs/data_dictionary.md` for the schema and column definitions.
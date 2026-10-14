# CareFlow: Clinical Pathway Process Mining

Stage 1 of the CareFlow pipeline: a reproducible generator of a **fictional** Emergency Department event log, built for BigQuery, dbt, PM4Py and Power BI.

> All data is synthetic. Nothing is copied from MIMIC-IV or any real patient, and the probabilities in the code are design choices, not real hospital statistics.

## Quick start (Windows PowerShell)

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt

# 100 encounters -> data/sample/ehr_events_sample.csv
python src/generate_ehr_events.py

# About 200,000 event rows (~29k encounters)
python src/generate_ehr_events.py --target-events 200000 --output data/ehr_events_200k.csv

# Fixed number of encounters, different seed
python src/generate_ehr_events.py --encounters 5000 --seed 7 --output data/ehr_events_5k.csv
```

The same `--seed` always produces the same file.

## Options

| Option | Default | Meaning |
|---|---|---|
| `--encounters N` | 100 | Create exactly N encounters. |
| `--target-events N` | none | Create encounters until at least N rows exist (never cuts an encounter in half). |
| `--seed N` | 42 | Random seed. |
| `--output PATH` | `data/sample/ehr_events_sample.csv` | Output CSV. |
| `--start-date` / `--days` | 2025-01-01 / 365 | Window in which encounters arrive. |

## Tests

```powershell
pytest -v
```

16 tests check unique IDs, no missing values, chronological timestamps, constant encounter attributes, valid start/end events, reproducibility and pathway variety.

## Schema

15 columns, described in [docs/data_dictionary.md](docs/data_dictionary.md).

## Project layout

```
src/generate_ehr_events.py   generator
tests/                       pytest suite
data/sample/                 small committed sample (100 encounters)
docs/                        data dictionary
```

## Using the log with PM4Py

```python
import pandas as pd, pm4py
df = pd.read_csv("data/ehr_events_200k.csv", parse_dates=["timestamp"])
df = pm4py.format_dataframe(df, case_id="case_id", activity_key="activity", timestamp_key="timestamp")
```
(Check the argument names against your installed PM4Py version.)

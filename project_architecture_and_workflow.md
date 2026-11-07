# CareFlow Project Architecture and Workflow

> **Scope and evidence.** This document describes the files and code present in the local `C:\Careflow` repository as inspected on 5 November 2026. It separates implemented behavior from report claims, configuration, and work that still needs coordination. The repository contains synthetic event data; metrics from it should not be interpreted as measured clinical performance.

## 1. Project overview and objectives

CareFlow is a clinical-pathway and process-analytics project built around a synthetic emergency-care event log. Its code supports exploring event sequences, activity frequencies, elapsed intervals between consecutive recorded events, basic data-quality checks, and process models. It also contains standalone CSV-to-BigQuery upload scripts and a local-only incremental-ingestion dry run.

The overall project objective, as represented by the source and reports, is to turn event records grouped into patient encounters into summaries that help explore pathway patterns and possible operational delays. The implementation is an analytics prototype: the event data is synthetic, “waiting time” may mean an interval between recorded activities, and no production clinical decision or operational workflow is established by the repository.

## 2. Implementation status at a glance

| Capability | Status evidenced in repository | Notes |
|---|---|---|
| Local event CSV validation and enrichment | Implemented as standalone scripts | `enhance_dataset.py` derives several columns from event text and event order; `fix_missing_values.py` checks and saves a cleaned local copy while preserving missing values. The scripts are not orchestrated as a single pipeline. |
| Transition elapsed-time analysis in Python | Implemented | `src/waiting_time_analysis.py` calculates intervals and transition summaries from a sample CSV. |
| Streamlit dashboard | Implemented | Supports CSV upload and a bounded BigQuery query, shared filters, five analysis pages, and CSV exports. |
| BigQuery upload | Implemented as direct scripts, subject to credentials and permissions | The scripts issue table load jobs; one truncates a test table and another truncates an enhanced table. These are manual scripts, not connected to the local dry-run pipeline. |
| SQL analytics | Query files implemented | Queries target different table names (`event_logs_test`, `event_logs_analysis`, and `event_logs`); the repository does not establish that all those tables exist or are synchronized. |
| dbt staging model and checks | Configured in source | A view selects from `event_logs_analysis`; schema tests and two non-negative checks are declared. A local dbt run is not proof of a successful run against the intended cloud target. |
| Nightly pipeline | Local dry-run only | `src/nightly_bigquery_pipeline.py` validates a CSV and compares IDs with a local test baseline. It explicitly performs no BigQuery query or write. A `.bat` launcher runs this dry run; a scheduler is not configured here. |
| Cloud incremental merge / production ingestion | Not implemented in the inspected nightly pipeline | `src/test_incremental_merge.py` tests a Pandas merge simulation only. The nightly-pipeline documentation lists a BigQuery staging and `MERGE` as future work. |
| Clinical/production deployment | Not evidenced | No live hospital-system integration, clinical validation, deployment configuration, or production automation was found in the inspected repository. |

## 3. Repository layout and component responsibilities

```text
C:\Careflow\
├── README.md                         # BigQuery test uploader overview
├── requirements.txt                  # Python package names
├── enhance_dataset.py                # Local feature derivation from simulated CSV
├── fix_missing_values.py             # Local validation/cleaned copy
├── run_nightly_pipeline.bat          # Windows launcher for local dry run
├── src/
│   ├── load_event_log.py             # Load bundled XES sample with PM4Py
│   ├── waiting_time_analysis.py      # Python transition-interval analysis
│   ├── nightly_bigquery_pipeline.py  # Local validation and ID comparison only
│   ├── pipeline_utils.py             # Logger and report helpers
│   ├── test_incremental_merge.py     # In-memory/local idempotency demonstration
│   ├── upload_to_bigquery.py         # CSV load to event_logs_test
│   └── upload_enhanced_to_bigquery.py# CSV load to event_logs_enhanced
├── data/
│   ├── ehr_events_full.csv           # 15-column event input used by pipeline/uploader
│   ├── sample/                       # XES sample and analysis input location
│   ├── processed/                    # Local derived/cleaned outputs
│   ├── pipeline_test/                # Small synthetic baseline and incoming batch
│   └── pipeline_reports/              # Dry-run report output
├── sql/                              # BigQuery analytics query files
├── dashboard/                        # Streamlit UI, auth, BigQuery reader
├── careflow_dbt/                     # dbt staging view and data tests
├── docs/                             # Nightly-pipeline notes and simulation report
└── tests/                            # Pytest/unittest coverage for analytics logic
```

The repository also contains root-level CSV datasets and generated/local artifacts. `.gitignore` excludes several generated datasets, processed outputs, logs, `.venv`, dbt `target`, credentials/configuration such as `profiles.yml`, and XES source files. Their presence on disk does not mean they are tracked or reproducible from the committed source alone.

### Main component boundaries

- **Data preparation:** root-level scripts read/write CSVs using local paths. The enrichment script uses relative filenames based on the current working directory; run it from the directory where its inputs are available.
- **Python analytics:** `src/waiting_time_analysis.py` works on a CSV and emits detailed intervals and grouped summaries under `data/processed/`.
- **Warehouse access:** the upload scripts load data to BigQuery; the dashboard reader queries a table; SQL files contain read-only analytics. These pieces have separate configuration and table targets.
- **Dashboard:** `dashboard/app.py` owns the interactive UI and recomputes its measures in Pandas from the currently selected source. It does not call the SQL analytics files.
- **Pipeline simulation:** the nightly script uses a local CSV and `data/pipeline_test/existing_events.csv` as a baseline. It has no BigQuery client import or cloud writes.
- **dbt:** `careflow_dbt` defines a staging view and tests, but no `profiles.yml` is present in the inspected root (and that file is ignored); credentials, target profile, and a successful cloud run need confirmation.

## 4. Technology stack

- Python, with Pandas and NumPy for tabular preparation/analysis.
- PM4Py for loading XES event logs and discovering process models in the dashboard.
- Streamlit for the dashboard; Plotly for charts; PyVis for the interactive filtered pathway diagram when installed; Graphviz visualizers are used for selected PM4Py models.
- Google Cloud BigQuery Python client for direct CSV loading and dashboard queries; Google authentication uses Streamlit service-account secrets when available or Application Default Credentials locally.
- BigQuery Standard SQL for warehouse analytics.
- SQLite and Python standard-library hashing utilities for local dashboard account storage.
- dbt for a BigQuery staging view and declared model/data tests.
- pytest and unittest-style test code for local logic.

The root `requirements.txt` lists `streamlit`, `pandas`, `plotly`, `google-cloud-bigquery`, `db-dtypes`, `pm4py`, and `pyvis`. It does not pin versions and does not list every library used by all checked-in scripts (for example NumPy is imported by `enhance_dataset.py`; `dbt` and Graphviz also need separate installation/configuration). A reproducible lockfile or environment specification is not present.

## 5. Dataset and schema

### Data sources found

1. **Synthetic EHR CSVs:** `data/ehr_events_full.csv` is used by the local nightly dry run and `src/upload_to_bigquery.py`. The pipeline requires 15 columns. Root-level `ehr_events_simulated.csv` and `ehr_events_enhanced.csv` are used by `enhance_dataset.py` and `src/upload_enhanced_to_bigquery.py`, respectively. The enhanced script derives 4 additional fields, producing a 19-field shape when starting from the 15-field event schema.
2. **XES sample:** `data/sample/Sepsis Cases - Event Log.xes.gz` is loaded by `src/load_event_log.py` with PM4Py. The Python waiting-time script instead points at `data/sample/ehr_events_sample.csv`; that CSV was not present in the inspected file list, so that script's default input currently needs confirmation/provisioning.
3. **Small pipeline fixtures:** `data/pipeline_test/existing_events.csv` and `incoming_events.csv` exercise ID matching/merge behavior and are not the full project dataset.

### Event columns

The 15-column pipeline/uploader schema is: `event_id`, `case_id`, `activity`, `timestamp`, `department`, `event_sequence`, `resource_role`, `resource_id`, `event_detail`, `arrival_mode`, `age_group`, `gender`, `chief_complaint`, `triage_level`, and `disposition`.

The enrichment script adds:

- `task_duration_minutes`: numeric value extracted from text matching `task duration ~N min` in `event_detail`.
- `waiting_time_minutes`: numeric value extracted from `queue delay ~N min` text.
- `arrival_timestamp`: earliest recorded event timestamp per `case_id`; code comments clarify this is the first recorded event, not necessarily actual arrival.
- `minutes_until_next_event`: elapsed time to the next timestamp in the case. It is an event gap, not task duration.

The enhancement code leaves unparseable/missing duration and wait values as null. Despite claims in `docs/simulation_analysis_summary.md` that missing values were imputed to zero/assumed values, the inspected `enhance_dataset.py` explicitly preserves these values as `NaN`, and `fix_missing_values.py` says it preserves missing values rather than inventing clinical durations. Resolve this report/code discrepancy before relying on reported zero-missing counts.

`data/processed/ehr_events_cleaned.csv` shows these 19 columns in its header. Data files on disk may differ in row counts and provenance: the local dry-run report records 200,004 incoming rows and 0 IDs in its local baseline, while project reports describe an enhanced set of 198,258 events, 28,737 cases, and 19 columns. Treat those as reports about different snapshots unless the dataset versions are reconciled. No schema contract or canonical source-of-truth table is declared in one place.

### Warehouse naming and schema caution

The project ID and dataset used in code/reports are `careflow-analytics-98234` and `careflow_analytics`. The code refers to several destination/source tables:

| Table | References |
|---|---|
| `event_logs_test` | README, `upload_to_bigquery.py`, `waitingTimeAnalysis.sql`, `caseDurationAnalysis.sql`, `pathwayBottleneckRanking.sql` |
| `event_logs_enhanced` | `upload_enhanced_to_bigquery.py`, BigQuery integration report |
| `event_logs_analysis` | Other SQL analytics and dbt staging model |
| `event_logs` | Dashboard reader, `bigquery_test.py`, `dataQualityChecks.sql` |

All are code references, not evidence that every table currently exists or contains the same dataset. The README's uploader explicitly uses a test table and a truncating load disposition. The enhanced uploader also uses `WRITE_TRUNCATE`. Before connecting these components, the team needs to choose and document the canonical table, field types, refresh semantics, and owners. SQL queries that expect derived duration/wait columns need a table with those fields, whereas the 15-column test upload schema does not include them.

## 6. End-to-end data flow (as implemented)

There are useful pieces, but no single end-to-end orchestrator wires all stages together:

```text
Synthetic CSV ──> optional local enrichment ──> optional cleaned copy
      │                    │
      ├──> local dry-run validation + local baseline ID comparison ──> report/log
      ├──> standalone BigQuery test-table upload
      └──> standalone enhanced-table upload (different CSV and table)

BigQuery tables ──> standalone SQL queries / dbt view and tests
       └───────────> dashboard BigQuery reader (limited sample)

User CSV upload ──> dashboard validation ──> Pandas metrics / charts / downloads
```

There is no demonstrated automatic handoff from enrichment to upload, from pipeline dry-run to a cloud `MERGE`, from SQL outputs to dashboard pages, or from a scheduled job to the dashboard. Dashboard charts are recalculated from loaded event records in memory. The BigQuery option selects at most 200, 500, or 1,000 records, while the data-reader function enforces a maximum of 1,000 and uses a 20 MB maximum billed query limit with a 30-minute Streamlit data cache.

## 7. Python preprocessing and enrichment

`enhance_dataset.py` reads `ehr_events_simulated.csv` and writes `ehr_events_enhanced.csv` in the current working directory. It parses timestamps with mixed formats/day-first behavior, sorts by case/time/sequence, extracts the two approximate metrics from `event_detail`, sets the first event timestamp per encounter, calculates the next-event gap, prints row/case/duplicate/missing/negative checks, formats timestamps as strings, and saves CSV. It does not write to BigQuery.

`fix_missing_values.py` reads the root enhanced CSV and writes `data/processed/ehr_events_cleaned.csv`. It checks required columns, reports ID and numeric missingness, converts duration/wait/interval columns to numeric, counts negative intervals, and retains missing values. It performs no cloud operation.

`src/load_event_log.py` reads the compressed XES sample with PM4Py, converts it to a DataFrame, and prints basic counts, fields, a preview, and null counts. It is an inspection script; it does not persist a CSV or feed the other scripts automatically.

`src/waiting_time_analysis.py` parses timestamps, drops rows missing case/activity/time, sorts by case/time and by event ID when available, uses a per-case previous-event shift, computes elapsed minutes, counts and excludes negative intervals, and saves interval details and transition aggregates (count, mean, median, max) to `data/processed/`. The default input path currently points to a CSV absent from the inspected file listing.

## 8. BigQuery storage and integration

### Standalone CSV load scripts

- `src/upload_to_bigquery.py` reads `data/ehr_events_full.csv`, validates required column presence, parses timestamps, rejects duplicate `event_id`, supplies an explicit 15-field schema, and loads to `careflow-analytics-98234.careflow_analytics.event_logs_test` with `WRITE_TRUNCATE`. It requires working Google credentials, BigQuery permissions, and billing/project setup. Running it performs a real cloud table load; it is not dry-run safe.
- `src/upload_enhanced_to_bigquery.py` reads root `ehr_events_enhanced.csv`, uses schema autodetection, and loads to `event_logs_enhanced` with `WRITE_TRUNCATE`. It requires BigQuery credentials and table write permissions. This script does not run automatically as part of the nightly dry-run.
- `dashboard/bigquery_data.py` reads from `event_logs`, selecting `case_id`, `activity`, `timestamp`, and `department`, excludes null core fields, sorts by case/time, caps rows at 1,000 and billed bytes at 20 MB, and caches results for 1,800 seconds. It uses service-account credentials from Streamlit secrets when available, with ADC fallback.

The README describes `event_logs_test` as the test target and notes that nightly automated ingestion is not configured. `docs/nightly_pipeline.md` says cloud write testing is pending due to billing access. The existence of upload code is therefore distinct from proof that a given upload was run successfully in the current environment.

### Authentication in dashboard

`dashboard/auth.py` stores accounts in a local SQLite database at `dashboard/users.db`. Passwords are salted and derived with PBKDF2-HMAC-SHA256 (600,000 iterations); comparisons use constant-time `hmac.compare_digest`. This is local app authentication code. The repository does not show a deployment-specific identity provider, account recovery, or centralized user store.

## 9. SQL and process analytics

The `sql/` directory contains read-only BigQuery queries for:

- `waitingTimeAnalysis.sql`: previous/current activity transitions per case, event-gap minutes, count/mean/median/max.
- `pathwayBottleneckRanking.sql`: deterministic event ordering, transition percentiles, minimum transition sample of 30, and ranking by p90 gap.
- `bottleneckAnalysis.sql`: average/median/max of `waiting_time_minutes` by department and activity.
- `caseDurationAnalysis.sql` and `patientJourneyAnalysis.sql`: first-to-last recorded event duration per case and journey summaries.
- `reworkAnalysis.sql`: repeated activity visits per case, treating extra same-activity visits as a rework proxy.
- `patientOutcomeAnalysis.sql`: final disposition per case based on descending event sequence, outcome counts/percentages.
- `dataQualityChecks.sql`: null/blank and distinct event ID counts plus duplicate ID listing.

The SQL is analytics source code, not an automated job or dashboard data service. Queries use different table names and depend on appropriate schemas. For example, transition-gap SQL can run against an event table with the core event fields, while department bottleneck analysis expects the derived `waiting_time_minutes` field. The term “waiting time” needs careful interpretation: a gap between recorded events is not necessarily time spent waiting, nor does event text extraction establish a validated operational measurement. Repeated activity is likewise only a proxy for rework.

## 10. Pipeline and dry-run behavior

`src/nightly_bigquery_pipeline.py` labels itself local dry-run only and has no BigQuery dependency. By default it reads `data/ehr_events_full.csv`, requires the 15 event columns, normalizes `event_id`, rejects blank/duplicate incoming IDs, parses timestamp values as UTC, then compares incoming IDs to `data/pipeline_test/existing_events.csv`. The baseline is a small local fixture; it is not queried from BigQuery. It writes `data/pipeline_reports/dry_run_report.txt` and `logs/nightly_pipeline.log`, reporting that no cloud comparison or writes occurred.

`run_nightly_pipeline.bat` activates the local Windows `.venv` and runs that script. The launcher is a convenience entry point; no Windows Task Scheduler, cloud scheduler, CI schedule, retry mechanism, alerting, or production schedule was found in the inspected files. The name “nightly” does not mean the script is scheduled.

`src/test_incremental_merge.py` creates small Pandas fixture DataFrames, merges new rows by `event_id`, reruns the same batch to demonstrate idempotency, and writes `data/pipeline_test/merged_events.csv`. It does not connect to BigQuery and does not prove cloud `MERGE` behavior or transaction safety.

`src/pipeline_utils.py` defines logger/report helpers, but the nightly script contains its own logger and report code. This helper is not imported by the pipeline, so it is not the active path for the current dry run.

## 11. Dashboard pages and data sources

`dashboard/app.py` provides login/sign-up, then a sidebar with five pages, a data-source selector, and shared activity/case filters. Input needs `case_id`, `activity`, and `timestamp`; `event_timestamp` is renamed to `timestamp` if needed. Timestamps parse as UTC, blank/invalid required rows are removed, and events are sorted by case and time. Transition metrics are calculated over the complete timeline before filtering so filtering does not create false adjacency between separated events.

Data source choices:

- **CSV Upload:** user-provided CSV, with no default local file selected automatically.
- **BigQuery:** limited query from `dashboard/bigquery_data.py`; selectable sample size is 200/500/1,000. It queries `event_logs` and loads department with core fields.

Pages:

1. **Overview:** event/encounter/activity counts, mean elapsed interval, top activities, long-mean transitions, department distribution if available, frequent observed pathway transitions (up to 20), and event counts over time.
2. **Activity Analysis:** activity counts, frequency chart, summary table, CSV download.
3. **Elapsed-Time Analysis:** mean/median/max intervals, transitions with high mean interval, transition statistics table, CSV download. The page caveat says intervals are not necessarily waiting or proof of delay.
4. **Data Quality:** row counts before/after validation, invalid rows removed, missing/invalid required values and negative interval indicators, data preview, CSV report download. These checks concern the selected sample, not a warehouse-wide audit.
5. **Process Mining:** uses the loaded and filtered event data with PM4Py for Heuristics Net, directly-follows graph, and Petri Net options; also includes a frequency-filtered DFG described explicitly as a fuzzy-style abstraction rather than PM4Py's native Fuzzy Miner, an interactive PyVis view when available, and a patient event timeline. This page does not issue a separate BigQuery analytics query.

The dashboard is interactive analytics over whichever rows were loaded. A BigQuery query limit means the displayed process graph and metrics may represent only a partial sample, not full hospital pathways.

## 12. Testing and verification coverage

The repository includes:

- `tests/test_nightly_pipeline.py`: tests event ID set comparison for first run, repeated batch, mixed IDs, empty input, and no input-set mutation. These test the pure comparison function, not CSV validation against BigQuery or cloud writes.
- `tests/test_process_analytics.py`: tests per-case elapsed intervals, no cross-case transitions, transition counts/statistics, exclusion of invalid timestamps, required column errors, and single-event cases.
- `src/test_incremental_merge.py`: executable assertion-based simulation of repeated batch idempotency.
- `dashboard/bigquery_test.py`: a BigQuery query for activity counts with a maximum billed bytes setting; requires credentials and a live BigQuery table.
- dbt model tests for uniqueness/non-null fields and custom SQL assertions for negative task duration/wait time.

Tests are code evidence, not a record that they were run successfully in this documentation task. The local baseline and dry-run report are generated artifacts and should not be interpreted as a test of live ingestion. Warehouse/dbt checks require valid profiles, permissions, table schema, and actual execution against the intended dataset.

## 13. Setup and execution workflow

### Local Python environment

1. Install a supported Python version and create/activate a virtual environment.
2. Install the root `requirements.txt`; install/configure additional tools such as dbt and Graphviz separately if you use those components.
3. Run commands from `C:\Careflow` unless the script's relative paths require another working directory.

Representative local commands (PowerShell):

```powershell
python -m pip install -r requirements.txt
python src\load_event_log.py
python src\waiting_time_analysis.py
python enhance_dataset.py
python fix_missing_values.py
python src\nightly_bigquery_pipeline.py
python src\test_incremental_merge.py
streamlit run dashboard\app.py
```

The load-event script expects the bundled XES file. The waiting-time script's configured CSV input was absent from the inspected repository listing and may need to be supplied or the path updated by the project owner. `enhance_dataset.py` expects `ehr_events_simulated.csv` in the current working directory and writes `ehr_events_enhanced.csv` there. `fix_missing_values.py` expects the enhanced CSV at the repository root. Commands that write files create local derived outputs.

### BigQuery access

Before running either uploader or choosing BigQuery in the dashboard, confirm Google Cloud credentials (ADC or Streamlit service-account secrets), project/dataset permissions, billing configuration, target table, and intended overwrite behavior. The upload scripts use `WRITE_TRUNCATE`, so each replaces the target table contents. Execute only when that overwrite is intended. The direct uploader is a cloud write, whereas the nightly pipeline command is local-only.

### dbt

`careflow_dbt/dbt_project.yml` declares a dbt project; `profiles.yml` is not present in the inspected repository and is ignored by Git. Configure a profile and verify the source table/project before running dbt. The staging model currently selects all fields from `event_logs_analysis` as a view. A dbt project configuration alone does not mean the model has been built or its tests passed in the target warehouse.

## 14. Limitations and future improvements

### Current limitations

- Synthetic data only; reported observations are not measured hospital operations.
- Several reports make claims about imputation and dataset counts that do not match all current code/artifacts; resolve data snapshot and metric lineage.
- Conflicting BigQuery table names and potentially different schemas across uploaders, SQL, dbt, and dashboard.
- No single orchestrated ingestion/enrichment/warehouse/dashboard flow; nightly pipeline is local dry run using a small baseline.
- No live BigQuery incremental comparison or tested cloud `MERGE`; direct loaders overwrite target tables.
- No configured scheduler, monitoring, retry/alerting, deployment setup, or production credential provisioning is shown.
- Dashboard BigQuery data is limited to 1,000 records and cached; a partial sample can distort process maps and metrics.
- Dashboard schema checks only require case, activity, and timestamp; other analytics may require additional fields.
- Python waiting-time analysis points to a sample CSV not listed in the repository contents.
- Dependencies are unpinned and the setup does not provide a lockfile or documented Python/dbt version matrix.
- Repeated activities and inter-event gaps are proxies; they do not establish avoidable rework or actual waiting time.

### Suggested next steps (proposals, not implemented behavior)

1. Agree on a canonical event schema, timestamp/sequence ordering, source dataset version, and canonical BigQuery table; document table ownership and table-refresh policy.
2. Resolve the discrepancy between code-preserved nulls and report claims of imputed complete durations/waits; add explicit derivation lineage and avoid undocumented imputations.
3. Align direct loaders, SQL queries, dbt sources/models, and dashboard reader on the canonical table and field contract.
4. If authorized and cloud access is available, design a staging plus idempotent BigQuery `MERGE`, then validate it in a non-production dataset with repeat-batch and failure-recovery tests before scheduling.
5. Add a real orchestrator only after owners agree on source delivery, schedule, credentials, monitoring, retries, and write semantics; keep dry-run and write modes unambiguous.
6. Replace sample-only dashboard analysis with aggregate warehouse queries or explicit pagination when full-population analysis is required; show sample coverage in the UI.
7. Provide a reproducible environment specification, deterministic input paths, and a setup guide including dbt profile requirements.
8. Clarify whether local SQLite accounts are suitable for the intended deployment or replace them with the deployment's managed identity solution.
9. Have domain owners validate definitions and interpretations for task duration, waiting time, patient journey, outcomes, and rework proxies before treating analytics as operational measures.

## 15. Questions and gaps for project-owner confirmation

- Which dataset version is authoritative (200,004-row local full CSV vs. 198,258-row enhanced dataset described in reports), and what explains the difference?
- Which BigQuery table is canonical: `event_logs_test`, `event_logs_enhanced`, `event_logs_analysis`, or `event_logs`? Which table does the dashboard deployment actually use?
- Does the team intend `waiting_time_minutes` to be parsed from synthetic `event_detail`, derived from event gaps, or both as distinct measures?
- Are the claimed imputation values and outcome figures from a separate script or prior data snapshot? They are not produced by the inspected current enrichment/cleaning scripts.
- Should the absent `data/sample/ehr_events_sample.csv` be added, or should `src/waiting_time_analysis.py` use another checked-in file?
- Who owns cloud table creation, dbt profile/target configuration, and any future scheduler or incremental ingestion implementation?
- Are local SQLite accounts only for demonstration, or is there a separate deployment authentication plan?

## 16. Source files inspected

The implementation review covered the repository structure and these files:

- Project/runtime: `README.md`, `requirements.txt`, `.gitignore`, `run_nightly_pipeline.bat`.
- Data prep and loading: `enhance_dataset.py`, `fix_missing_values.py`, `src/load_event_log.py`, `src/waiting_time_analysis.py`.
- BigQuery and pipeline: `src/upload_to_bigquery.py`, `src/upload_enhanced_to_bigquery.py`, `src/nightly_bigquery_pipeline.py`, `src/pipeline_utils.py`, `src/test_incremental_merge.py`, `docs/nightly_pipeline.md`.
- SQL: all eight files under `sql/` (`bottleneckAnalysis.sql`, `caseDurationAnalysis.sql`, `dataQualityChecks.sql`, `pathwayBottleneckRanking.sql`, `patientJourneyAnalysis.sql`, `patientOutcomeAnalysis.sql`, `reworkAnalysis.sql`, and `waitingTimeAnalysis.sql`).
- Dashboard: `dashboard/app.py`, `dashboard/auth.py`, `dashboard/bigquery_data.py`, `dashboard/bigquery_test.py`.
- dbt: `careflow_dbt/dbt_project.yml`, `careflow_dbt/README.md`, `careflow_dbt/models/staging/stg_event_logs.sql`, `careflow_dbt/models/staging/schema.yml`, and both custom SQL tests.
- Tests and reports: `tests/test_nightly_pipeline.py`, `tests/test_process_analytics.py`, `bigquery_integration_report.md`, `pipeline_testing_report.md`, `process_analytics_report.md`, `sql_analytics_documentation.md`, and `docs/simulation_analysis_summary.md`.
- Data artifacts: headers/samples and the existing dry-run report plus local baseline fixtures, without modifying any of these files.

---

**Change boundary:** this document is documentation only. It does not change application code, dataset files, dashboard state, BigQuery, or GitHub. No commit or push is part of this work.

## 17. Team-wide project map (Day 1 overview)

This section broadens the view from the checked-out `PrasadKavitake` work to the team task streams visible in the local clone's cached remote-tracking refs. The remote could not be refreshed during this review, so branch names and contents below describe that cached snapshot and may not include newer GitHub changes.

| Branch in cached clone | Main task stream found in its files and commit history |
|---|---|
| `dolly-careflow` | Reproducible synthetic EHR generation, event schema/data dictionary, dataset validation, EDA reports, generator tests, and a GitHub Actions pytest workflow. |
| `Lehana` | BigQuery data-quality and elapsed-time work, a dbt staging model and tests, dashboard development, bounded BigQuery sampling, and authentication handling. |
| `Vishweswaran` | PM4Py process discovery and conformance checking, pathway/timeline visualizations, and clinician/department workflow views in a separate dashboard implementation. |
| `PrasadKavitake` | Local enrichment, SQL analytics, upload scripts, a local-only pipeline dry run, dashboard features, tests, and project reports. |
| `Arya` | The cached branch contains a README-only change; no larger implementation task was visible in that branch snapshot. |
| `main` | The cached remote-tracking reference points to the initial repository commit. |

### Intended combined workflow

The task streams suggest the following project-level workflow. This is an architectural view across branches, not evidence that all steps currently run together:

```text
Synthetic event generation
        ↓
Schema, timestamp, encounter-sequence validation and EDA
        ↓
BigQuery raw event table
        ↓
dbt staging and data-quality checks
        ↓
SQL elapsed-time / journey / outcome analytics
        ↓
PM4Py process discovery and conformance analysis
        ↓
Dashboard views for pathway, timing, data quality, and workflow exploration
```

The local dry-run pipeline on `PrasadKavitake` is a separate validation simulation: it compares incoming IDs with a local fixture and performs no BigQuery query or write. The direct upload scripts, dbt models, SQL files, and dashboards are also separate entry points. A shared canonical table, agreed schema, and an integration branch are still needed before describing this as one automated end-to-end pipeline.

This team-wide map is an overview only. Detailed documentation of each team's stage, handoff, and integration points will be added incrementally in subsequent updates.

## 18. Synthetic event generation and validation (Day 2)

### Generation responsibility

The cached `dolly-careflow` branch contains the synthetic event generator at `src/generate_ehr_events.py`. Its purpose is to create fictional emergency-department encounter histories that are suitable for data-pipeline and process-mining development. The generator supports a target event count or encounter count, a configurable date range, and a random seed. The documented generation command requests about 200,000 events with seed `42`; it may produce a slightly different total because it completes whole encounters rather than truncating an encounter at the requested row limit.

The branch documentation describes a 15-column event-level CSV with identifiers, activity/timestamp/order, department and synthetic staff/resource details, encounter attributes, and disposition. `case_id` groups events into an encounter; `event_id` identifies an event; `event_sequence` provides the within-encounter order. The documented snapshot contains 200,004 events across 28,737 encounters. These are synthetic records, not real patient data or measured hospital performance.

### Validation and exploratory analysis

The same branch contains `src/eda_validation.py`, `src/eda_analysis.py`, tests under `tests/`, and a GitHub Actions workflow. The documented validation covers required fields, event-ID uniqueness, timestamp validity/order, consecutive sequence numbers, encounter-level attribute consistency, activity-to-department/resource mappings, and expected encounter starts and terminal events. Generator tests also cover repeatability under the same seed, pathway variation, and completing an encounter when targeting a row count. The EDA script produces activity, duration, interval, pathway-variant, and category summaries under `reports/eda/`.

These checks establish that generated records follow the generator's programmed rules. They do not establish clinical accuracy. The generation parameters and workflow patterns are assumptions for exercising analytics code.

### Handoff to later stages

The generator branch's handoff is a CSV with the 15 source fields. Its data dictionary explicitly leaves calculated waiting time, length of stay, shift, and bottleneck flags to downstream work. Before a team-wide load, agree whether that CSV is shared as a generated artifact or regenerated from committed code, and ensure all consumers use the same snapshot and schema. In the cached branch documentation, the full CSV is excluded from Git, while a smaller sample is kept for reference.

The current `PrasadKavitake` work adds a separate optional local enrichment step that parses approximate task and queue values from `event_detail` and derives first-event and next-event timestamps. Those derived columns are not part of the generator's 15-column contract and should be treated as a downstream transformation, with their own null handling and definitions.

```text
Generator (synthetic 15-column CSV)
        ↓
Structural and encounter-rule validation
        ↓
EDA summaries and test evidence
        ↓
CSV handoff to ingestion / transformation owners
```

This generation/validation stage is documented from the cached `dolly-careflow` branch. It is not invoked by the local nightly dry-run script on `PrasadKavitake`.

## 19. BigQuery storage and dbt handoff (Day 3)

### Intended warehouse stages

Across the task branches, BigQuery is intended to hold the event rows centrally so that transformations and analytics can query a shared source. The Lehana branch provides a dbt staging-view example: it reads `careflow-analytics-98234.careflow_analytics.event_logs`, casts `event_id` and `case_id` to strings, trims activity labels, safely casts the timestamp, and substitutes `Unknown` for a blank department. Its schema tests check that the core identifiers, activity, timestamp, and department are populated and that `event_id` is unique.

In this design, raw event rows are loaded first, dbt standardizes and checks them, and downstream SQL/dashboard components consume a documented table contract. The dbt files describe a transformation and checks; they do not by themselves schedule the model or guarantee that it has run in the target BigQuery project.

### Upload paths found on `PrasadKavitake`

The checked-out branch has two independent uploader scripts:

- `src/upload_to_bigquery.py` reads `data/ehr_events_full.csv`, validates a 15-column event schema, rejects duplicate event IDs, and targets `careflow_analytics.event_logs_test`.
- `src/upload_enhanced_to_bigquery.py` reads the root-level `ehr_events_enhanced.csv`, relies on schema autodetection, and targets `careflow_analytics.event_logs_enhanced`.

Both load jobs use `WRITE_TRUNCATE`, so running either script replaces the contents of its destination table. They are direct cloud-write commands and are not called by the local nightly dry run. They require Google credentials, the relevant BigQuery permissions, and a configured project/dataset.

### Integration gap to resolve

The cached branches refer to `event_logs`, `event_logs_test`, `event_logs_enhanced`, and `event_logs_analysis`. The Lehana dbt model reads `event_logs`, while the checked-out `PrasadKavitake` dbt model reads `event_logs_analysis`; the dashboard reader also targets `event_logs`. These names and model definitions should not be treated as one connected storage design until the team confirms which tables exist and selects a canonical source and staging model.

The 15-column generated CSV, the optional 19-column locally enriched CSV, and dbt's selected output fields also represent different contracts. Before loading or transforming the full dataset, agree on field names and types, null behavior, timestamp naming, derived-field definitions, and whether refreshes replace or append records. No production scheduler or automatic raw-to-dbt handoff is evidenced by these scripts.

```text
Generated CSV ──> manual uploader ──> chosen BigQuery raw table
                                      ↓
                              dbt staging view
                                      ↓
                              schema/data tests
                                      ↓
                         SQL and dashboard readers
```

This is the intended warehouse handoff across branches. In the checked-out code, the uploaders, dbt model, SQL queries, and dashboard reads remain separately configured entry points.

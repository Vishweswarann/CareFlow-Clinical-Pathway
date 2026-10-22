CareFlow Clinical Pathway — Data Quality Report

1. Objective

The objective of this work is to validate the quality and reliability of hospital event data used in the CareFlow Clinical Pathway project.

2. Dataset Information

- Source: BigQuery
- Table: "careflow-analytics-98234.careflow_analytics.event_logs"
- Total records: 200,004
- Columns checked: case_id, event_id, activity, timestamp, department

3. Data Quality Checks

Validation Check| Result| Status
Total records| 200,004| Verified
Missing case IDs| 0| Passed
Missing event IDs| 0| Passed
Missing activities| 0| Passed
Missing timestamps| 0| Passed
Missing departments| 0| Passed
Duplicate event IDs| 0| Passed
Empty activity names| 0| Passed
Future timestamps| 0| Passed
Empty department names| 0| Passed

4. Conclusion

The dataset passed the data-quality checks listed above. No missing values, duplicate event IDs, empty activity names, empty department names, or future timestamps were found in the checks performed.

Additional validation of event ordering, activity consistency, and patient-case sequences is required before concluding that the dataset is fully reliable.
## 5. Additional Validation Checks

| Validation Check | Result | Status |
|---|---:|---|
| Empty case IDs | 0 | Passed |
| Activity names with extra spaces | 0 | Passed |
| Department names with extra spaces | 0 | Passed |
| Patient cases with only one event | 0 | Passed |
| Total patient cases | 28,737 | Verified |

## 6. Next Steps

- Validate activity names and department values for consistency.
- Create reusable data-quality SQL checks.
- Implement appropriate dbt models and tests.
- Review and commit the completed work to the Lehana branch.
## 7. dbt Test Execution

The dbt model execution completed successfully, and 10 dbt tests passed in the configured environment.


## 8. Full-Dataset Elapsed-Time Analysis

The following metrics were calculated using a read-only BigQuery query on the event_logs table. Consecutive events were ordered by timestamp, with event_sequence used to break timestamp ties. Negative elapsed intervals were excluded.

| Metric | Result |
|---|---:|
| Total events in source dataset | 200,004 |
| Distinct cases in source dataset | 28,737 |
| Non-negative consecutive-event intervals analyzed | 171,267 |
| Distinct activity-transition types | 27 |
| Mean elapsed interval | 28.86 minutes |
| Median elapsed interval | 20.18 minutes |
| Maximum elapsed interval | 240 minutes |

### Interpretation

The mean elapsed interval between consecutive recorded events was 28.86 minutes, and the median was approximately 20.18 minutes. The maximum observed interval was 240 minutes.

These metrics describe elapsed time between recorded events. They should not automatically be interpreted as patient waiting times because an interval may include time spent performing an activity.

### Validation Scope

These results provide an additional baseline for validating the dashboard's elapsed-time analysis. The metrics are based on the full source table, whereas the dashboard may use a limited sample. The results should therefore not be expected to match exactly unless both calculations use the same records and filtering rules.

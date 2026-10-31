

\# CareFlow – Pipeline Testing Report



\## 1. Introduction



As part of the CareFlow Clinical Pathway Analytics project, I worked on understanding and testing the data pipeline used to process hospital event-log data.



The purpose of this task was to verify how incoming event records are checked against existing records and how new events can be identified without unnecessarily inserting duplicate data.



\## 2. Objectives



\- Understand the working of the nightly data pipeline.

\- Validate incoming event-log records.

\- Compare incoming event IDs with existing event IDs.

\- Identify new and already existing records.

\- Test duplicate-event detection.

\- Verify pipeline behaviour using dry-run execution.



\## 3. Pipeline Overview



The pipeline follows a sequence of operations:



1\. Read the incoming event-log CSV file.

2\. Validate the input dataset.

3\. Extract unique event IDs.

4\. Compare incoming IDs with existing event IDs.

5\. Identify new records and already existing records.

6\. Generate a pipeline execution report.



This process helps prevent duplicate event records during repeated data ingestion.



\## 4. Incremental Data Validation



I worked on understanding the incremental data-loading approach.



Instead of treating every incoming record as new, the pipeline compares event IDs to determine whether a record already exists.



The comparison produces two categories:



\- \*\*Existing Events:\*\* Records whose event IDs are already present.

\- \*\*New Events:\*\* Records whose event IDs are not found in the existing dataset.



This approach helps maintain data consistency and supports incremental data processing.



\## 5. Dry-Run Testing



I worked with the dry-run functionality to test the pipeline without performing actual database writes.



During dry-run execution, the pipeline:



\- Reads and validates the incoming CSV file.

\- Checks event ID uniqueness.

\- Compares incoming records with the existing baseline.

\- Identifies new and previously existing events.

\- Generates a report containing the comparison results.



Dry-run execution is useful because it allows the pipeline logic to be checked before enabling actual data insertion.



\## 6. Testing and Validation



I worked on testing different scenarios to verify the event comparison logic.



The test scenarios included:



\- First-time execution with new event records.

\- Repeated execution with the same event IDs.

\- Mixed input containing both existing and new event IDs.

\- Empty input dataset.

\- Verification that comparison operations do not modify the existing baseline.



These tests helped verify the expected behaviour of the pipeline.



\## 7. Tools and Technologies Used



\- Python

\- Pandas

\- CSV files

\- Git and GitHub

\- BigQuery concepts

\- Pytest for automated testing



\## 8. Results



The pipeline testing helped validate the logic for identifying new and existing event records.



Dry-run execution also demonstrated how incoming data can be checked before database writes are enabled.



Automated tests were used to verify the comparison logic and different input scenarios.



\## 9. Conclusion



Through this task, I gained practical experience in data pipeline development, incremental data validation and automated testing.



I understood the importance of checking incoming records before inserting them into a database and how dry-run execution can help identify potential issues safely.



This work contributes to making the CareFlow data-processing workflow more reliable and consistent.




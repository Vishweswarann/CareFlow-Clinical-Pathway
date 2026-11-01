\# CareFlow – BigQuery Integration Report



\## 1. Introduction



As part of the CareFlow Clinical Pathway Analytics project, I worked on integrating processed hospital event-log data with Google BigQuery.



The main objective was to understand how structured event data can be transferred from local CSV files into a cloud-based data warehouse for further analysis and querying.



\## 2. Objectives



\- Understand Google BigQuery and its role in data analytics.

\- Integrate processed event-log data with BigQuery.

\- Understand datasets and table structures.

\- Upload CSV data into BigQuery tables.

\- Verify uploaded records and table information.

\- Understand how BigQuery supports large-scale analytical queries.



\## 3. Technology Used



\- Google BigQuery

\- Google Cloud Platform

\- Python

\- Pandas

\- Google Cloud BigQuery Python Client

\- CSV files



\## 4. BigQuery Dataset Structure



The project uses the following BigQuery configuration:



| Component | Name |

|---|---|

| GCP Project | careflow-analytics-98234 |

| Dataset | careflow\_analytics |

| Enhanced table | event\_logs\_enhanced |

| Test table | event\_logs\_test |



The dataset stores structured hospital event-log information for analytical processing.



\## 5. Data Integration Process



I worked on understanding and executing the data-upload workflow using Python.



The integration process involved:



1\. Reading the processed CSV file.

2\. Loading the dataset using Pandas.

3\. Establishing a connection with Google BigQuery.

4\. Selecting the destination dataset and table.

5\. Uploading structured records into BigQuery.

6\. Verifying the destination table and uploaded records.



\## 6. BigQuery Table Handling



I worked with the BigQuery dataset and its tables to understand how event-log information is stored and accessed.



The enhanced event-log table contains information such as:



\- Event ID

\- Case ID

\- Activity

\- Timestamp

\- Department

\- Event sequence

\- Resource role

\- Resource ID

\- Event details

\- Patient-related attributes

\- Derived timing information



The enhanced dataset successfully uploaded to BigQuery contained 198,258 rows and 19 columns.



\## 7. Data Verification



After the upload process, I checked the destination table to verify that the data was available in BigQuery.



The verification process focused on:



\- Checking whether the destination table existed.

\- Verifying the uploaded row count.

\- Checking the table schema.

\- Confirming that expected columns were present.

\- Understanding how uploaded records could be retrieved using SQL queries.



\## 8. Role of BigQuery in CareFlow



BigQuery provides centralized cloud storage for the project's structured event-log data.



It supports analytical operations such as:



\- Retrieving hospital activity records.

\- Filtering events based on conditions.

\- Grouping activities by patient case.

\- Calculating activity transition times.

\- Generating statistical summaries.

\- Providing data for dashboard visualizations.



\## 9. Learning Outcomes



Through this task, I gained practical knowledge of:



\- Cloud-based data warehousing.

\- Connecting Python applications with BigQuery.

\- Uploading CSV datasets into cloud tables.

\- Understanding BigQuery schemas and table structures.

\- Verifying uploaded records.

\- Using SQL for analytical operations on stored data.



\## 10. Conclusion



Working on BigQuery integration helped me understand how processed event-log data can be stored in a cloud-based analytical environment.



I gained experience with Python-based data uploading, BigQuery table management and data verification.



This integration supports the CareFlow analytics workflow by making structured hospital event data available for further SQL analysis and dashboard development.


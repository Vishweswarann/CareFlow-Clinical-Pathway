\# CareFlow – SQL Analytics Documentation



\## 1. Introduction



As part of the CareFlow Clinical Pathway Analytics project, I worked on SQL-based analysis of hospital event logs to understand patient activity sequences and calculate elapsed time between consecutive hospital activities.



The main purpose of this analysis was to examine how patients move through different hospital departments and identify activity transitions that may require further investigation due to longer time intervals.



The SQL analysis was developed using Google BigQuery and is documented in `sql/waitingTimeAnalysis.sql`.



\## 2. Objectives



\- Analyze hospital activity sequences using SQL.

\- Calculate elapsed time between consecutive activities.

\- Group activities based on patient case IDs.

\- Generate transition-level statistical summaries.

\- Calculate average, median and maximum elapsed times.

\- Identify transitions with potentially longer delays.

\- Provide analytical results for the CareFlow dashboard.



\## 3. Dataset Fields Used



The following columns were important for the analysis:



| Column | Description |

|---|---|

| event\_id | Unique event identifier |

| case\_id | Unique patient case identifier |

| activity | Name of the hospital activity |

| timestamp | Timestamp of the recorded activity |

| event\_sequence | Sequence number of the event |

| department | Hospital department associated with the event |



The `case\_id`, `activity`, `timestamp` and `event\_sequence` fields were particularly important for calculating activity transition times.



\## 4. SQL Functions Used



\### 4.1 LAG()



The LAG() window function is used to access a value from a previous row within an ordered result set.



In this project, it helps identify the timestamp and activity of the previous event within the same patient case.



\### 4.2 TIMESTAMP\_DIFF()



TIMESTAMP\_DIFF() calculates the difference between two timestamp values.



I used this function to calculate the elapsed time between consecutive hospital activities in minutes.



\### 4.3 PARTITION BY



PARTITION BY divides records into separate groups based on a specified column.



I used `PARTITION BY case\_id` to ensure that events belonging to different patient cases were not mixed during the analysis.



\### 4.4 ORDER BY



ORDER BY arranges event records chronologically using timestamps and event sequence values.



This is important because activity transitions must follow the correct event order.



\### 4.5 APPROX\_QUANTILES()



APPROX\_QUANTILES() calculates approximate percentile values.



It is useful for generating median and other percentile-based elapsed-time statistics for large datasets.



\## 5. Analytics Workflow



The SQL analytics process follows these steps:



1\. Retrieve hospital event records from BigQuery.

2\. Organize events by patient case ID.

3\. Arrange activities chronologically.

4\. Use LAG() to retrieve the previous activity and timestamp.

5\. Calculate elapsed time using TIMESTAMP\_DIFF().

6\. Group records by activity transitions.

7\. Calculate average, median, maximum and count statistics.

8\. Use the resulting summaries to examine possible workflow delays.



\## 6. SQL Query Example



The following is an illustrative BigQuery Standard SQL query demonstrating the activity transition analysis.



```sql

WITH ordered\_events AS (

&#x20;   SELECT

&#x20;       case\_id,

&#x20;       activity,

&#x20;       timestamp,

&#x20;       event\_sequence,



&#x20;       LAG(activity) OVER (

&#x20;           PARTITION BY case\_id

&#x20;           ORDER BY timestamp, event\_sequence

&#x20;       ) AS previous\_activity,



&#x20;       LAG(timestamp) OVER (

&#x20;           PARTITION BY case\_id

&#x20;           ORDER BY timestamp, event\_sequence

&#x20;       ) AS previous\_timestamp



&#x20;   FROM `careflow-analytics-98234.careflow\_analytics.event\_logs\_enhanced`

),



transition\_times AS (

&#x20;   SELECT

&#x20;       previous\_activity,

&#x20;       activity AS current\_activity,



&#x20;       TIMESTAMP\_DIFF(

&#x20;           timestamp,

&#x20;           previous\_timestamp,

&#x20;           MINUTE

&#x20;       ) AS elapsed\_minutes



&#x20;   FROM ordered\_events

&#x20;   WHERE previous\_timestamp IS NOT NULL

)



SELECT

&#x20;   previous\_activity,

&#x20;   current\_activity,



&#x20;   AVG(elapsed\_minutes) AS average\_elapsed\_minutes,



&#x20;   APPROX\_QUANTILES(

&#x20;       elapsed\_minutes, 100

&#x20;   )\[OFFSET(50)] AS median\_elapsed\_minutes,



&#x20;   MAX(elapsed\_minutes) AS maximum\_elapsed\_minutes,



&#x20;   COUNT(\*) AS transition\_count



FROM transition\_times

WHERE elapsed\_minutes >= 0



GROUP BY

&#x20;   previous\_activity,

&#x20;   current\_activity



ORDER BY average\_elapsed\_minutes DESC;

```



\*Note: This is an illustrative query showing the analytical approach. The actual project SQL implementation is maintained in `sql/waitingTimeAnalysis.sql`.\*



\## 7. Interpretation of Analytical Results



The generated transition summaries help understand the time intervals between different hospital activities.



The important measurements include:



\- \*\*Average Elapsed Time:\*\* Average interval between consecutive activities.

\- \*\*Median Elapsed Time:\*\* Middle value of the observed intervals.

\- \*\*Maximum Elapsed Time:\*\* Largest observed interval.

\- \*\*Transition Count:\*\* Number of observations for a particular activity transition.



Transitions with higher elapsed times can be investigated to identify potential workflow delays.



However, transitions with very few observations should be interpreted carefully because a small sample can produce misleading averages.



Also, elapsed time between recorded activities should not automatically be treated as actual task duration or confirmed patient waiting time.



\## 8. Project Contribution



Through this task, I contributed to the SQL analytics component of CareFlow.



My work involved:



\- Developing SQL-based activity transition analysis.

\- Understanding and applying SQL window functions.

\- Calculating elapsed time between consecutive activities.

\- Generating transition-level statistical summaries.

\- Ranking transitions based on elapsed-time measurements.

\- Supporting the analytical requirements of the dashboard.



The analysis helps convert raw hospital event logs into meaningful information about patient activity sequences and workflow patterns.



\## 9. Conclusion



The SQL analytics work helped me develop practical knowledge of BigQuery and advanced SQL functions.



I learned how window functions, timestamp calculations and aggregate functions can be used to analyze large event-log datasets.



This work contributes to the CareFlow Clinical Pathway Analytics project by providing useful insights into activity transitions, elapsed times and potential workflow bottlenecks.


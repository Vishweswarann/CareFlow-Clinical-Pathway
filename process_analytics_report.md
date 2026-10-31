\# CareFlow – Process Analytics Report



\## 1. Introduction



As part of the CareFlow Clinical Pathway Analytics project, I worked on analyzing hospital event logs to understand the sequence of patient activities and the time elapsed between consecutive activities.



The main objective of this analysis was to understand patient flow, measure activity transition times and identify areas where delays may occur during the hospital process.



\## 2. Objectives



\- Analyze the sequence of activities performed during patient encounters.

\- Calculate elapsed time between consecutive hospital activities.

\- Identify activities with longer transition times.

\- Generate statistical summaries of activity transition times.

\- Support the identification of potential workflow bottlenecks.



\## 3. Dataset Used



The project uses a simulated EHR event-log dataset.



The enhanced dataset contains:

\- Total events: 198,258

\- Unique cases: 28,737

\- Total columns: 19



Important columns used for analysis include:

\- event\_id

\- case\_id

\- activity

\- timestamp

\- department

\- event\_sequence



\## 4. Process Analytics Using SQL



I worked on SQL-based analysis to calculate the elapsed time between consecutive activities within each patient case.



The analysis uses the following SQL functions:



\- \*\*LAG():\*\* Used to access the timestamp or activity of the previous event within a case.

\- \*\*TIMESTAMP\_DIFF():\*\* Used to calculate the time difference between two timestamps.

\- \*\*PARTITION BY:\*\* Used to separate events belonging to different patient cases.

\- \*\*ORDER BY:\*\* Used to maintain the chronological order of activities.

\- \*\*APPROX\_QUANTILES():\*\* Used to calculate approximate percentile-based statistics.



These functions helped generate activity transition summaries from the event-log dataset.



\## 5. Waiting-Time and Elapsed-Time Analysis



The analysis focuses on understanding the time interval between consecutive hospital activities.



The calculated elapsed-time information helps identify transitions that may require further investigation.



The analysis includes:

\- Average elapsed time.

\- Median elapsed time.

\- Maximum elapsed time.

\- Number of observations for each activity transition.



These measurements help compare different activity transitions and understand variations in patient flow.



\## 6. Identification of Potential Bottlenecks



By examining the average elapsed time between activities, transitions with relatively longer intervals can be identified for further investigation.



However, a high average based on a small number of observations should be interpreted carefully. Further validation is necessary before considering a transition an actual hospital workflow bottleneck.



\## 7. Tools and Technologies Used



\- SQL

\- Google BigQuery

\- Python

\- Pandas

\- Git and GitHub



\## 8. Conclusion



Through this task, I gained practical experience in process analytics and working with hospital event-log data.



I learned how SQL window functions and timestamp calculations can be used to analyze activity transitions and measure elapsed time.



This analysis contributes to the CareFlow project by providing useful information about patient activity sequences and potential workflow delays, which can be presented through the project dashboard.




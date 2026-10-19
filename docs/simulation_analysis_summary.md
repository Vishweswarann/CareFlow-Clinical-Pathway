
# CareFlow Clinical Pathway — Simulation Analysis

## 1. Objective

Enhance a synthetic hospital event log to simulate
irregular patient arrivals, variable task durations,
waiting times, repeated activities, alternative pathways,
rare emergency surgery events, and incomplete cases.

## 2. Dataset

- Total events: 198,258
- Total patient cases: 28,737
- Data source: Synthetic EHR event log
- Analysis platform: Google BigQuery

## 3. Key Findings

### Patient Journey
- Average journey duration: 245.9 minutes
- Median journey duration: 223 minutes
- Average events per case: 6.9

### Waiting-Time Bottlenecks
- Hospital Admission: 33.88 minutes average wait
- Imaging: 28.54 minutes average wait
- Laboratory Testing: 23.83 minutes average wait

### Repeated Activities
- Cases with repeated activities: 12,376
- Percentage of cases: 43.07%
- Total extra activity visits: 20,135

### Patient Outcomes
- Discharged: 21,381 cases (74.40%)
- Admitted: 6,832 cases (23.77%)
- Left Without Being Seen: 524 cases (1.82%)

## 4. Data Quality

- Unique event IDs: 198,258
- Missing task durations after imputation: 0
- Missing waiting times after imputation: 0

## 5. Assumptions and Limitations

The dataset is synthetic and is not a representation
of measured hospital performance.

Missing emergency surgery duration and waiting-time
values were imputed using assumed values of 180 and
10 minutes, respectively.

Repeated activity types are used as a proxy for rework.
Not every repeated activity represents an error or
unnecessary clinical work.

Journey duration measures the time between the first
and last recorded event in each case.

## 6. Deliverables

- Synthetic event-log dataset
- BigQuery analysis table
- SQL bottleneck analysis
- SQL patient journey analysis
- SQL repeated-activity analysis
- SQL patient outcome analysis
- Simulation analysis documentation

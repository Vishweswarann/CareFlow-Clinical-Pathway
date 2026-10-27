
import pandas as pd
import numpy as np

# Load the simulated dataset
INPUT_FILE = "ehr_events_simulated.csv"
OUTPUT_FILE = "ehr_events_enhanced.csv"

df = pd.read_csv(INPUT_FILE)
df["timestamp"] = pd.to_datetime(
    df["timestamp"],
    format="mixed",
    dayfirst=True,
    errors="raise"
)



# Sort events chronologically within each patient case
df = df.sort_values(
    ["case_id", "timestamp", "event_sequence"]
).reset_index(drop=True)

# 1. Extract the simulated task duration and waiting time
# from event_detail, where these approximate values were recorded.
details = df["event_detail"].fillna("")

df["task_duration_minutes"] = pd.to_numeric(
    details.str.extract(r"task duration ~(\d+) min")[0],
    errors="coerce"
)

df["waiting_time_minutes"] = pd.to_numeric(
    details.str.extract(r"queue delay ~(\d+) min")[0],
    errors="coerce"
)

# 2. Assign zero/unknown values carefully for special events.
# These values were not recorded explicitly for all event types.
df.loc[
    df["task_duration_minutes"].isna(),
    "task_duration_minutes"
] = np.nan

df.loc[
    df["waiting_time_minutes"].isna(),
    "waiting_time_minutes"
] = np.nan

# 3. Record the first event timestamp as the case arrival timestamp.
# This represents the first recorded event, not necessarily
# the actual hospital arrival time.
df["arrival_timestamp"] = (
    df.groupby("case_id")["timestamp"].transform("min")
)

# 4. Calculate elapsed time until the next event in each case.
# Useful for process-mining analysis, but NOT the same as
# the actual task duration.
df["minutes_until_next_event"] = (
    df.groupby("case_id")["timestamp"]
      .shift(-1)
      .sub(df["timestamp"])
      .dt.total_seconds()
      .div(60)
)

# 5. Validate the dataset
print("Total events:", len(df))
print("Unique cases:", df["case_id"].nunique())
print("Duplicate event IDs:", df["event_id"].duplicated().sum())
print(
    "Duplicate case-sequence pairs:",
    df.duplicated(["case_id", "event_sequence"]).sum()
)
print(
    "Missing task durations:",
    df["task_duration_minutes"].isna().sum()
)
print(
    "Missing waiting times:",
    df["waiting_time_minutes"].isna().sum()
)
print(
    "Negative intervals:",
    (df["minutes_until_next_event"] < 0).sum()
)

# 6. Save the enhanced dataset
df["timestamp"] = df["timestamp"].dt.strftime(
    "%Y-%m-%d %H:%M:%S"
)
df["arrival_timestamp"] = df["arrival_timestamp"].dt.strftime(
    "%Y-%m-%d %H:%M:%S"
)

df.to_csv(OUTPUT_FILE, index=False)

print(f"\nEnhanced dataset saved as: {OUTPUT_FILE}")

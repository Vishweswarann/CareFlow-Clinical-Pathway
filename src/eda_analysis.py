
from pathlib import Path

import pandas as pd
import matplotlib.pyplot as plt

# --------------------------------------------------
# 1. LOAD DATA
# --------------------------------------------------

ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "data" / "ehr_events_full.csv"
OUTPUT_DIR = ROOT / "reports" / "eda"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

df = pd.read_csv(DATA_PATH)
df["timestamp"] = pd.to_datetime(df["timestamp"], errors="raise")

print("Dataset shape:", df.shape)
print("Unique encounters:", df["case_id"].nunique())


# --------------------------------------------------
# 2. ACTIVITY FREQUENCY
# --------------------------------------------------

activity_counts = (
    df["activity"]
    .value_counts()
    .rename_axis("activity")
    .reset_index(name="event_count")
)

activity_counts["percentage"] = (
    activity_counts["event_count"] / len(df) * 100
).round(2)

activity_counts.to_csv(
    OUTPUT_DIR / "activity_frequency.csv", index=False
)

print("\nActivity frequency:")
print(activity_counts.to_string(index=False))

plt.figure(figsize=(11, 6))
plt.bar(activity_counts["activity"], activity_counts["event_count"])
plt.title("Event Frequency by Activity")
plt.xlabel("Activity")
plt.ylabel("Number of Events")
plt.xticks(rotation=40, ha="right")
plt.tight_layout()
plt.savefig(OUTPUT_DIR / "activity_frequency.png", dpi=150)
plt.close()


# --------------------------------------------------
# 3. ENCOUNTER DURATION
# --------------------------------------------------

case_summary = (
    df.groupby("case_id")
    .agg(
        first_event=("timestamp", "min"),
        last_event=("timestamp", "max"),
        event_count=("event_id", "count"),
    )
    .reset_index()
)

case_summary["duration_minutes"] = (
    case_summary["last_event"] - case_summary["first_event"]
).dt.total_seconds() / 60

print("\nLongest 10 encounters:")
print(
    case_summary.nlargest(10, "duration_minutes")[
        ["case_id", "duration_minutes", "event_count"]
    ].to_string(index=False)
)

case_summary.to_csv(
    OUTPUT_DIR / "encounter_summary.csv", index=False
)

print("\nEncounter duration in minutes:")
print(case_summary["duration_minutes"].describe().round(2))

plt.figure(figsize=(9, 5))
plt.hist(case_summary["duration_minutes"], bins=40)
plt.title("Distribution of Encounter Durations")
plt.xlabel("Elapsed Duration (minutes)")
plt.ylabel("Number of Encounters")
plt.tight_layout()
plt.savefig(OUTPUT_DIR / "encounter_duration.png", dpi=150)
plt.close()


# --------------------------------------------------
# 4. INTERVALS BETWEEN CONSECUTIVE EVENTS
# --------------------------------------------------

ordered = df.sort_values(["case_id", "event_sequence"]).copy()

# Capture the activity at the start of each interval.
ordered["from_activity"] = (
    ordered.groupby("case_id")["activity"].shift(1)
)

# Calculate elapsed time from the previous event to the current event.
ordered["interval_minutes"] = (
    ordered.groupby("case_id")["timestamp"]
    .diff()
    .dt.total_seconds() / 60
)

intervals = ordered.dropna(
    subset=["interval_minutes", "from_activity"]
).copy()

print("\nIntervals between consecutive events (minutes):")
print(intervals["interval_minutes"].describe().round(2))

transition_summary = (
    intervals.groupby("from_activity", as_index=False)
    .agg(
        mean_interval_minutes=("interval_minutes", "mean"),
        median_interval_minutes=("interval_minutes", "median"),
        transition_count=("interval_minutes", "size"),
    )
    .sort_values("median_interval_minutes", ascending=False)
)

transition_summary.to_csv(
    OUTPUT_DIR / "activity_interval_summary.csv", index=False
)

print("\nIntervals grouped by the activity that starts the interval:")
print(transition_summary.round(2).to_string(index=False))

# --------------------------------------------------
# 5. COMMON PATHWAY VARIANTS
# --------------------------------------------------

pathways = (
    ordered.groupby("case_id")["activity"]
    .agg(lambda activities: " -> ".join(activities))
    .value_counts()
    .head(20)
    .rename_axis("pathway")
    .reset_index(name="encounter_count")
)

pathways["percentage"] = (
    pathways["encounter_count"] / df["case_id"].nunique() * 100
).round(2)

pathways.to_csv(
    OUTPUT_DIR / "top_pathway_variants.csv", index=False
)

print("\nTop 10 pathway variants:")
print(pathways.head(10).to_string(index=False))


# --------------------------------------------------
# 6. CATEGORY DISTRIBUTIONS
# --------------------------------------------------

for column in [
    "arrival_mode",
    "triage_level",
    "disposition",
    "age_group",
    "gender",
    "resource_role",
]:
    if column in df.columns:
        summary = (
            df[column]
            .value_counts(dropna=False)
            .rename_axis(column)
            .reset_index(name="event_count")
        )

        summary.to_csv(
            OUTPUT_DIR / f"{column}_distribution.csv",
            index=False,
        )

# --------------------------------------------------
# 7. FINISH
# --------------------------------------------------

print("\nEDA complete.")
print("Reports and charts saved to:", OUTPUT_DIR)

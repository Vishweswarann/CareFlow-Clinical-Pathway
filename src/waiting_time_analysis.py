
from pathlib import Path
import pandas as pd

# Project paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent
INPUT_FILE = PROJECT_ROOT / "data" / "sample" / "ehr_events_sample.csv"
OUTPUT_DIR = PROJECT_ROOT / "data" / "processed"


def analyze_waiting_times():
    # Load the synthetic EHR event log
    df = pd.read_csv(INPUT_FILE)

    required_columns = {"case_id", "activity", "timestamp"}
    missing = required_columns - set(df.columns)

    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")

    # Convert timestamps and remove rows that cannot be timed
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    df = df.dropna(subset=["case_id", "activity", "timestamp"])

    # Sort events within each patient case
    df = df.sort_values(
        ["case_id", "timestamp", "event_id"]
        if "event_id" in df.columns
        else ["case_id", "timestamp"]
    ).copy()

    # Find the previous activity and timestamp for each case
    df["previous_activity"] = (
        df.groupby("case_id")["activity"].shift(1)
    )
    df["previous_timestamp"] = (
        df.groupby("case_id")["timestamp"].shift(1)
    )

    # Elapsed time between consecutive events, in minutes
    df["elapsed_minutes"] = (
        df["timestamp"] - df["previous_timestamp"]
    ).dt.total_seconds() / 60

    # First event in each case has no preceding event
    intervals = df.dropna(
        subset=["previous_activity", "elapsed_minutes"]
    ).copy()

    # Negative intervals should be investigated, not treated as waiting time
    negative_count = int((intervals["elapsed_minutes"] < 0).sum())
    intervals = intervals[intervals["elapsed_minutes"] >= 0]

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Detailed event-to-event intervals
    detail_file = OUTPUT_DIR / "event_intervals.csv"
    intervals.to_csv(detail_file, index=False)

    # Summary by activity transition
    summary = (
        intervals.groupby(
            ["previous_activity", "activity"], as_index=False
        )
        .agg(
            transition_count=("elapsed_minutes", "count"),
            mean_elapsed_minutes=("elapsed_minutes", "mean"),
            median_elapsed_minutes=("elapsed_minutes", "median"),
            max_elapsed_minutes=("elapsed_minutes", "max"),
        )
        .sort_values("median_elapsed_minutes", ascending=False)
    )

    summary_file = OUTPUT_DIR / "waiting_time_by_transition.csv"
    summary.to_csv(summary_file, index=False)

    print(f"Input events: {len(df)}")
    print(f"Patient cases: {df['case_id'].nunique()}")
    print(f"Valid consecutive intervals: {len(intervals)}")
    print(f"Negative intervals excluded: {negative_count}")
    print(f"\nDetailed results: {detail_file}")
    print(f"Transition summary: {summary_file}")
    print("\nTransitions with the highest median elapsed time:")
    print(summary.head(10).round(2).to_string(index=False))


if __name__ == "__main__":
    analyze_waiting_times()
